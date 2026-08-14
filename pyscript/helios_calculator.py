import numpy as np
from scipy.optimize import linprog

# Module: HELIOS Calculator - Python Function to Calculate an Optimized Energy Plan                            
# Home Energy Linear Integrated Optimization Service (HELIOS Calculator)
# The Optimizer uses SciPy Linear/MILP Programming to calculated the Optimal Energy Plan 
#
# Created by: Jos Raaijmakers
# Log: 
#   2026-05-19: JR: V0.1  Started Implementation with help of Google Gemini

@service
def helios_calc_battery_schedule():
    # 1. Prijzen ophalen (bijv. komende 24 uur in centen/kWh)
    # Dit kun je dynamisch uit een HA sensor trekken
    prices = [15, 12, 10, 8, 9, 14, 22, 30, 28, 25, 20, 18, 
              16, 15, 14, 18, 25, 35, 40, 32, 22, 18, 16, 14]
    
    T = len(prices) # 24 uur
    
    # 2. Beslissingsvariabelen (2 parameters per uur):
    # x[0..23]  = Vermogen geladen (kW)
    # x[24..47] = Vermogen ontladen (kW)
    c = np.concatenate([prices, -np.array(prices)]) # Doelfunctie: minimaliseer kosten
    
    # Maximaal vermogen om te (ont)laden: bijv. max 3.0 kW per uur
    max_kw = 3.0
    bounds = [(0, max_kw) for _ in range(2 * T)]
    
    # 3. Batterij restricties (Capaciteit & Efficientie)
    battery_capacity_kwh = 10.0
    initial_soc_kwh = 2.0 # Huidige lading
    efficiency = 0.90 # 90% rendement
    
    # Formule: SOC_t = Start + sum(Laden * eff) - sum(Ontladen / eff)
    # Beperking: 0 <= SOC_t <= Max_capaciteit
    A_ub = []
    b_ub = []
    
    for t in range(1, T + 1):
        # Lading t/m uur t
        charge_row = [efficiency if i < t else 0 for i in range(T)]
        # Ontlading t/m uur t
        discharge_row = [-(1.0 / efficiency) if i < t else 0 for i in range(T)]
        
        row = charge_row + discharge_row
        
        # Maximale capaciteit niet overschrijden: SOC_t <= Capacity
        A_ub.append(row)
        b_ub.append(battery_capacity_kwh - initial_soc_kwh)
        
        # Niet onder 0 kWh zakken: -SOC_t <= 0
        A_ub.append([-val for val in row])
        b_ub.append(initial_soc_kwh)

    # 4. Los het probleem op met de HiGHS solver
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

    if res.success:
        charge_plan = res.x[:T]
        discharge_plan = res.x[T:]
        
        log.info(f"Optimalisatie geslaagd! Verwachte kosten: {res.fun:.2f}")
        
        # Sla het resultaat op in een Home Assistant Sensor
        state.set(
            "sensor.battery_optimal_charge_power",
            value=round(charge_plan[0], 2),
            attributes={"full_schedule": charge_plan.tolist()}
        )
    else:
        log.error(f"Optimalisatie mislukt: {res.message}")
