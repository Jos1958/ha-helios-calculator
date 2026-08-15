import time
from datetime import datetime, timedelta
import numpy as np
from scipy.optimize import linprog

# Module: HELIOS Calculator - Python Function to Calculate an Optimized Energy Plan                            
# Home Energy Linear Integrated Optimization Service (HELIOS Calculator)
# The Optimizer uses SciPy Linear/MILP Programming to calculated the Optimal Energy Plan 
#
# Created by: Jos Raaijmakers
# Log: 
#   2026-05-19: JR: V0.1  Started Implementation with help of Google Gemini
#   2026-05-20: JR: V0.2  Balance Rule included
#   2026-06-23: JR: V0.3  Input arrays as parameters for the service, automation calls the service
#   2026-06-24: JR: V0.4  Battery Configuration and Return payload to automation, calculate strategy


@service(supports_response="optional")
def helios_calc_home_energy(
    steps=24,
    step_size=60,
    start_step=0,  # 0 = Determine start step automatically using current time
    max_time=10.0,
    max_iterations=10000,
    grid_max_import=11.0,
    grid_max_export=11.0,
    import_prices=None,
    export_prices=None,
    house_forecast=None,
    solar=None,
    battery=None,
    ev=None,
    heat_pump=None,
    boiler=None,
    return_response=None
):
    """
Home Energy Linear Integrated Optimization System (HELIOS):

A Home Assistant Energy Optimizer Service that uses SciPy Linear/MILP Programming.
It calculates an Optimized Energy Plan for a certain period (e.g. 1 or 2 days) by
searching for the best power values per step in the period.
Specified the number of steps and the length of a step in minutes.
For example: 24 steps of 60 minutes optimizes a period of 1 day.
Import and Export prices and House Usage Forecast arrays are input for the Optimizer.
For each step the prices and energy usage need to be provided in these arrays.

The Energy Cost is calculated for the energy import from or exported to the Grid.
Total Energy Cost is the sum of the energy costs per step.
The optimizer tries to MINIMIZE the Total Energy Cost over the whole period.
Remark: A negative cost can be returned when energy is exported to the grid or when negative import prices occur.
Without a battery or without deferrable devices there is not much to optimize since 
a power balance between power usage and imported and exported energy must
exist in each step!

The optimization period is always for today (and optionally following days) and by default the start step will based on the current time.
Optionally a different start step can be specified (e.g. 1 to start at the beginning of the day.  
Input arrays must start at 00:00 for today so that the optimizer can find the correct prices and forecasts.

The calculated Optimized Energy Plan is used as input to determine the Battery Strategy:
  NOM, Buy, Sell, Charge, Discharge, Disabled, (Zero?)
Current values are provided for steering the battery and deferrable devices.

Optional inputs are:
- Battery Information
- Solar Forecast Information

Optional deferrable devices are:
- Eletrical Vehicle (EV) Charging Information
- Heat Pomp (HP) Operation Information
- Boiler Operation Information
    """
    
    T = int(steps)
    dt = float(step_size) / 60.0
    start_index = int(start_step) - 1 # Start Index (0..T-1), while Start Step (1..T)

    # -------------------------------------------------------------------
    # 0. TIME LOGIC & AUTOMATIC START_INDEX Calculation (based on current time)
    # -------------------------------------------------------------------
    now = datetime.now()
    base_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) # Start at 00:00 today

    # When start_index is -1 (start_step is 0), the start index is calculated using current time
    if start_index < 0:
        minutes_passed = (now - base_dt).total_seconds() / 60.0
        start_index = int(minutes_passed // float(step_size))
        
        # Make sure the start index is within range [0, T-1]:
        # TODO: Determine if this is really what should happen !!!!
        start_index = max(0, min(start_index, T)) # 0..T, for T all steps will be skipped

    # -------------------------------------------------------------------
    # 1. PARSE INPUT ARRAYS
    # -------------------------------------------------------------------
    import_prices  = [float(p) for p in import_prices]  if import_prices  else [0.20] * T
    export_prices  = [float(p) for p in export_prices]  if export_prices  else [0.05] * T
    house_forecast = [float(h) for h in house_forecast] if house_forecast else [0.50] * T

    solar_enabled  = bool(solar     and solar.get("enabled", True))
    solar_forecast = [float(s) for s in solar.get("forecast", [0.0] * T)] if solar_enabled else [0.0] * T

    bat_enabled    = bool(battery   and battery.get("enabled", True))
    ev_enabled     = bool(ev        and ev.get("enabled", False))
    hp_enabled     = bool(heat_pump and heat_pump.get("enabled", False))
    boiler_enabled = bool(boiler    and boiler.get("enabled", False))

    # -------------------------------------------------------------------
    # 2. DYNAMISCHE INDEX-MAP OPBOUWEN
    # -------------------------------------------------------------------
    active_vars = ["import", "export"]
    if bat_enabled:
        active_vars.extend(["bat_charge", "bat_discharge"])
    if ev_enabled:
        active_vars.append("ev_charge")
    if hp_enabled:
        active_vars.append("hp_power")
    if boiler_enabled:
        active_vars.append("boiler_power")

    var_offset = {name: i for i, name in enumerate(active_vars)}
    M = len(active_vars)
    total_vars = T * M

    def get_idx(t, var_name):
        return t * M + var_offset[var_name]

    # -------------------------------------------------------------------
    # 3. COST VECTOR (c) and BOUNDS are calculated
    # -------------------------------------------------------------------
    c = np.zeros(total_vars)
    bounds = [(0, 0)] * total_vars

    # For each step determine the cost and the bounds per variable
    # Per step the cost is a import-price * import + export-price * export
    # Total cost is the sum of all step costs
    # The total cost will be minimized (more negative is good)
    # Skipped steps (in the past) are included but have zero cost since import and export are zero
    for t in range(T):
        # Determine if the current step is in the past and needs to be skipped
        # Past steps will be disabled by setting the upper limit of variables to 0
        # As a result the variables for these steps can only be resolved to zero.
        is_past = (t < start_index) # Step in the past will be skipped

        # Grid Import & Export
        idx_imp = get_idx(t, "import")
        idx_exp = get_idx(t, "export")
        c[idx_imp] =  import_prices[t] * dt
        c[idx_exp] = -export_prices[t] * dt
        bounds[idx_imp] = (0, 0) if is_past else (0, float(grid_max_import))
        bounds[idx_exp] = (0, 0) if is_past else (0, float(grid_max_export))

        # Battery: 
        if bat_enabled:
            idx_chg = get_idx(t, "bat_charge")
            idx_dis = get_idx(t, "bat_discharge")
            c_p = 0.0 if is_past else float(battery.get("charge_power_kw", 3.0))
            d_p = 0.0 if is_past else float(battery.get("discharge_power_kw", 3.0))
            bounds[idx_chg] = (0, c_p)
            bounds[idx_dis] = (0, d_p)

            # Give charging and discharging a verwaarloosbare cost (e.g. 0.0001 per kWh)
            # This will prevent the solver to charge and discharge at the same time!
            if not is_past:
                c[idx_chg] = 0.000 * dt
                c[idx_dis] = 0.010 * dt
        
 #       if bat_enabled:
 #           c_p = 0.0 if is_past else float(battery.get("charge_power_kw"   , 3.0))
 #           d_p = 0.0 if is_past else float(battery.get("discharge_power_kw", 3.0))
 #           bounds[get_idx(t, "bat_charge"   )] = (0, c_p)
 #           bounds[get_idx(t, "bat_discharge")] = (0, d_p)

        # Optional Smart Deferrable Devices:
        if ev_enabled: # Electrical Vehicle enabled?
            ev_p = 0.0   if is_past else float(ev.get("charge_power"    , 7.4))
            bounds[get_idx(t, "ev_charge"   )] = (0, ev_p)

        if hp_enabled: # Heat Pump enabled?
            hp_p = 0.0   if is_past else float(heat_pump.get("max_power", 2.0))
            bounds[get_idx(t, "hp_power"    )] = (0, hp_p)

        if boiler_enabled: # Boiler enabled?
            boil_p = 0.0 if is_past else float(boiler.get("max_power"   , 1.5))
            bounds[get_idx(t, "boiler_power")] = (0, boil_p)

    # -------------------------------------------------------------------
    # 4. BALANCE RULES (A_eq, b_eq): Sum of all Power variables is always zero
    # -------------------------------------------------------------------
    A_eq = [] # Initialize the left  side of the balance rules array
    b_eq = [] # Initialize the right side of the balance rules array

    for t in range(T): # For each step
        row = np.zeros(total_vars)
        row[get_idx(t, "import")] =  1.0
        row[get_idx(t, "export")] = -1.0

        if bat_enabled:
            row[get_idx(t, "bat_discharge")] =  1.0
            row[get_idx(t, "bat_charge"   )] = -1.0

        if ev_enabled:
            row[get_idx(t, "ev_charge"    )] = -1.0

        if hp_enabled:
            row[get_idx(t, "hp_power"     )] = -1.0

        if boiler_enabled:
            row[get_idx(t, "boiler_power" )] = -1.0

        A_eq.append(row)

        if t < start_index:
            b_eq.append(0.0)
        else:
            net_house_demand = house_forecast[t] - solar_forecast[t]
            b_eq.append(net_house_demand)

    # -------------------------------------------------------------------
    # 5. BATTERIJ SOC BEPERKINGEN & RANDGEVALLEN (A_ub, b_ub)
    # -------------------------------------------------------------------
    A_ub = []
    b_ub = []

    if bat_enabled:
        cap = float(battery.get("capacity_kwh", 10.0))
        eff = float(battery.get("efficiency", 0.95))

        soc_start_pct = float(battery.get("soc_start_pct", 20.0))
        soc_start_kwh = (soc_start_pct / 100.0) * cap

        soc_min_pct = float(battery.get("soc_min_pct", 15.0))
        soc_max_pct = float(battery.get("soc_max_pct", 85.0))
        
        soc_min_kwh = (soc_min_pct / 100.0) * cap
        soc_max_kwh = (soc_max_pct / 100.0) * cap

        # A. Retrieve Maximum Power (Charge and Discharge):
        max_charge_power = float(battery.get("charge_power_kw", 3.0))
        max_discharge_power = float(battery.get("discharge_power_kw", 3.0))

        # B. Borderline Case: Is the requested end-SOC possible in the available charge time?
        soc_end_min_pct = float(battery.get("soc_end_min_pct", soc_min_pct))
        requested_end_kwh = (soc_end_min_pct / 100.0) * cap

        remaining_steps = max(1, T - start_index) # Determine how many steps are available in the optimization period
        max_possible_added_kwh = remaining_steps * max_charge_power * dt * eff # Determine maximum charge capacity (kWh)
        
        # Adapt the end-SOC when infeasible for the solver in the available time (optimization period) 
        soc_end_min_kwh = min(requested_end_kwh, soc_start_kwh + max_possible_added_kwh) # Minimum of the requested and max possible end-SOC

        # C. Cumulative SOC rules per step
        # Keep the battery SOC above the Minimum and below the Maximum at every step of the optimization period
        # For each step two rules are added:
        # - Keep the sum of the Charged kWh - Discharged kWh below SOC-Max - SOC-Start
        # - Keep the sum of the Discharged kWh - Charged kWh above SOC-Start - SOC-Min
        # The Sum per step includes in every next step an extra step charge or discharge
        # No rules are added for the steps that are before the start step
        # To prevent infeasible SOC-Min or SOC-Max rules: 
        #   Adapt the SOC-Min and SOC-Max for an under-charged (below SOC-Min) or over-charged (above SOC-Max) battery
        #   when the max charge or max discharge power is insufficient to reach the minimum or maximum SOC during the step.
        for t in range(1, T + 1):
            if t <= start_index:
                continue # Current step is before the

            steps_from_start = t - start_index

            # When starting above SOC-Max we cannot discharge faster than the max discharge power:
            max_discharge_kwh = steps_from_start * (max_discharge_power / eff) * dt
            step_allowed_max_kwh = max(soc_max_kwh, soc_start_kwh - max_discharge_kwh)

            # When starting below the SOC-Min, we cannot charge faster than the max charge power:
            max_charge_kwh = steps_from_start * (max_charge_power * eff) * dt
            step_allowed_min_kwh = min(soc_min_kwh, soc_start_kwh + max_charge_kwh)

            # Initiate the multipliers of the maximum rule with 0 (future steps are excluded from the sum)
            row_max = np.zeros(total_vars)
            row_min = np.zeros(total_vars)

            # Fill the multipliers for all steps until and including the current step
            # Remark: The sum includes the skipped steps (before the start step) but the charge and discharge values for these steps will be zero anyway
            for i in range(t):
                row_max[get_idx(i, "bat_charge")] = eff * dt
                row_max[get_idx(i, "bat_discharge")] = -(1.0 / eff) * dt
                row_min[get_idx(i, "bat_charge")] = -eff * dt
                row_min[get_idx(i, "bat_discharge")] = (1.0 / eff) * dt

            # Add the SOC-Max rule for the current step:
            A_ub.append(row_max) # Array with Multipliers for charge and discharge values for the current step (Maximum SOC rule)
            b_ub.append(step_allowed_max_kwh - soc_start_kwh) # (Feasible) Maximum SOC - Start SOC

            # Add the SOC-Min rule for the current step:
            A_ub.append(row_min) # Array with Multiplies for charge and discharge values for the current step (Minimum SOC rule)
            b_ub.append(soc_start_kwh - step_allowed_min_kwh) # Start SOC - (Feasible) Minimum SOC

        # D. Minimale SOC-End Rule for the end of the optimization period:
        # This rule allows for an optional minimum SOC-End value for the Battery SOC at the end of the optimization period.
        # Otherwise the optimization would empty the battery to the minimum to optimize the cost value.
        # When an SOC-End of 0 is provided the SOC-Min will automatically be applied as the minimum end SOC.
        # To prevent an infeasible SOC-End the end value has already been adapted above. 
        row_end = np.zeros(total_vars)
        for t in range(T):
            row_end[get_idx(t, "bat_charge")] = -eff * dt
            row_end[get_idx(t, "bat_discharge")] = (1.0 / eff) * dt

        A_ub.append(row_end) # Array with Multipliers for charge and discharge values for all steps (Minimum SOC End rule)
        b_ub.append(-(soc_end_min_kwh - soc_start_kwh)) # (Feasible) Minimum SOC End - Start SOC
    
    # -------------------------------------------------------------------
    # 6. SCIPY SOLVER AANROEPEN
    # -------------------------------------------------------------------
    solver_options = {
        "time_limit": float(max_time),
        "maxiter": int(max_iterations)
    }

    t_start = time.perf_counter()

    res = linprog(
        c,
        A_ub=A_ub if A_ub else None,
        b_ub=b_ub if b_ub else None,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
        options=solver_options
    )

    t_end = time.perf_counter()
    execution_time_ms = round((t_end - t_start) * 1000, 2)

    # -------------------------------------------------------------------
    # 7. RESULTATEN VERWERKEN EN STRATEGIEN BEPALEN
    # -------------------------------------------------------------------
    if res.success:
        timestamps = []
        grid_import_plan, grid_export_plan = [], []
        solar_plan, house_plan = [], []
        bat_charge_plan, bat_discharge_plan = [], []
        soc_pct_plan, soc_kwh_plan = [], []
        strategy_plan = []
        ev_plan, hp_plan, boiler_plan = [], [], []

        current_soc_kwh = soc_start_kwh if bat_enabled else 0.0

        step_dt = base_dt # Start at 00:00 today
        for t in range(T):
            timestamps.append(step_dt.isoformat(timespec="minutes")) # Timestamp for start of next step

            imp = round(float(res.x[get_idx(t, "import")]), 2)
            exp = round(float(res.x[get_idx(t, "export")]), 2)
            sol = round(solar_forecast[t], 2)
            house = round(house_forecast[t], 2)

            c_p = round(float(res.x[get_idx(t, "bat_charge")]), 2) if bat_enabled else 0.0
            d_p = round(float(res.x[get_idx(t, "bat_discharge")]), 2) if bat_enabled else 0.0

            ev_p = round(float(res.x[get_idx(t, "ev_charge")]), 2) if ev_enabled else 0.0
            hp_p = round(float(res.x[get_idx(t, "hp_power")]), 2) if hp_enabled else 0.0
            boil_p = round(float(res.x[get_idx(t, "boiler_power")]), 2) if boiler_enabled else 0.0

            # SOC verloop berekenen
            if bat_enabled:
                delta_kwh = (c_p * eff - d_p / eff) * dt
                current_soc_kwh = max(0.0, min(cap, current_soc_kwh + delta_kwh))
                current_soc_pct = round((current_soc_kwh / cap) * 100.0, 1)
            else:
                current_soc_pct = 0.0

            # Strategie Bepalen (met 'Skipped' voor overgeslagen stappen)
            if t < start_index:
                strat = "Skipped"
            else:
                net_house_demand = max(0.0, house - sol)
                net_solar_surplus = max(0.0, sol - house)

                if c_p > (net_solar_surplus + 0.1):
                    if import_prices[t] < 0 or sol < 0.05:
                        strat = "Buy"
                    elif sol >= c_p:
                        strat = "Charge Solar"
                    else:
                        strat = "Charge"
                elif d_p > (net_house_demand + 0.1):
                    if exp > 0.05:
                        strat = "Sell"
                    else:
                        strat = "Discharge"
                elif c_p > 0.05 or d_p > 0.05:
                    strat = "NOM"
                else:
                    strat = "Disabled"

            # Arrays vullen
            grid_import_plan.append(imp)
            grid_export_plan.append(exp)
            solar_plan.append(sol)
            house_plan.append(house)
            bat_charge_plan.append(c_p)
            bat_discharge_plan.append(d_p)
            soc_kwh_plan.append(round(current_soc_kwh, 2))
            soc_pct_plan.append(current_soc_pct)
            strategy_plan.append(strat)
            ev_plan.append(ev_p)
            hp_plan.append(hp_p)
            boiler_plan.append(boil_p)
            
            step_dt = step_dt + timedelta(minutes=step_size) # Timestamp for next step
        
        end_dt = step_dt # End of last step
        
        # -------------------------------------------------------------------
        # 8. UPDATE HOME ASSISTANT SENSOR
        # -------------------------------------------------------------------
        active_index = min(start_index, T - 1) # Determine the currently active step, use last step when outside the optimization 
        active_time  = timestamps[active_index]
        current_strat = strategy_plan[active_index] # Current strategy

        # Warning: Battery is Charging OR Discharging but currently this is not yet enforced by the optimization model!
        # A rule may need to be added to enforce this or a cost for (dis)charging may be added to prevent this
        net_w = 1000 * (bat_charge_plan[active_index] - bat_discharge_plan[active_index]) # Net Battery Power in Watt


        full_payload = {
            "success": True,
            "total_cost_eur": round(float(res.fun), 2),
            "last_run_started": now.isoformat(),
            
            "solver_execution_time_ms": execution_time_ms,
            "solver_iterations": res.nit,
            "solver_status": res.message,
            
            "start_time" : base_dt.isoformat(timespec="minutes"),
            "active_time": active_time,
            "end_time"   : end_dt.isoformat(timespec="minutes"),
            "start_step" : start_index  + 1,
            "active_step": active_index + 1,
            "soc_start"  : soc_start_kwh,
            
            # Current Strategy and Power values for the active step (current period)
            # Remark: Plan is in kW but Current is in Watt
            "current": {
                "strategy": current_strat, 

                "net_battery_power_w": net_w,      # Net Battery Power in W: Charge is Positive (+), Discharge is Negative (-)
                "battery_power_w"    : abs(net_w), # Battery Power in Watt is always positive (for Charging and Discharging), absolute value of net
                "charge_power_w"     : (net_w      if net_w > 0 else 0),  # Charge    is only applicable when net battery power is positive
                "discharge_power_w"  : (abs(net_w) if net_w < 0 else 0),  # Discharge is only applicable when net battery power is negative

                # Previous battery power values (no longer used):
#               "battery_power_w"  : 1000 * max(bat_charge_plan[active_index], bat_discharge_plan[active_index]), 
#               "charge_power_w"   : 1000 * bat_charge_plan[active_index],
#               "discharge_power_w": 1000 * bat_discharge_plan[active_index],

                "grid_w"           : 1000 * (grid_import_plan[active_index] - grid_export_plan[active_index]), # Net Grid Power in Watt
                "ev_power_w"       : 1000 * ev_plan[active_index],
                "hp_power_w"       : 1000 * hp_plan[active_index],
                "boiler_power_w"   : 1000 * boiler_plan[active_index]
            },

            # Volledige dagplanning voor kaarten/grafieken
            # Per stap: timestamps, strategie, batterij soc percentage en soc kWh
            #  overige plannen in kW per stap
            "plan": {
                "timestamp": timestamps,
                "strategy": strategy_plan,
                "soc_pct": soc_pct_plan,
                "soc_kwh": soc_kwh_plan,
                "grid_import_kw": grid_import_plan,
                "grid_export_kw": grid_export_plan,
                "solar_kw": solar_plan,
                "house_kw": house_plan,
                "battery_charge_kw": bat_charge_plan,
                "battery_discharge_kw": bat_discharge_plan,
                "ev_charge_kw": ev_plan,
                "heat_pump_kw": hp_plan,
                "boiler_kw": boiler_plan
            }
        }

        state.set(
            "sensor.energy_optimization_plan",
            value=current_strat,
            new_attributes=full_payload
        )

        log.info(f"Energie optimalisatie succesvol uitgevoerd in {execution_time_ms} ms (start_step={start_index + 1}).")
        
        # Volledige data teruggeven aan de Trace
        return full_payload

    else:
        log.error(f"Energy Optimizer mislukt: {res.message}")
        error_payload = {
            "success": False,
            "error": res.message
        }
        return error_payload

