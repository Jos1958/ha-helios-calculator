import time
import logging
import scipy

from typing import Any
from scipy.optimize import linprog

_LOGGER = logging.getLogger(__name__)

def solve_optimize_energy_cost(start_time: string, demand: float, price_low: float, price_high: float) -> dict[str, Any]:
    """Synchronous, CPU-intensive function that executes SciPy HiGHS."""
    t_start = time.perf_counter()
    
    c = [price_low, price_high, 0.05]
    A_ub = [[-1.0, -1.0, -1.0]]
    b_ub = [-demand]
    bounds = [(0, 10), (0, None), (0, 8)]

    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    execution_time = (time.perf_counter() - t_start) * 1000

    if not result.success:
        _LOGGER.error("HiGHS solver failed: %s", result.message)
        return {"success": False, "error": result.message}

    return {
        "success": True,
        "scipy": f"SciPy: {scipy.__version__}", 
        "execution_time_ms": round(execution_time, 2),
        "start_time": start_time,
        "input_parameters": {
            "demand": round(demand, 1),
            "price_low": round(price_low, 2),
            "price_high": round(price_high, 2),
        },
        "variables": {        
            "energy_low": round(float(result.x[0]), 1),
            "energy_high": round(float(result.x[1]), 1),
            "energy_solar": round(float(result.x[2]), 1),
        },
        "total_cost_eur": round(float(result.fun), 2),
    }
