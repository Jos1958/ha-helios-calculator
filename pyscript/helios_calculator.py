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

@service
def helios_calc_home_energy():
    T = 8 # 24 uur
    
    # -------------------------------------------------------------------
    # 1. INPUT DATA (Haal dit uit je HA sensoren / voorspellingen)
    # -------------------------------------------------------------------
    import_prices  = [0.25, 0.20, 0.18, 0.15, 0.16, 0.22, 0.35, 0.37] # 24 prijzen (€/kWh)
    export_prices  = [0.08, 0.05, 0.03, 0.01, 0.02, 0.06, 0.15, 0.22] # 24 vergoedingen (€/kWh)
    
    solar_forecast = [0   , 0   , 0   , 0   , 0.5 , 1.2 , 2.5 , 3.8 ] # 24 uurs voorspelling (kW)
    house_forecast = [0.4 , 0.3 , 0.3 , 0.4 , 0.6 , 1.2 , 0.8 , 2.4 ] # 24 uurs verbruik (kW)

    # -------------------------------------------------------------------
    # 2. DOELFUNCTIE (c) - 96 Variabelen
    # Structure: [Charge (24x), Discharge (24x), Import (24x), Export (24x)]
    # -------------------------------------------------------------------
    c_charge = [0] * T             # Batterij laden kost op zichzelf niks (gaat via import)
    c_discharge = [0] * T          # Ontladen kost niks
    c_import = import_prices       # Import kost geld (positief)
    c_export = [-p for p in export_prices] # Export levert geld op (negatief)
    
    c = np.concatenate([c_charge, c_discharge, c_import, c_export])

    # -------------------------------------------------------------------
    # 3. BALANSREGEL (A_eq en b_eq): Import - Export - Charge + Discharge = Huis - Zon
    # -------------------------------------------------------------------
    A_eq = []
    b_eq = []
    
    for t in range(T):
        row = [0] * (4 * T)
        
        row[t] = -1         # -Charge[t]
        row[T + t] = 1      # +Discharge[t]
        row[2*T + t] = 1    # +Import[t]
        row[3*T + t] = -1   # -Export[t]
        
        A_eq.append(row)
        
        # Vaste waarde aan de rechterkant:
        netto_vraag = house_forecast[t] - solar_forecast[t]
        b_eq.append(netto_vraag)

    # -------------------------------------------------------------------
    # 4. BATTERIJSPECIFICATIES (A_ub en b_ub voor de accu grenzen)
    # -------------------------------------------------------------------
    A_ub = []
    b_ub = []
    battery_max = 10.0  # kWh
    soc_start = 2.0     # kWh
    
    for t in range(1, T + 1):
        row = [0] * (4 * T)
        # Tellen alleen Charge en Discharge mee tot uur t
        for i in range(t):
            row[i] = 1        # +Charge
            row[T + i] = -1   # -Discharge
            
        A_ub.append(row)
        b_ub.append(battery_max - soc_start) # Max capaciteit
        
        # Ook de 'niet onder 0 kWh zakken' regel toevoegen:
        A_ub.append([-val for val in row])
        b_ub.append(soc_start)

    # -------------------------------------------------------------------
    # 5. GRENZEN PER KNOP (Bounds)
    # -------------------------------------------------------------------
    bounds_charge = [(0, 3.0) for _ in range(T)]     # Max 3 kW laden
    bounds_discharge = [(0, 3.0) for _ in range(T)]  # Max 3 kW ontladen
    bounds_import = [(0, 17.0) for _ in range(T)]    # Max aansluiting (bijv. 3x25A = 17kW)
    bounds_export = [(0, 17.0) for _ in range(T)]    # Max terugleveren
    
    bounds = bounds_charge + bounds_discharge + bounds_import + bounds_export

    # -------------------------------------------------------------------
    # 6. OPLOSSEN
    # -------------------------------------------------------------------
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

    if res.success:
        import_plan = res.x[2*T : 3*T]
        export_plan = res.x[3*T : 4*T]
        
        log.info(f"Optimalisatie geslaagd! Verwachte kosten: {res.fun:.2f}")
        
        # Sla het resultaat op in een Home Assistant Sensor
        state.set(
            "sensor.battery_optimal_charge_power",
            value=round(res.fun, 2),
            attributes={"import_plan": import_plan.tolist()}
        )
    else:
        log.error(f"Optimalisatie mislukt: {res.message}")
