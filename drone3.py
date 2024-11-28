import csv
from dronekit import connect, VehicleMode, LocationGlobalRelative
import time

# Connect to the Vehicle
connection_string = '/dev/ttyACM0'
vehicle = connect(connection_string, baud=57600, wait_ready=True)

# Function to arm the drone and take off
def arm_and_takeoff(target_altitude):
    print("Basic pre-arm checks")
    
    # Check if vehicle is armable
    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialize...")
        time.sleep(1)

    print("Arming vehicle")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.arm()

    # Wait until vehicle is armed
    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)

    print("Taking off!")
    vehicle.simple_takeoff(target_altitude)

    # Wait until the vehicle reaches a safe height
    while True:
        print(" Altitude: ", vehicle.location.global_relative_frame.alt)
        if vehicle.location.global_relative_frame.alt >= target_altitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

# Function to navigate to a specified location
def goto_location(lat, lon, altitude):
    target_location = LocationGlobalRelative(lat, lon, altitude)
    vehicle.simple_goto(target_location)

    # Wait until the vehicle reaches the location
    while True:
        current_lat = vehicle.location.global_relative_frame.lat
        current_lon = vehicle.location.global_relative_frame.lon
        print(f"Current location: ({current_lat}, {current_lon})")
        if abs(current_lat - lat) < 0.00005 and abs(current_lon - lon) < 0.00005:
            print("Reached waypoint")
            break
        time.sleep(1)

# Function to delete visited coordinates and update CSV
def delete_visited_coordinate(filename, visited_lat, visited_lon):
    with open(filename, newline='') as csvfile:
        # Dynamically retrieve the fieldnames from the file
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames  # Capture all fieldnames from the CSV
        rows = list(reader)
    
    # Filter out visited coordinates
    remaining_rows = [row for row in rows if not (float(row['Latitude']) == visited_lat and float(row['Longitude']) == visited_lon)]
    
    # Rewrite the CSV without visited coordinates
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(remaining_rows)

# Function to read waypoints from CSV
def read_waypoints_from_csv(filename):
    waypoints = []
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            lat = float(row['Latitude'])
            lon = float(row['Longitude'])
            waypoints.append((lat, lon))
    return waypoints

# Main script
if __name__ == "__main__":
    # Define target altitude
    target_altitude = 15  # predefined altitude of 15 meters

    # CSV file path
    csv_file = 'gps_data.csv'

    # Arm and take off
    arm_and_takeoff(target_altitude)

    # Loop until all waypoints are visited
    while True:
        # Read waypoints from CSV
        waypoints = read_waypoints_from_csv(csv_file)

        # If there are no more waypoints, break the loop
        if not waypoints:
            print("All waypoints visited.")
            break

        # Get the first waypoint
        lat, lon = waypoints[0]
        
        # Navigate to the waypoint
        print(f"Going to waypoint: lat={lat}, lon={lon}")
        goto_location(lat, lon, target_altitude)

        # Delete the visited waypoint from the CSV
        delete_visited_coordinate(csv_file, lat, lon)

        # Hover at the waypoint for 2 seconds
        time.sleep(2)

    # Hover for 5 seconds and enable RTL
    print("Hovering for 5 seconds before returning home.")
    time.sleep(5)
    vehicle.mode = VehicleMode("RTL")

    # Close vehicle object before exiting script
    vehicle.close()
