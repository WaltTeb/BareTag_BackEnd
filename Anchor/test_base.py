import serial
import json
from Anchor import Anchor
import socket
import requests
import math
import time

def three_anchors_updated(anchors):
    updated_anchors = sum(anchor.updated for anchor in anchors)
    return updated_anchors >= 3

def trilaterate(anchors):
    x1, y1, r1 = anchors[0].x_coord, anchors[0].y_coord, anchors[0].get_dist()
    x2, y2, r2 = anchors[1].x_coord, anchors[1].y_coord, anchors[1].get_dist()
    x3, y3, r3 = anchors[2].x_coord, anchors[2].y_coord, anchors[2].get_dist()

    A = -2*x1 + 2*x2
    B = -2*y1 + 2*y2
    C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2
    D = -2*x2 + 2*x3
    E = -2*y2 + 2*y3
    F = r2**2 - r3**2 - x2**2 + x3**2 - y2**2 + y3**2

    X = (C*E - F*B) / (E*A - B*D)
    Y = (C*D - A*F) / (B*D - A*E)

    return (X, Y)

def get_anchors_from_server(user_id):
    response = requests.get(f'http://localhost:5000/get_anchors?user_id={user_id}')
    if response.status_code == 200:
        data = response.json()
        return data.get("anchors", [])
    else:
        print(f"Error fetching anchors: {response.status_code}")
        return []

def meters_to_lat_long(x_offset, y_offset, reference_anchor):
    lon_offset = x_offset / (111320 * math.cos(math.radians(reference_anchor.latitude)))
    lat_offset = y_offset / 111320
    return reference_anchor.latitude + lat_offset, reference_anchor.longitude + lon_offset

# --------------------------- RUNNING CODE ---------------------------
try:
    lora_usb_port = "/dev/ttyUSB0"
    user_id = 1
    anchors_data = get_anchors_from_server(user_id)
    print("Anchors from server:", anchors_data)

    anchor_list = []
    anchor_dict = {}

    # Find the anchor with smallest latitude and longitude
    min_anchor = min(anchors_data, key=lambda x: (x['latitude'], x['longitude']))
    
    # Get the minimum latitude and longitude (used for the origin point) : (0,0)
    min_lat, min_lon = min_anchor['latitude'], min_anchor['longitude']

    # Convert all anchors to x,y positions relative to anchor with smallest lat and lon
    for anchor in anchors_data:  
        x = (anchor['longitude'] - min_lon) * 111320 * math.cos(math.radians(min_lat))
        y = (anchor['latitude'] - min_lat) * 111320

        # Create All Anchor Objects
        new_anchor = Anchor(anchor['id'], x, y)
        anchor_list.append(new_anchor)
        anchor_dict[new_anchor.id] = new_anchor
    
    for anchor in anchor_list:
        print(anchor)   # Will call __str__ method and show x,y of our anchors

    with serial.Serial(f"/dev/{lora_usb_port}", 115200, timeout=1) as ser:
        while True:
            line = ser.readline()
            if len(line) > 3:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("+RCV"):
                    recv_data = line_str.split(',')
                    recv_id = int(recv_data[0][5:])
                    recv_dist = float(recv_data[2])
                    anchor_dict[recv_id].update_dist(recv_dist)
            if three_anchors_updated(anchor_list):
                tag_location = trilaterate(anchor_list)
                tag_latitude, tag_longitude = meters_to_lat_long(tag_location[0], tag_location[1], min_anchor)
                print(f"Tag Latitude {tag_latitude}, Tag Longitude: {tag_longitude}")

                data_to_send = {
                    "tag_name": "NEW TAG 2",
                    "latitude": tag_latitude,
                    "longitude": tag_longitude,
                    "user_id": user_id,
                    "anchor_ids": [anchor.id for anchor in anchor_list]
                        }

                response = requests.post('http://localhost:5000/add_tag_tcp', json=data_to_send)
                if response.status_code == 200:
                    print("Server Response: ", response.json())
                else:
                    print(f"Error: {response.status_code}, {response.text}")

except KeyboardInterrupt as e:
    print(f"Program quit with exception {e}")