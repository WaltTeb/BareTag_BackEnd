import serial
import json
from Anchor import Anchor
import socket
import requests
import math
import codecs

def trilaterate(anchors):
    x1 = anchors[0].x_coord
    x2 = anchors[1].x_coord
    x3 = anchors[2].x_coord

    y1 = anchors[0].y_coord
    y2 = anchors[1].y_coord
    y3 = anchors[2].y_coord

    r1 = anchors[0].get_dist()
    r2 = anchors[1].get_dist()
    r3 = anchors[2].get_dist()

    A = -2*x1 + 2*x2
    B = -2*y1 + 2*y2
    C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2
    D = -2*x2 + 2*x3
    E = -2*y2 + 2*y3
    F = r2**2 - r3**2 - x2**2 + x3**2 - y2**2 + y3**2

    X = (C*E - F*B) / (E*A - B*D)
    Y = (C*D - A*F) / (B*D - A*E)

    # Reset the updated flag for all anchors that were updated before
    for anchor in anchors:
        anchor.updated = False 

    return (X, Y)   

def get_anchors_from_server(user_id):
    # Get request to Flask server to fetch anchors for user_id
    response = requests.get(f'http://172.24.131.25:5000/get_anchors?user_id={user_id}') # might have to update this link


    if response.status_code == 200:
        # Extract list of anchors from the server response
        data = response.json()
        anchors_data = data.get("anchors", []) # anchors is key
        return anchors_data
    else:
        print(f"Error fetching anchors: {response.status_code}")
        return []
    
"""""
# Helper function to create our grid based on x/y meter positions
def lat_lon_to_meters(lat1, lon1, lat2, lon2):
    # Approximate Earth radius in kilometers
    R = 6371
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Haversine formula to calculate distance between two lat/lon points
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    distance = R * c * 1000  # Distance in meters
    return distance
"""

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



  # -------------------------------------------------- RUNNING CODE -------------------------------------

try:

    lora_usb_port = "ttyUSB0" # Set port manually (no more json)
    user_id = 1
    anchors_data = get_anchors_from_server(user_id)
    print("Anchors from server:", anchors_data)

    # Initialize Anchor

    anchor_list = []
    anchor_dict = {}

    # Find the anchor with smallest latitude and longitude
    min_anchor = min(anchors_data, key=lambda x: (x['latitude'], x['longitude']))
    print("min anchor type:", type(min_anchor))

    # Get the minimum latitude and longitude (used for the origin point)
    min_lat = min_anchor['latitude']
    min_lon = min_anchor['longitude']

    # Convert all anchors to x,y positions relative to the anchor with the smallest latitude
    for anchor in anchors_data:
        # Calculate the x and y distance from the min_lat/min_lon anchor
        x = (anchor['longitude'] - min_lon) * 111320 * math.cos(math.radians(min_lat))  # X in meters
        y = (anchor['latitude'] - min_lat) * 111320  # Y in meters

        # Use latitude and longitude difference as x and y
        new_anchor = Anchor(anchor['id'], x, y)
        anchor_list.append(new_anchor)
        anchor_dict[new_anchor.id] = new_anchor
    
    for anchor in anchor_list:
        print(anchor)  # This will call the __str__ method of the Anchor class, for debugging

    
    with serial.Serial(f"/dev/{lora_usb_port}", 57600, timeout=1) as ser:
        while 1:
            line = ser.readline()
            if len(line) > 3:
                print(line)
                line_str = line.decode("utf-8")[:-2]
                if line_str[:4] == "+RCV":

                    recv_data = line_str.split(',')
                    recv_id = int(recv_data[0][5:])
                    recv_dist = float(recv_data[2])
                    anchor_dict[recv_id].update_dist(recv_dist)

            # Check for expired updates
            for anchor in anchor_list:
                if not anchor.updated_recently(threshold=10):
                    anchor.updated = False  # Reset an anchor if not updated in last 10 sec

            # List of only updated anchors to send to trilaterate
            updated_anchors = [anchor for anchor in anchor_list if anchor.updated]
            # Now can trilaterate after making sure 3 have been updated within 10s of each other
            if len(updated_anchors) >= 3:
                tag_location = trilaterate(updated_anchors)

                # Convert the x, y tag_location to the latitude and longitude of the tag
                tag_latitude, tag_longitude = meters_to_lat_long(tag_location[0], tag_location[1], min_anchor)
                print(f"Tag Latitude {tag_latitude}, Tag Longitude: {tag_longitude}") # debugging


                # Collect the IDs of the anchors used
                used_anchors = [updated_anchors[0].id, updated_anchors[1].id, updated_anchors[2].id]


                # Prepare data to send to the server
                data_to_send = {
                    "tag_name": "NEW TAG 2",
                    "latitude": tag_latitude, # X offset in meters
                    "longitude": tag_longitude,  # Y offset in meters
                    "user_id": 1,   # Assume user_id is provided
                    "anchor_ids": used_anchors # Include the anchor IDs used
                }

                # Send data to the Flask server using the requests library
                response = requests.post('http://172.24.131.25:5000/add_tag_tcp', json=data_to_send)

                # Handle the server's response
                if response.status_code == 200:
                    print("Server Response: ", response.json())
                else:
                    print(f"Error: {response.status_code}, {response.text}")

except KeyboardInterrupt as e:
    print(f"Program quit with exception {e}")