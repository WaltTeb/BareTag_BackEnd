#------------ Sean Brown -----------------
#--------------BareTag Client ------------------
#-------------TCP_Client.py------------------
import socket
import sys
import json

# Fale data
data = {
    "user_id:": 1,  # Not sure how I am going to know this
    "tag_name": "Test DUMMY",     # Tag name
    "latitude": 100.2,      # Latitude
    "longitude": -100.7    # Longitude 
}

# Create the HTTP request for Flask server
http_request = f"""POST /add_tag_tcp HTTP/1.1\r
Host: localhost:5000\r
Content-Type: application/json\r
Content-Length: {len(json.dumps(data))}\r
\r
{json.dumps(data)}\r
"""

# Set up the TCP client to connect to the Flask server
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        # Connect to the server running on localhost, port 5000
        s.connect(('localhost', 5000))

        # Send the HTTP request to the Flask server
        s.sendall(http_request.encode())

        # Receive response from the server
        response = s.recv(1024)
        print(f"Server response: {response.decode()}")

    except Exception as e:
        print(f"An error occurred: {e}")

