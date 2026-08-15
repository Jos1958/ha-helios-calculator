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

@service
def helios_calc_home_energy(
    steps=24,
    step_size=60,
    import_prices=None,
    export_prices=None,
    house_forecast=None,
    grid_max_import=17.0,
    grid_max_export=17.0,
    battery=None,
    solar=None,
    ev=None,
    hp=None,
    boiler=None
):
    """
    Home Assistant Energy Optimizer Service via SciPy Linear/MILP Programming.
    """
    # -------------------------------------------------------------------
    # 0. VALIDATIE EN TIJDSFACTOR
    # -------------------------------------------------------------------
    if not import_prices or not export_prices or not house_forecast:
        log.error("Optimizer: import_prices, export_prices en house_forecast zijn verplicht!")
        return

    # Omrekenfactor van vermogen (kW) naar energie (kWh) per stap
    dt = step_size / 60.0  # bijv. 60 min -> 1.0, 15 min -> 0.25
    T = int(steps)

    # Validate input lengtes
    if len(import_prices) < T or len(export_prices) < T or len(house_forecast) < T:
        log.error(f"Optimizer: Input reeksen moeten minimaal {T} elementen lang zijn.")
        return

    # -------------------------------------------------------------------
    # 1. INDEX BEHEER EN VARIABELEN OPBOUWEN
    # -------------------------------------------------------------------
    # Elk uur heeft sowieso Import en Export
    vars_per_step = ["import", "export"]
    
    # Optionele variabelen toevoegen
    if battery: vars_per_step.extend(["bat_charge", "bat_discharge"])
    if solar and solar.get("enabled", True): vars_per_step.append("solar_power")
    if ev and ev.get("enabled", True): vars_per_step.append("ev_charge")
    if hp and hp.get("enabled", True): vars_per_step.append("hp_power")
    if boiler and boiler.get("enabled", True): vars_per_step.append("boiler_power")

    n_vars_per_step = len(vars_per_step)
    total_vars = T * n_vars_per_step

    def get_idx(step, var_name):
        """Helper om de exacte index van een variabele te vinden in de x-matrix"""
        return step * n_vars_per_step + vars_per_step.index(var_name)

    # Arrays voor SciPy opzetten
    c = np.zeros(total_vars)
    bounds = [(0, None)] * total_vars
    integrality = [0] * total_vars

    A_eq, b_eq = [], []
    A_ub, b_ub = [], []

    # -------------------------------------------------------------------
    # 2. BOUNDS, INTEGRALITY EN DOELFUNCTIE (c)
    # -------------------------------------------------------------------
    for t in range(T):
        # Net Import & Export
        idx_imp = get_idx(t, "import")
        idx_exp = get_idx(t, "export")
        bounds[idx_imp] = (0, grid_max_import)
        bounds[idx_exp] = (0, grid_max_export)
        c[idx_imp] = import_prices[t] * dt
        c[idx_exp] = -export_prices[t] * dt  # Export levert geld op (negatief)

        # Batterij
        if battery:
            c_p = battery.get("charge_power", 3.0)
            d_p = battery.get("discharge_power", 3.0)
            bounds[get_idx(t, "bat_charge")] = (0, c_p)
            bounds[get_idx(t, "bat_discharge")] = (0, d_p)

        # Zonne-energie (Curtailment optie)
        if solar and solar.get("enabled", True):
            max_sol = solar.get("forecast", [0]*T)[t]
            bounds[get_idx(t, "solar_power")] = (0, max_sol)

        # EV (Elektrische Auto)
        if ev and ev.get("enabled", True):
            is_connected = ev.get("connected_schedule", [True]*T)[t]
            max_ev_p = ev.get("max_power", 11.0) if is_connected else 0.0
            bounds[get_idx(t, "ev_charge")] = (0, max_ev_p)

        # Warmtepomp
        if hp and hp.get("enabled", True):
            idx_hp = get_idx(t, "hp_power")
            if hp.get("mode", "MODULATING") == "ON_OFF":
                bounds[idx_hp] = (0, 1)
                integrality[idx_hp] = 1  # Binary / Integer
            else: # MODULATING
                min_p = hp.get("min_power", 0.0)
                max_p = hp.get("max_power", 2.5)
                bounds[idx_hp] = (0, max_p)

        # Boiler
        if boiler and boiler.get("enabled", True):
            idx_b = get_idx(t, "boiler_power")
            if boiler.get("mode", "ON_OFF") == "ON_OFF":
                bounds[idx_b] = (0, 1)
                integrality[idx_b] = 1  # Binary
            else:
                bounds[idx_b] = (0, boiler.get("max_power", 2.0))

    # -------------------------------------------------------------------
    # 3. VERMOGENSBALANS PER TIJDSSTAP (A_eq)
    # Import - Export - Charge + Discharge + Solar - EV - HP - Boiler = House
    # -------------------------------------------------------------------
    for t in range(T):
        row = np.zeros(total_vars)
        row[get_idx(t, "import")] = 1.0
        row[get_idx(t, "export")] = -1.0
        
        if battery:
            row[get_idx(t, "bat_charge")] = -1.0
            row[get_idx(t, "bat_discharge")] = 1.0
        if solar and solar.get("enabled", True):
            row[get_idx(t, "solar_power")] = 1.0
        if ev and ev.get("enabled", True):
            row[get_idx(t, "ev_charge")] = -1.0
        if hp and hp.get("enabled", True):
            row_val = -hp.get("nominal_power", 1.5) if hp.get("mode") == "ON_OFF" else -1.0
            row[get_idx(t, "hp_power")] = row_val
        if boiler and boiler.get("enabled", True):
            row_val = -boiler.get("nominal_power", 2.0) if boiler.get("mode") == "ON_OFF" else -1.0
            row[get_idx(t, "boiler_power")] = row_val

        A_eq.append(row)
        b_eq.append(house_forecast[t])

    # -------------------------------------------------------------------
    # 4. CUMULATIEVE & TOTAAL REGELS (A_ub en A_eq)
    # -------------------------------------------------------------------
    # A. BATTERIJ SOC GRENZEN (A_ub)
    if battery:
        cap = battery.get("capacity", 10.0)
        soc_start = battery.get("soc_start", 2.0)
        eff = battery.get("efficiency", 0.95)

        for t in range(1, T + 1):
            row_max = np.zeros(total_vars)
            row_min = np.zeros(total_vars)
            for i in range(t):
                row_max[get_idx(i, "bat_charge")] = eff * dt
                row_max[get_idx(i, "bat_discharge")] = -(1.0 / eff) * dt
                row_min[get_idx(i, "bat_charge")] = -eff * dt
                row_min[get_idx(i, "bat_discharge")] = (1.0 / eff) * dt
            
            # Max capaciteit niet overschrijden
            A_ub.append(row_max)
            b_ub.append(cap - soc_start)
            # Niet onder 0 kWh zakken
            A_ub.append(row_min)
            b_ub.append(soc_start)

    # B. EV TARGET SOC (A_eq)
    if ev and ev.get("enabled", True) and "target_kwh" in ev:
        row_ev = np.zeros(total_vars)
        needed_kwh = max(0.0, ev["target_kwh"] - ev.get("soc_start", 0.0))
        for t in range(T):
            row_ev[get_idx(t, "ev_charge")] = 1.0 * dt
        A_eq.append(row_ev)
        b_eq.append(needed_kwh)

    # C. WARMTEPOMP MINIMALE ENERGIE / UREN (A_ub)
    if hp and hp.get("enabled", True) and "min_hours" in hp:
        row_hp = np.zeros(total_vars)
        min_kwh = hp["min_hours"] * hp.get("nominal_power", 1.5)
        for t in range(T):
            factor = hp.get("nominal_power", 1.5) if hp.get("mode") == "ON_OFF" else 1.0
            row_hp[get_idx(t, "hp_power")] = -1.0 * factor * dt
        A_ub.append(row_hp)
        b_ub.append(-min_kwh)

    # D. BOILER MINIMALE ENERGIE / UREN (A_ub)
    if boiler and boiler.get("enabled", True) and "min_hours" in boiler:
        row_b = np.zeros(total_vars)
        min_kwh = boiler["min_hours"] * boiler.get("nominal_power", 2.0)
        for t in range(T):
            factor = boiler.get("nominal_power", 2.0) if boiler.get("mode") == "ON_OFF" else 1.0
            row_b[get_idx(t, "boiler_power")] = -1.0 * factor * dt
        A_ub.append(row_b)
        b_ub.append(-min_kwh)

    # -------------------------------------------------------------------
    # 5. SCIPY SOLVER AANROEPEN
    # -------------------------------------------------------------------
    res = linprog(
        c,
        A_ub=A_ub if A_ub else None,
        b_ub=b_ub if b_ub else None,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        integrality=integrality if any(integrality) else None,
        method="highs"
    )

    # -------------------------------------------------------------------
    # 6. RESULTAAT VERWERKEN EN IN HOME ASSISTANT ZETTEN
    # -------------------------------------------------------------------
    if res.success:
        plan = {var: [] for var in vars_per_step}
        for t in range(T):
            for var in vars_per_step:
                val = round(float(res.x[get_idx(t, var)]), 2)
                plan[var].append(val)

        total_cost = round(float(res.fun), 2)
        
        # Sla op in een Home Assistant sensor
        state.set(
            "sensor.energy_optimization_plan",
            value=f"€{total_cost}",
            attributes={
                "total_cost_eur": total_cost,
                "steps": T,
                "step_size_min": step_size,
                "plan": plan
            }
        )
        log.info(f"Optimalisatie geslaagd! Berekende net-kosten: €{total_cost}")
    else:
        log.error(f"Optimalisatie mislukt. Reden: {res.message}")

    return plan