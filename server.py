import socket
import ipaddress
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import os

load_dotenv()

PAYLOAD = 2036


MONGO_URI = os.getenv('MONGODB_URI')
client = MongoClient(MONGO_URI)
db = client['test']                      # Chong dong put ur stuff here
collection = db['Stuff_virtual']  

# Nam stuff CHANGE THIS TOO CHONG DONG at least board name the unit conversion stuff keep
DEVICE_METADATA = {
    "kitchen_fridge": {
        "board_name": "Arduino Pro Mini - test",
        "sensor_type": "Moisture Meter - Moisture MEter",
        "unit": "RH%",
        "conversion_factor": 1.0  
    },
    "test_device": {
        "board_name": "ESP-12S - Test",
        "sensor_type": "MPU6050 - test",
        "unit": "kWh",
        "conversion_factor": 1.0  
    },
    "smart_dishwasher": {
        "board_name": "Smart Dishwasher",
        "sensor_type": "Water Consumption",
        "unit": "gallons",
        "conversion_factor": 0.264172  
    }
}

def get_moisture_readings(start_time=None, end_time=None):
    """Get moisture readings from the virtual collection"""
    query = {
        "payload.board_name": DEVICE_METADATA["kitchen_fridge"]["board_name"],
        "payload.Moisture Meter - Moisture MEter": {"$exists": True}
    }
    
    if start_time and end_time:
        query["time"] = {"$gte": start_time, "$lte": end_time}
    
    return collection.find(query)

def get_water_consumption():
    """Get water consumption data for dishwasher"""
    query = {
        "payload.board_name": DEVICE_METADATA["smart_dishwasher"]["board_name"],
        "payload.Water Consumption": {"$exists": True}
    }
    return collection.find(query)

def get_electricity_consumption():
    """Get electricity consumption for all devices"""
    devices = ["Arduino Pro Mini - test", "ESP-12S - Test"]  
    result = {}
    
    for device in devices:
        query = {
            "payload.board_name": device,
            "payload.MPU6050 - test": {"$exists": True}  
        }
        latest_reading = collection.find_one(query, sort=[("time", -1)])
        if latest_reading:
            try:
                raw_value = float(latest_reading["payload"]["MPU6050 - test"])
                device_type = next(k for k, v in DEVICE_METADATA.items() if v["board_name"] == device)
                conversion_factor = DEVICE_METADATA[device_type]["conversion_factor"]
                result[device] = raw_value * conversion_factor
            except (KeyError, ValueError):
                result[device] = 0
    
    return result

def convert_to_rh_percent(moisture_value):
    """Convert moisture reading to Relative Humidity percentage using metadata"""
    try:
        value = float(moisture_value)
        return value * DEVICE_METADATA["kitchen_fridge"]["conversion_factor"]
    except (ValueError, TypeError):
        return 0.0

def get_pst_time():
    """Get current time in PST"""
    pst = pytz.timezone('America/Los_Angeles')
    return datetime.now(pst)

def process_query(query):
    """Process incoming queries and return appropriate response"""
    if query == "What is the average moisture inside my kitchen fridge in the past three hours?":
        try:
            end_time = get_pst_time()
            start_time = end_time - timedelta(hours=3)
            
            readings = get_moisture_readings(start_time, end_time)
            moisture_values = []
            
            for doc in readings:
                try:
                    moisture = float(doc["payload"]["Moisture Meter - Moisture MEter"])
                    moisture_values.append(moisture)
                except (KeyError, ValueError, TypeError):
                    continue
            
            if not moisture_values:
                return "No moisture data available for the past three hours"
            
            avg_moisture = sum(moisture_values) / len(moisture_values)
            metadata_info = f"Device: {DEVICE_METADATA['kitchen_fridge']['board_name']}, Unit: {DEVICE_METADATA['kitchen_fridge']['unit']}"
            
            return f"Average moisture: {avg_moisture:.2f}% RH\nMetadata: {metadata_info}"
        except Exception as e:
            return f"Error processing moisture query: {str(e)}"

    elif query == "What is the average water consumption per cycle in my smart dishwasher?":
        try:
            readings = get_water_consumption()
            consumption_values = []
            
            for doc in readings:
                try:
                    raw_consumption = float(doc["payload"]["Water Consumption"])
                    gallons = raw_consumption * DEVICE_METADATA["smart_dishwasher"]["conversion_factor"]
                    consumption_values.append(gallons)
                except (KeyError, ValueError, TypeError):
                    continue
            
            if not consumption_values:
                return "No water consumption data available"
            
            avg_consumption = sum(consumption_values) / len(consumption_values)
            return f"Average water consumption: {avg_consumption:.2f} gallons"
        except Exception as e:
            return f"Error processing water consumption query: {str(e)}"

    elif query == "Which device consumed more electricity among my three IoT devices (two refrigerators and a dishwasher)?":
        try:
            consumption_data = get_electricity_consumption()
            
            if not consumption_data:
                return "No electricity consumption data available"
            
            max_consumer = max(consumption_data.items(), key=lambda x: x[1])
            consumptions = "\n".join([f"{device}: {value:.2f} kWh" 
                                    for device, value in consumption_data.items()])
            
            return f"Device Electricity Consumption:\n{consumptions}\n\nHighest consumer: {max_consumer[0]} with {max_consumer[1]:.2f} kWh"
        except Exception as e:
            return f"Error processing electricity consumption query: {str(e)}"

    return "Invalid query"

# user input for ip and port
while True:
    try:
        host = input("Input ip: ")
        ipaddress.ip_address(host)
        print(f"Ip address chosen: {host}")
        break
    except ValueError:
        print("Invalid IP address")

while True:
    try:
        port = int(input("Input port: "))
        if (port >= 0 and port <= 2**(16)):
            print(f"Port number chosen: {port}")
            break
        raise Exception("The input is not in the port range")
    except ValueError:
        print("Needs to be an int")
    except Exception as e:
        print(f"An error occurred: {e}")

# socket.SOCK_STREAM has the socket use datagram; TCP Connection
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((host, port))
    s.listen()
    conn, addr = s.accept()
    print(f"Server Host: {host}, Server Port: {port}")
    while True:
        print("\nWaiting for client message... ")
        data = conn.recv(PAYLOAD)
        print("Received Response from the Client")
        print(f"\nIP Client: {addr}, Data: {data.decode()}, Length Data: {len(data)}")
        if data:
            try:
                print(f"Processing query from client {addr}")
                query = data.decode()
                if query == 'end':
                    conn.sendall(b'Ended')
                    print("\nEnding server")
                    conn.close()
                    s.close()
                    break
                
                response = process_query(query)
                conn.sendall(response.encode())
                
            except Exception as e:
                print(f"Error occurred {e}")
                error_msg = f"Error processing query: {str(e)}"
                conn.sendall(error_msg.encode())
