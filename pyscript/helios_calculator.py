try: # Faking Home Assistant Environment for Visual Studio using Home Assistant Mock
    from HomeAssistantMock import service, time_trigger, log, automation, task, state  # Include HA mock for testing outside of Home Assistant
except ImportError:
    pass  # In Home Assistant no mock is needed since service/state/log etc already exist global!

# Modules used by Home Assistant must be in the "modules" folder of the Home Assistant configuration directory. 
# The modules folder is automatically added to the Python path by Home Assistant but not by Visual Studio Code. 
# Therefore, we need to add the modules folder to the Python path for testing in Visual Studio Code.
from HeliosModule import helios_calculate_plan, helios_calculate_dummy  # Import the Helios Optimize Energy function (from module folder)

# Helios Service with a return response
# Definition of the Home Assistant Service to calculate an optimized energy plan
# Handles only the Home Assistant specific calls
# The actual calculation is done by helios_optimize() and can run without HA specific python functions
@service(supports_response="optional") 
def helios_ha_service(
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
    Home Energy Linear Integrated Optimization Service (HELIOS):
    A Home Assistant Optimize Energy Plan Service that uses SciPy Linear/MILP Programming.
    """

    # Call the optimization function with the provided parameters
    # The optimization function is designed to be independent of Home Assistant, allowing for easier testing and debugging.
    payload = helios_calculate_plan(
        steps=steps,
        step_size=step_size,
        start_step=start_step,
        max_time=max_time,
        max_iterations=max_iterations,
        grid_max_import=grid_max_import,
        grid_max_export=grid_max_export,
        import_prices=import_prices,
        export_prices=export_prices,
        house_forecast=house_forecast,
        solar=solar,
        battery=battery,
        ev=ev,
        heat_pump=heat_pump,
        boiler=boiler
    )

    # Store the optimization result in the Home Assistant Helios Energy Plan Entity and its attributes 
    state.set(
        "pyscript.helios_energy_plan",
        value=payload.get('current_strat'),
        new_attributes=payload
    )

    return payload # Return the payload to the Home Assistant automation in the return_response

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

# This block takes care of running the service directly in VS Code
if __name__ == "__main__":
    print("=======================================================")
    print("🚀 LOCAL HELIOS TEST RUN STARTED IN VISUAL STUDIO CODE ")
    print("=======================================================")

    return_response = helios_ha_service()


