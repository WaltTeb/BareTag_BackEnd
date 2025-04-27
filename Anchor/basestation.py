import serial
import json
from Anchor import Anchor
import socket
import requests
import math
import codecs
import time
from dotenv import load_dotenv
import os
import numpy as np
#from Multilateration_3D_Positioning import multilat_lib

def trilaterate(anchors, distances):
    x1 = anchors[0].x_coord
    x2 = anchors[1].x_coord
    x3 = anchors[2].x_coord

    y1 = anchors[0].y_coord
    y2 = anchors[1].y_coord
    y3 = anchors[2].y_coord

    r1 = distances[0]
    r2 = distances[1]
    r3 = distances[2]

    A = -2*x1 + 2*x2
    B = -2*y1 + 2*y2
    C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2
    D = -2*x2 + 2*x3
    E = -2*y2 + 2*y3
    F = r2**2 - r3**2 - x2**2 + x3**2 - y2**2 + y3**2

    X = (C*E - F*B) / (E*A - B*D)
    Y = (C*D - A*F) / (B*D - A*E)

    return (X, Y)   

# --------------------------------------- INTERACTING WITH BACKEND TO FETCH DATA --------------------------------

def get_anchors_from_server(user_id):
    # Get request to Flask server to fetch anchors for user_id
    #response = requests.get(f'http://172.24.131.25:5000/get_anchors?user_id={user_id}') # might have to update this link
    response = requests.get(f'{os.environ["BASE_URL"]}/get_anchors?user_id={user_id}') # might have to update this link


    if response.status_code == 200:
        # Extract list of anchors from the server response
        data = response.json()
        anchors_data = data.get("anchors", []) # anchors is key
        return anchors_data
    else:
        print(f"Error fetching anchors: {response.status_code}")
        return []

def get_tags_from_server(user_id):
    # Get request to Flask server to fetch the tags of a user
    #response = requests.get(f'http://172.24.131.25:5000/get_tags?user_id={user_id}')
    response = requests.get(f'{os.environ["BASE_URL"]}/get_tags?user_id={user_id}')


    if response.status_code == 200: # GOOD
        data = response.json()
        tags_data = data.get("tags_location", []) 
        tag_ids = [tag['id'] for tag in tags_data] # Extracts all Tag IDs under a user profile
        return tag_ids
    else:
        print(f"Error fetching tags: {response.status_code}")
        return []

# ----------------------------------------------- Conversion ----------------------------------

def meters_to_lat_long(x_offset, y_offset, reference_anchor):
    # Convert the given x and y offsets (meters) into latitude and longitude relative to (0,0) anchor

    # x offset to longitude diff
    # lon_offset = x_offset / (111320 * math.cos(math.radians(reference_anchor.latitude)))
    lon_offset = x_offset / (111320 * math.cos(math.radians(reference_anchor["latitude"])))


    # Convert y to latitude difference
    lat_offset = y_offset / 111320

    # Calculate new latitude and longitude
    # new_latitude = reference_anchor.latitude + lat_offset
    # new_longitude = reference_anchor.longitude + lon_offset

    new_latitude = reference_anchor["latitude"] + lat_offset
    new_longitude = reference_anchor["longitude"] + lon_offset


    return new_latitude, new_longitude



  # -------------------------------------------------- ESTABLISHING ANCHOR COORDINATE GRID  -------------------------------------

try:
    load_dotenv()

    lora_usb_port = "USB0" # Set port manually (no more json)
    user_id = 1
    anchors_data = get_anchors_from_server(user_id)
    print("Anchors from server:", anchors_data)

    # Initialize Anchor
    anchor_coords = []  # in geo-coordinates
    anchor_list = []
    anchor_dict = {}

    # Find the anchor with smallest latitude and longitude
    min_anchor = min(anchors_data, key=lambda x: (x['latitude'], x['longitude']))
    print("min anchor type:", type(min_anchor))

    # Get the minimum latitude and longitude (used for the origin point)
    min_lat = min_anchor['latitude']
    min_lon = min_anchor['longitude']
    min_alt = min_anchor['altitude']

    # Convert all anchors to x,y positions relative to the anchor with the smallest latitude
    for anchor in anchors_data:
        # Calculate the x and y distance from the min_lat/min_lon anchor
        longitude = anchor['longitude']
        latitude = anchor['latitude']
        altitude = anchor['altitude']
        anchor_coords.append([longitude, latitude, altitude])
        x = (longitude - min_lon) * 111320 * math.cos(math.radians(min_lat))  # X in meters
        y = (latitude - min_lat) * 111320  # Y in meters
        z = anchor['altitude'] - min_alt

        # Use latitude and longitude difference as x and y
        new_anchor = Anchor(anchor['id'], x, y, z)
        anchor_list.append(new_anchor)
        anchor_dict[new_anchor.id] = new_anchor
    
    for anchor in anchor_list:
        print(anchor)  # This will call the __str__ method of the Anchor class, for debugging

    tags_list = get_tags_from_server(user_id)
    if not tags_list:
        print(f"No tags found for user {user_id}. Exiting")
        exit()
    # Check to see what tags we got from the server
    print(f"Tags to ping: {tags_list}")
    
    # ----------------------------------------------------------- ACQUIRING TAG LOCATIONS ---------------------------------------------------------------------------------
    
    # Dictionary to store tag measurements (key: tag_id, value: {anchor_id: distance})
    # tag_measurements = {tag['id']: {} for tag in tags_list}
    tag_measurements = {tag: {} for tag in tags_list}


    with serial.Serial(f"/dev/{lora_usb_port}", 57600, timeout=1) as ser:
        # Send a message to every anchor from the Base Station the IDs of the Tags we are looking for
        for anchor in anchor_list: 
            # Construct message
            for tag in tags_list:
                anchor_resp = ""
                num_pings = 0
                while anchor_resp[:19] != f'+RCV={anchor.id},9,ACK_NT:{tag}':
                    if num_pings == 5:
                        print(f"Failed to communicate with Anchor: {anchor.id}")
                        exit()
                    message = f"AT+SEND={anchor.id},{len(tag)+8},NEW_TAG:{tag}\r\n"
                    num_pings += 1
                    print(f"Sending: {message}")
                    ser.write(message.encode()) # Send message over serial
                #     # time.sleep(1)
                    try:
                        anchor_resp = ser.readline()
                        anchor_resp = anchor_resp.decode("utf-8")
                        while anchor_resp[:3] == "+OK":
                            anchor_resp = ser.readline()
                            anchor_resp = anchor_resp.decode("utf-8")

                        print(f"Recieved: {anchor_resp[:19]}")
                        
                    except serial.SerialTimeoutException as te:
                        print("Serial timedout waiting for uart ack")
                        ser.write(message.encode()) # Send message over serial
                        num_pings += 1
                    
                    if isinstance(anchor_resp, bytes):
                        anchor_resp = anchor_resp.decode("utf-8")
                
                print(f"Registered Tag: {tag}, to Anchor: {anchor.id}")
        
        for anchor in anchor_list:
            anchor_resp = ""
            num_pings = 0
            while anchor_resp[:19] != f'+RCV={anchor.id},9,ACK_BROAD':
                if num_pings == 5:
                    print(f"Failed to communicate with Anchor: {anchor.id}")
                    exit()
                message = f"AT+SEND={anchor.id},10,_BROADCAST\r\n"
                num_pings += 1
                print(f"Sending: {message}")
                ser.write(message.encode()) # Send broadcast command

                try:
                    anchor_resp = ser.readline()
                    anchor_resp = anchor_resp.decode("utf-8")
                    while anchor_resp[:3] == "+OK":
                        anchor_resp = ser.readline()
                        anchor_resp = anchor_resp.decode("utf-8")
                    print(f"Recieved: {anchor_resp[:19]}")

                except serial.SerialTimeoutException as te:
                    print("Serial timedout waiting for uart ack")
                    ser.write(message.encode()) # Send message over serial
                    num_pings += 1

                if isinstance(anchor_resp, bytes):
                        anchor_resp = anchor_resp.decode("utf-8")
            print(f"Anchor: {anchor.id} now broadcasting")

        tag_distances = {}
        # Receiving distance measurements from anchors
        while 1:
            line = ser.readline()
            if len(line) > 3:
                print(line)
                line_str = line.decode("utf-8")[:-2]
                if line_str[:4] == "+RCV":
                    recv_data = line_str.split(',') 
                    recv_anc_id = int(recv_data[0][5:])   # Anchor that you are receiving measurement from
                    recv_tag_info = recv_data[2]    # Distance from the tag to (specific) anchor and tag ID
                    recv_tag_info = recv_tag_info.split(':')
                    recv_dist = float(recv_tag_info[0])

                    # Walter need this sent in the packet
                    recv_tag_id = recv_tag_info[1]  # Need to know the ID of the tag its measured to

                    # Not sure if we need this anymore , do not think so
                    anchor_dict[recv_anc_id].update_dist(recv_dist, recv_tag_id) # Saves this in an dictionary of anchors and received distances
                    tag_measurements[recv_tag_id][recv_anc_id] = recv_dist # Update tag's measurement

                    # Debugging output
                    print(f"Received from Anchor {recv_anc_id}: Tag {recv_tag_id} at Distance {recv_dist}m")

            # Check if tags have measurements from 3 different anchors
            for tag_id, measurements in tag_measurements.items():
                if len(measurements) >= 3:
                    # Get the 3 anchors that have measurements for this tag
                    anchors_with_distances = [anchor_dict[anchor_id] for anchor_id in measurements.keys()]
                    distances = list(measurements.values())
                    tag_location = trilaterate(anchors_with_distances, distances)

                    # Convert the x, y tag_location to the latitude and longitude of the tag
                    tag_latitude, tag_longitude = meters_to_lat_long(tag_location[0], tag_location[1], min_anchor)
                    print(f"Tag Latitude {tag_latitude}, Tag Longitude: {tag_longitude}") # debugging

                    ''' Estimate the z location of the tag '''
                    # Convert anchor_list [class Anchor] to [[x,y,z]]
                #    estimated_z = multilat_lib.brute_force(anchor_coords=anchor_coords, x=tag_location[0], y=tag_location[1], distances=distances)
                 #   estimated_local = np.array([tag_location[0], tag_location[1], estimated_z])  # local x, y, z
                  #  tag_altitude = multilat_lib.local_to_geo(estimated_local, min_anchor)[2]
                    
                    # Collect the IDs of the anchors used
                    used_anchors = list(measurements.keys())


                    # Prepare data to send to the server
                    data_to_send = {
                        "tag_id": f"{tag_id}",
                        "latitude": tag_latitude, # X offset in meters
                        "longitude": tag_longitude,  # Y offset in meters
                        "altitude": tag_altitude,
                        "user_id": 1,   # Assume user_id is provided
                        # "anchor_ids": used_anchors # Include the anchor IDs used
                    }

                    # Send data to the Flask server using the requests library
                    #response = requests.post('http://172.24.131.25:5000/add_tag_tcp', json=data_to_send)
                    response = requests.post(f"{os.environ['BASE_URL']}/add_tag_tcp", json=data_to_send)


                    # Handle the server's response
                    if response.status_code == 200:
                        print("Server Response: ", response.json())
                    else:
                        print(f"Error: {response.status_code}, {response.text}")
                    
                    # RESET the measurements for a tag after performing trilateration on it
                    print(f"Resetting measurements for Tag {tag_id}")
                    tag_measurements[tag_id] = {} # Clear measurements for the tag

except KeyboardInterrupt as e:
    print(f"Program quit with exception {e}")