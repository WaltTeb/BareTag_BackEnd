import serial
import json
from Anchor import Anchor
import socket
import requests

def all_anchors_updated(anchors):
    for anchor in anchors:
        if not anchor.updated:
            return False
    return True

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

    return (X, Y)

def get_anchors_from_server(user_id):
    response = requests.get(f'http://localhost:5000/get_user_anchors/{}')

try:
    with open('anchor_config.json') as config_file:
        data = json.load(config_file)

    lora_usb_port = data['lora_usb_port']

    anchor_list_json = data['anchors']
    anchor_list = []
    anchor_dict = {}

    for anchor in anchor_list_json:
        new_anchor = Anchor(anchor['anchor_id'], anchor['x_coord'], anchor['y_coord'])
        anchor_list.append(new_anchor)
        anchor_dict[new_anchor.id] = new_anchor

    
    with serial.Serial(f"/dev/{lora_usb_port}", 115200, timeout=1) as ser:
        while 1:
            line = ser.readline()
            if len(line) > 3:
                line_str = line.decode("utf-8")[:-2]
                if line_str[:4] == "+RCV":
                    recv_data = line_str.split(',')
                    recv_id = int(recv_data[0][5:])
                    recv_dist = float(recv_data[2])
                    anchor_dict[recv_id].update_dist(recv_dist)
            if all_anchors_updated(anchor_list):
                tag_location = trilaterate(anchor_list)
                print(tag_location)

            # Collect the IDs of the anchors used
            used_anchors = [anchor_list[0].id, anchor_list[1].id, anchor_list[2].id]


            # Prepare data to send to the server
            data_to_send = {
                "tag_name": "NEW TAG 2",
                "x_offset": tag_location[0], # X offset in meters
                "y_offset": tag_location[1],  # Y offset in meters
                "user_id": 1,   # Assume user_id is provided
                "anchor_ids": used_anchors # Include the anchor IDs used
            }

            # Send data to the Flask server using the requests library
            response = requests.post('http://localhost:5000/add_tag_tcp', json=data_to_send)

            # Handle the server's response
            if response.status_code == 200:
                print("Server Response: ", response.json())
            else:
                print(f"Error: {response.status_code}, {response.text}")

except KeyboardInterrupt as e:
    print(f"Program quit with exception {e}")