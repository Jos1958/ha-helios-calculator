import time
from datetime import datetime, timedelta
import numpy as np                            # Numeric Pyscript Library (includes numeric array) 
from scipy.optimize import linprog            # Scientific Pyscript Library for LP

# Module: HELIOS Optimize Energy Service                            Version: 0.5
# Home Energy Linear Integrated Optimization System (HELIOS):
# A Home Assistant Energy Optimizer Module that uses SciPy Linear/MILP Programming
# to calculated the optimized Energy Plan for Solar production, Battery Charging/Discharging
# and House Energy Usage for dynamic prices during the period.
# A House Forecast is specified with the undeferrable energy usage in the house.
# In the future support for Deferrable Devices (like EV, HP and Boiler) will be added. 
#
# Created by: Jos Raaijmakers
# Log: 
#   2026-05-19: JR: V0.1 Started Implementation with help of Google Gemini
#   2026-05-20: JR: V0.2 Balance Rule included
#   2026-06-23: JR: V0.3 Input arrays as parameters for the service, automation calls the service
#   2026-06-24: JR: V0.4 Battery Configuration
#   2026-06-28: JR: v0.5 Created HBC lab page with plan results (status, graph, table) using apexchart and markdown cards
#
# Description:
# Calculates an optimized energy plan for a specified horizon (typically 1 to 2 days)
# by finding the optimal power setpoints for each interval.
# 
# The planning horizon is defined by the number of steps and the step duration in minutes.
# For example: 24 steps of 60 minutes optimizes a 1-day period.
# 
# Grid import/export prices and house load forecasts must be provided as input arrays,
# containing values for every step in the period.
# 
# Total Energy Cost is the sum of energy costs per step (calculated from grid import and export power).
# The optimizer aims to MINIMIZE the Total Energy Cost over the entire horizon.
# Note: Negative costs may occur when exporting energy to the grid or during negative import prices.
# 
# Note: Without a battery or deferrable loads, optimization opportunities are limited
# since a strict power balance between consumption, import, and export must be met in each step.
# 
# The optimization horizon always starts today (and optionally extends to following days).
# By default, the active start step is calculated based on the current time.
# Optionally, a specific start step can be defined (e.g., step 1 to start at 00:00).
# All input arrays must start at 00:00 today so the optimizer can align prices and forecasts correctly.
# 
# The resulting Optimized Energy Plan determines the active strategy for the current step
# (e.g., NOM, Buy, Sell, Charge, Discharge, Disabled) and provides real-time setpoints
# to steer the battery and (TODO) deferrable loads.
# 
# Required inputs:
#  - Configuration (steps, step size, start step, solver time/iteration limits, grid limits)
#  - Grid import prices array
#  - Grid export prices array
#  - House consumption forecast array
# 
# Optional inputs:
#  - Solar production forecast array
#  - Battery parameters
# 
# Optional deferrable loads (TODO):
#  - Electric Vehicle (EV) charging profile
#  - Heat Pump (HP) operation parameters
#  - Boiler operation parameters
#
# Function List (V=Implemented, -=Todo):
# V Optimizer: Solve the optimized energy plan using a SciPy Lineair Programming with the HiGHs solver
# V Optimizer: First implementation has a fixed price array (for charging and discharge) and optimizes the cost
# V Rules: In each step the SoC of the battery much be above 0 and below the maximum capacity 
# V Payload: Return the optimized energy plan in a Home Assistant Entity/Attributes
# V Payload: Return infeasible status with message and success indicator, runtime, iteration steps
# V Payload: Built payload with optimization status and plan to return to HA Entity
# V Optimizer: Include House Usage, Grid Import and Export and Solar Production variables in the rules
# V Optimizer: Balance rule is introduced since House Usage, Solar Production, Grid Import/Export and Battery Charging/Discharging must be in balance 
# V Cost: Costs are calculated for the the Grid Import and Export instead of for the Charging/Discharging
# V Grid Configuration: Values for Max and Min Grid Power 
# V Input: Prices and House and Solar Forecasts are now parameters for the service (iso fixed arrays) 
# V Payload: Current values are returned in the payload for the active step in Watt (iso kW in the plan)
# V Payload: Calculate the Battery SoC % and Energy (kWh) and return in the result 
# V Input: Solver configuration for max iterations and runtime
# V Payload: Return the result as a response to the service (can now be viewed/used in the HA Automation)
# 
# V Battery Configuration: Effectivity, SoC (Min, Max, Start and End), Max Charge/Discharge Power
# V Error Handling: Protect against infeasible solution with Min and Max and invalid SoC Start
# V Error Handling: Protect against infeasible solution with SoC End that is not reachable for remaining steps and max charge power
# V Payload: Created a Battery Strategy from the Optimized Plan (still needs to be improved)
# V Payload: Handle parallel charging and discharging in the current values (but not in the plan) 
# - Optimizer: Introduced charging and discharge costs to prevent the above, still needs to be configurable
# - Limit recorder for the output entity (see google gemini thread)
#
# - HBC Interface (to be discussed with Bob):
#   - What is the status of the next version of HBC?
#   - Environment: PyScript, Node-Red, HACS (?)
#   - HBC User Interface / Tab for Optimizer
#   - Helios as additional Strategy for HBC
#   - Input: Prices (Import and Export), Solar Forecast, House Forecast, Other Configuration
#   - Output: Status, Plan, Current (Strategy, Battery Power) 
#   - How to handle Energy Providers / Cheapest Hours, no export prices yet
#   - How to handle Solar Forecast Integrations, currently in HBC only today and tomorrow forecast
#   - How to divide the responsibilities between HBC and Helios
#
# - Development: Create a version that can run in Visual Studio for debugging
# - Adding additional comment in the code and replace all dutch comments by english (ongoing task)
# - Testing: Validation of the cost function and check that a good optimal solution has been calculated
# - Testing: Calculate the cost of other solution to be proof that an ideal solution has been found
# - Testing: Run with several datasets and determine expected result

# - Input: Day handling instead of number of steps, fixed horizons (in days) 
# - Conversion (multiply, combine or split) of arrays to adapt to the requested steps and step size
# - Error handling: Return a result with an error message when an exception occurs
# - Input: Validation of input values and length of the input arrays against number of steps
# - Optimizer: Binary (Disable) or modulating (Dim) Solar Production
# - Input: Implement separate efficiency for charging and discharging
# - Input: Handle specific solar forecast integrations (e.g. forecast.solar API), array with hour forecast required
# - Input: Keep history of house usage per hour or 15min (for house forecast)
# - Optimizer: Implement Electical Vehicle (EV) Charging, ready before date/time (next day or later)
# - Optimizer: Implement Heat Pump (HP) Device with required minimum kWh and already applied Energy per day
# - Optimizer: Implement Boiler Device with required minimum kWh and already applied Energy per day
# - Optimizer: Implement other deferrable devices
# - Payload: Device Strategy for other Devices (like Battery Strategy) 
# - Optimer: Disable Battery Discharging during EV Charging

# HeliosOptimize Energy Service with a return response
@service(supports_response="optional") 
def helios_calc_home_energy(
    steps=24,      # 24 steps for 60 minutes is one day,  48 steps is two days
    step_size=60,  # 96 steps for 15 minutes is one day, 192 steps is two days
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
    return_response=None # Return a result
):
    """
    Home Energy Linear Integrated Optimization System (HELIOS):
    A Home Assistant Energy Optimizer Service that uses SciPy Linear/MILP Programming.
    """

    T = int(steps)
    dt = float(step_size) / 60.0
    start_index = int(start_step) - 1 # Start Index (0..T-1), while Start Step (1..T)

    # -------------------------------------------------------------------
    # 0. TIME LOGIC & AUTOMATIC START_INDEX Calculation (based on current time)
    # -------------------------------------------------------------------
    now = datetime.now()
    base_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) # Start optimization at 00:00 today

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

    bat_enabled    = bool(battery   and battery.get  ("enabled", True ))
    ev_enabled     = bool(ev        and ev.get       ("enabled", False))
    hp_enabled     = bool(heat_pump and heat_pump.get("enabled", False))
    boiler_enabled = bool(boiler    and boiler.get   ("enabled", False))

    # -------------------------------------------------------------------
    # 2. BUILT DYNAMIC INDEX-MAP for optimization variables array
    # -------------------------------------------------------------------
    active_vars = ["import", "export"] # every optimization has an import an an export variable type
    if bat_enabled: # battery applicable?
        active_vars.extend(["bat_charge", "bat_discharge"]) # add a charge and a discharge variable type
    if ev_enabled:
        active_vars.append("ev_charge")
    if hp_enabled:
        active_vars.append("hp_power")
    if boiler_enabled:
        active_vars.append("boiler_power")

    var_offset = {name: i for i, name in enumerate(active_vars)}
    M = len(active_vars) # Number of variable types
    total_vars = T * M # total number of variables (steps * variable types)

    # Function to determine the index in the variable array
    # Input is the step index and the variable type
    # Each variable type exist in the array once for each step
    # Return the array index
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
        bounds[idx_imp] = (0, 0) if is_past else (0, float(grid_max_import))
        bounds[idx_exp] = (0, 0) if is_past else (0, float(grid_max_export))
        c[idx_imp] =  import_prices[t] * dt # Cost factor per imported kWh
        c[idx_exp] = -export_prices[t] * dt # Cost factor per exported kWh

        # Battery: 
        if bat_enabled:
            idx_chg = get_idx(t, "bat_charge")
            idx_dis = get_idx(t, "bat_discharge")
            c_p = 0.0 if is_past else float(battery.get("charge_power_kw", 3.0))
            d_p = 0.0 if is_past else float(battery.get("discharge_power_kw", 3.0))
            bounds[idx_chg] = (0, c_p)
            bounds[idx_dis] = (0, d_p)

            # Give charging and discharging a small cost 
            # TODO: Make the charging and discharging cost configurable
            # 0.0001 per kWh did not work so now using 0.01 for discharge only
            # This will prevent the solver to charge and discharge at the same time!
            if not is_past:
                c[idx_chg] = 0.000 * dt # Cost factor for charged kWh
                c[idx_dis] = 0.010 * dt # Cost factor for discharged kWh
        
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
    # 5. BATTERIJ SOC LIMITATIONS & BORDERLINE CASES (A_ub, b_ub)
    # -------------------------------------------------------------------
    # Start the optimization with the specified start SoC
    # Optionally end the optimization above the specified end SoC
    # Keep the battery above the minimum SoC and below the maximum SoC
    # Handle the special case when the start SoC is outside the min, max SoC
    # Handle the border line case when the end SoC is not reachable in the optimization period

    A_ub = []
    b_ub = []

    if bat_enabled:
        cap = float(battery.get("capacity_kwh", 10.0))
        eff = float(battery.get("efficiency"  , 0.95))

        soc_start_pct = float(battery.get("soc_start_pct", 20.0))
        soc_start_kwh = (soc_start_pct / 100.0) * cap

        soc_min_pct = float(battery.get("soc_min_pct", 15.0))
        soc_max_pct = float(battery.get("soc_max_pct", 85.0))
        
        soc_min_kwh = (soc_min_pct / 100.0) * cap
        soc_max_kwh = (soc_max_pct / 100.0) * cap

        # A. Retrieve Maximum Power (Charge and Discharge):
        max_charge_power    = float(battery.get("charge_power_kw"   , 3.0))
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
        # - Keep the sum of the Charged kWh    - Discharged kWh below SOC-Max - SOC-Start
        # - Keep the sum of the Discharged kWh - Charged kWh    above SOC-Start - SOC-Min
        # The Sum per step includes in every next step an extra step charge or discharge
        # No rules are added for the steps that are before the start step
        # To prevent infeasible SOC-Min or SOC-Max rules: 
        #   Adapt the SOC-Min and SOC-Max for an under-charged (below SOC-Min) or over-charged (above SOC-Max) battery
        #   when the max charge or max discharge power is insufficient to reach the minimum or maximum SOC during the step.
        for t in range(1, T + 1):
            if t <= start_index:
                continue # Current step is before the start index

            steps_from_start = t - start_index # steps handle since start index

            # When starting above SOC-Max we cannot discharge faster than the max discharge power:
            max_discharge_kwh = steps_from_start * (max_discharge_power / eff) * dt
            step_allowed_max_kwh = max(soc_max_kwh, soc_start_kwh - max_discharge_kwh)

            # When starting below the SOC-Min, we cannot charge faster than the max charge power:
            max_charge_kwh = steps_from_start * (max_charge_power * eff) * dt
            step_allowed_min_kwh = min(soc_min_kwh, soc_start_kwh + max_charge_kwh)

            # Initiate the multipliers of the maximum and minimum rule with 0's (future steps are excluded from the sum)
            row_max = np.zeros(total_vars)
            row_min = np.zeros(total_vars)

            # Fill the multipliers for all steps until and including the current step
            # Remark: The sum includes the skipped steps (before the start step) but the charge and discharge values for these steps will be zero anyway
            for i in range(t):
                row_max[get_idx(i, "bat_charge"   )] = eff * dt
                row_max[get_idx(i, "bat_discharge")] = -(1.0 / eff) * dt
                row_min[get_idx(i, "bat_charge"   )] = -eff * dt
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
    # 6. Call SCIPY with HiGHs SOLVER
    # -------------------------------------------------------------------
    solver_options = { # Solver time and iteration limits
        "time_limit": float(max_time),
        "maxiter": int(max_iterations)
    }

    t_start = time.perf_counter() # Start of LP run

    # Calculate with LP the optimal values of the optimization variables
    # Calculate the cost as the sum of the cost per step
    # Each optimization variable has its own cost factor (valid in all steps)
    # Stick to the ('<=' and '=') rules as defined for the variables
    # Keep the variables within the specified boundaries for each step
    # The Optimal solution has the lowest cost value (all steps together)
    res = linprog(
        c,                           # Cost factors per optimization variable
        A_ub=A_ub if A_ub else None, # Left  side of smaller or equal (<=) rules
        b_ub=b_ub if b_ub else None, # Right side of smaller or equal (<=) rules
        A_eq=A_eq,                   # Left  side of = rules
        b_eq=b_eq,                   # Right side of equal (=) rules
        bounds=bounds,               # Boundaries for the optimization variables
        method="highs",              # LP method
        options=solver_options       # Solver time and iteration limits
    )

    t_end = time.perf_counter() # End of LP run
    execution_time_ms = round((t_end - t_start) * 1000, 2) # calculate execution time

    # -------------------------------------------------------------------
    # 7. PROCESS RESULTS and DETERMINE STRATEGIES
    # -------------------------------------------------------------------
    if res.success:
        # Initialize the output arrays:
        timestamps = []
        solar_plan, house_plan = [], []
        grid_import_plan, grid_export_plan = [], []
        bat_charge_plan, bat_discharge_plan = [], []
        ev_plan, hp_plan, boiler_plan = [], [], []
        soc_pct_plan, soc_kwh_plan = [], []
        strategy_plan = []

        current_soc_kwh = soc_start_kwh if bat_enabled else 0.0

        step_dt = base_dt # Start at 00:00 today
        for t in range(T): # for each step get variables from the optimization:
            timestamps.append(step_dt.isoformat(timespec="minutes")) # Timestamp for start of next step

            # Use Solar and House Power from the Forecasts:
            sol   = round(solar_forecast[t], 2)
            house = round(house_forecast[t], 2)

            # Use Import, Export from the optimized variables
            imp    = round(float(res.x[get_idx(t, "import"       )]), 2)
            exp    = round(float(res.x[get_idx(t, "export"       )]), 2)

            # Use Battery Charge and Discharge Power from the optimized variables (but only when the battery is enabled)
            c_p    = round(float(res.x[get_idx(t, "bat_charge"   )]), 2) if bat_enabled    else 0.0
            d_p    = round(float(res.x[get_idx(t, "bat_discharge")]), 2) if bat_enabled    else 0.0

            # Use Deferrable Devices Power from the optimized variables (but only when the deferrable devices is enabled)
            ev_p   = round(float(res.x[get_idx(t, "ev_charge"    )]), 2) if ev_enabled     else 0.0
            hp_p   = round(float(res.x[get_idx(t, "hp_power"     )]), 2) if hp_enabled     else 0.0
            boil_p = round(float(res.x[get_idx(t, "boiler_power" )]), 2) if boiler_enabled else 0.0

            # Calculate Battery SoC % and KWh per step:
            if bat_enabled: # Is battery enabled?
                delta_kwh = (c_p * eff - d_p / eff) * dt
                current_soc_kwh = max(0.0, min(cap, current_soc_kwh + delta_kwh))
                current_soc_pct = round((current_soc_kwh / cap) * 100.0, 1)
            else: # battery not enabled
                current_soc_pct = 0.0

            # Determine (Battery) Strategy (with 'Skipped' for skipped steps)
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

            # Append variable value for the step to the arrays:
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
        soc_end_kwh = current_soc_kwh
        
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
            # Optimization/Solver Result and Timing: 
            "success": True,
            "friendly_name": "Helios Energy Plan",
            "total_cost_eur": round(float(res.fun), 2),
            "last_run_started": now.isoformat(),
            "last_run_stopped": datetime.now().isoformat(),
            
            "solver_execution_time_ms": execution_time_ms,
            "solver_iterations": res.nit,
            "solver_status": res.message,
            
            "start_time" : base_dt.isoformat(timespec="minutes"),
            "active_time": active_time,
            "end_time"   : end_dt.isoformat(timespec="minutes"),
            "start_step" : start_index  + 1,
            "active_step": active_index + 1,
            "soc_start"  : soc_start_kwh,
            "soc_end"    : soc_end_kwh,
            
            # Current Strategy and Power values for the active step (current period)
            # Remark: Plan is in kW but Current is in Watt
            "current": {
                "strategy": current_strat, # Battery Strategy 

                "net_battery_power_w": net_w,      # Net Battery Power in W: Charge is Positive (+), Discharge is Negative (-)
                "battery_power_w"    : abs(net_w), # Battery Power in Watt is always positive (for Charging and Discharging), absolute value of net
                "charge_power_w"     : (net_w      if net_w > 0 else 0),  # Charge    is only applicable when net battery power is positive
                "discharge_power_w"  : (abs(net_w) if net_w < 0 else 0),  # Discharge is only applicable when net battery power is negative

                "grid_w"           : 1000 * (grid_import_plan[active_index] - grid_export_plan[active_index]), # Net Grid Power in Watt
                "ev_power_w"       : 1000 * ev_plan[active_index],
                "hp_power_w"       : 1000 * hp_plan[active_index],
                "boiler_power_w"   : 1000 * boiler_plan[active_index]
            },

            # Complete Dayplanning for Tables/Graphs and for Testing
            # Per Step: Timestamps, Strategie, Batterij SoC percentage and SoC kWh
            #  other plan values in kW per step
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
            "pyscript.helios_energy_plan",
            value=current_strat,
            new_attributes=full_payload
        )

        log.info(f"Energy Optimalizer succesfully executed in {execution_time_ms} ms (start_step={start_index + 1}).")
        
        # Return Full Payload to the Service Trace
        return full_payload

    else:
        log.error(f"Energy Optimizer failed: {res.message}")
        error_payload = {
            "success": False,
            "error": res.message
        }

@service
def helios_start_optimizer():
    # 1. Turn on the helios optimizer running status (switches the button to orange)
    state.set("pyscript.helios_optimizer_running", "on", friendly_name="Helios Status")
    
    # 2. Start the automation (which also provides the input parameters for the above service)
    automation.trigger(entity_id="automation.helios_optimize_energy")
    
    # 3. Wait an extra 1 second otherwise the color change will not be visible
    task.sleep(1)
    
    # 4. Turn off the helios optimizer running status (switches the button back to green)
    state.set("pyscript.helios_optimizer_running", "off", friendly_name="Helios Status")
