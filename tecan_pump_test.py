from devices.industry_components.pumps.tecan_pumps.tecan_pump_driver import Tecan_driver 
from utils.serial_DT_transporter import SerialDTTransport
from devices.industry_components.pumps.tecan_pumps.tecan_pump import Tecan_pump
from methods.methods import GeneralExperimentMethod
import time
from pathlib import Path

instrument_config_file = Path(r"C:\Users\zahrtlab\AutoZahrt\AutoZahrt_experiments\Instrument_config_files\instrument_config_all_pumps.csv")
method_file = Path(r"C:\Users\zahrtlab\AutoZahrt\AutoZahrt_experiments\methods\flow_tecan_1.csv")



# experiment = GeneralExperimentMethod(input_file=method_file,
#                                      instrument_config_file=instrument_config_file)

# experiment.run_experiment()
# pump = Tecan_pump(port='COM3', baud_rate=9600, timeout=1)
# pump.connect()
# pump.stop() # Stop the pump before starting the test
# pump.set_flow_rate(flow_rate_ul_min=1000) # Set flow rate to 1000 uL/min
# pump.dispense(volume_ul=1000) # Dispense 1000 uL of liquid
# pump.close()




driver = Tecan_driver(port='COM15', baud_rate=9600, timeout=1)
driver.connect()
driver.initialize_pump(pump="A", resolution=0)
print("Initializing pump A.")
driver.initialize_pump(pump="B", resolution=0)
print("Initializing pump B.")
driver.send_command("/1J7R") # Initialize pump A with resolution 0
print("Initializing pump A.")
time.sleep(0.1) # Wait for pump A to initialize
driver.send_command("/2J7R") # Initialize pump B with resolution 0
print("Initializing pump B.")

# output_A = driver.is_valve_in_output_position(pump="A")
# print(f"Is valve in output position (Pump A): {output_A}")

# output_B = driver.is_valve_in_output_position(pump="B")
# print(f"Is valve in output position (Pump B): {output_B}")

# driver.disconnect()
# #driver.initialize_pump(pump="A", resolution=0)
# #driver.initialize_pump(pump="B", resolution=0)

# driver.run_continuous_flow(dispense_speed=1110)

# driver.check_until_initialized(pump="A", timeout=30)
# driver.check_until_initialized(pump="B", timeout=30)
# command_A = driver.compose_command_continuous_flow_A(resolution=1, aspirate_speed=6000, dispense_speed=3000, initial_position=0, final_position=24000)
# command_B = driver.compose_command_continuous_flow_B(resolution=1, aspirate_speed=6000, dispense_speed=3000, initial_position=0, final_position=24000)

# print(f"Command A: {command_A}")
# print(f"Command B: {command_B}")

# #driver.run_continuous_flow(dispense_speed=100)
# driver.start_pump(speed=3000, pump="A")
# driver.start_pump(speed=3000, pump="B")


# time.sleep(10)
# driver.stop_pump(pump="A")
# driver.stop_pump(pump="B")

# query_response = driver.query("/1?13")
# print(f"Pump A query response: {query_response}")
# query_response = driver.query("/2?13")
# print(f"Pump B query response: {query_response}")
# query_response = driver.query("/1?14")
# print(f"Pump A query response: {query_response}")
# query_response = driver.query("/2?14")
# print(f"Pump B query response: {query_response}")
# response = driver.query("/1N1J7V6000IA24000V3000OA0J0V6000IA24000gH0J7OV3000A0J0IV6000A24000GR")
# print(f"Pump A response: {response}")
# response = driver.query("/2N1H0V3000OA0R")
# print(f"Pump B response: {response}")
#driver.query("/1S14OA1500R")
#time.sleep(0.1) # Wait for pump to respond
#driver.query("/2S14IA3000R")
#time.sleep(0.1) # Wait for pump to respond
# time.sleep(30) # Wait for pump to respond
# driver.initialize_pump(pump="A", resolution=0)
# driver.initialize_pump(pump="B", resolution=0)
# time.sleep(0.1) # Wait for pumps to initialize
#driver.check_until_initialized(pump="A")
#driver.check_until_initialized(pump="B")
#driver.start_pump(speed=1000, pump="A")
#driver.start_pump(speed=1000, pump="B")
#time.sleep(20) # Let the pump run for 20 seconds
#driver.stop_pump(pump="A")
#driver.stop_pump(pump="B")
#driver.initialize_pump(pump="A", resolution=0)
#driver.initialize_pump(pump="B", resolution=0)
#time.sleep(10) # Wait for pump to initialize
# response = driver.query("/1S14D1R") 
# print(f"Pump response: {response}")
# response = driver.query("/2S14D1R") 
# print(f"Pump response: {response}")
# #status_char, error_code = driver.is_initialized("B")
# #response = driver.query("/2S14IA3000R")
# #print(f"Pump response: {response}")
# is_initialized_A = driver.is_initialized("A")
# print(f"Pump A initialized: {is_initialized_A}")
# is_initialized_B = driver.is_initialized("B")
# print(f"Pump B initialized: {is_initialized_B}")
#driver.initialize_pump(pump="A", resolution=0)
#driver.initialize_pump(pump="B", resolution=0)
#driver.check_until_initialized(pump="A", timeout=30)
#driver.check_until_initialized(pump="B", timeout=30)

#driver.disconnect()