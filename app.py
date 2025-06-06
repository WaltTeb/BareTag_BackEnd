from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import sqlite3
from formsubmission import RegistrationForm
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import math
from flask_session import Session  # ✅ Import Flask-Session
from flask_cors import CORS
from shapely.geometry import Point, Polygon
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import time


app = Flask(__name__)
app.secret_key = "__privatekey__"


@app.route('/') # home page
def Home():
    return render_template('home.html')

# ————————————————————————————————————————————————- SESSION ————————————————————————————————————————————————

CORS(app, supports_credentials=True)  # ✅ Allow iOS to send session cookies

# Configure Flask to use server-side sessions
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"  # Use "filesystem" instead of default cookies
Session(app)  # ✅ Initialize the session


# CHECK USER SESSION
@app.route('/session_check', methods=['GET'])
def session_check():
    user_id = session.get('user_id')
    user_name = session.get('user_name')

    if user_id:
        return jsonify({"message": "User session active", "user_id": user_id, "user_name": user_name}), 200
    else:
        return jsonify({"error": "No active session"}), 401
    

# ——————————————————————————————————————————————— LOGIN & REGISTRATION ———————————————————————————————————————————————

# LOGIN
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    con = sqlite3.connect('users.db')
    cur = con.cursor()
    cur.execute("SELECT * FROM profiles WHERE name=?", (username,))
    user = cur.fetchone()
    con.close()

    if user is None or not check_password_hash(user[2], password):  
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = user[0]  # ✅ Store user_id in session
    session['user_name'] = username  # ✅ Store username in session

    print(f"🟢 Session Data: {session}")  # ✅ Debug: Print session contents
    return jsonify({'message': 'Login successful', 'user_id': user[0], 'user_name': username}), 200

# LOGOUT
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # ✅ This removes all session data
    return jsonify({"message": "Logout successful"}), 200

# REGISTRATION PAGE
@app.route('/registration', methods=['POST'])
def registration():
    try:
        # Get data from the incoming JSON request
        data = request.get_json()

        # Get the fields from the JSON data
        userName = data['username']
        passWord = data['password']
        phoneNumber = data['phoneNumber']
        email = data['email']

        # Hash the password
        hashed_password = generate_password_hash(passWord)

        # Check if the user already exists
        con = sqlite3.connect('users.db')
        c = con.cursor()
        c.execute("SELECT * FROM profiles WHERE name=?", (userName,))
        existing_user = c.fetchone()

        if existing_user:
            # If the user already exists, return an error message
            con.close()
            return jsonify({'error': 'User already exists. Please try a new username.'}), 409
        
        # If the user does not exist, proceed with registration
        c.execute("INSERT INTO profiles (name, passWord, phoneNumber, email) VALUES (?, ?, ?, ?)",
                  (userName, hashed_password, phoneNumber, email))
        con.commit()
        con.close()

        # Return success message after registration
        return jsonify({'message': 'Registration successful, you can now log in.'}), 201
    
    except Exception as e:
        # Catch any unexpected errors and return a response
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


# —————————————————————————————————————————————————————— ANCHORS ——————————————————————————————————————————————————————

# ADD ANCHOR ROUTE
@app.route('/add_anchor', methods=['POST'])
def add_anchor_to_dashboard():
    # Extract data from the incoming JSON payload
    data = request.get_json()

    # Get user_id from session (user is logged in)
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401  # Unauthorized if no user is logged in

    # Extract individual data fields from the received JSON
    anchor_id = data.get('anchor_id') # user-defined
    anchor_name = data.get('anchor_name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    altitude = data.get('altitude')

    # Check if all required data was received
    if anchor_id and anchor_name and latitude and longitude and altitude!=None:
        try:
            # Insert the received anchor data into the 'anchors' table
            con = sqlite3.connect('users.db')
            c = con.cursor()
            c.execute("""INSERT INTO anchors (anchor_id, user_id, anchor_name, latitude, longitude, altitude, created_at) 
                         VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                      (anchor_id, user_id, anchor_name, latitude, longitude, altitude))
            con.commit()

            # Get the ID of the newly inserted anchor
            anchor_id = c.lastrowid

            con.close()

            # Return a success response to the frontend with the server-generated ID
            return jsonify({'message': 'Anchor successfully added to dashboard!', 'anchor_id': anchor_id}), 201
        except Exception as e:
            # In case of an error, return an error response
            return jsonify({'error': f'Error occurred while adding anchor: {str(e)}'}), 500
    else:
        # Check for missing fields
        missing_fields = []
        if not anchor_id:
            missing_fields.append('anchor_id')
        if not anchor_name:
            missing_fields.append('anchor_name')
        if latitude is None:
            missing_fields.append('latitude')
        if longitude is None:
            missing_fields.append('longitude')
        if altitude is None:
            missing_fields.append('altitude')

        # If any required field is missing, return an error with details
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        return jsonify({'error': f'Missing one of the required fields'}), 400



# EDIT ANCHOR PAGE
@app.route('/edit_anchor', methods=['POST'])
def edit_anchor():
    # Get user_id from the session
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401 # Unauthorized no user logged in
    

    # Extract data from incoming frontend payload
    data = request.get_json()
    anchor_id = data.get('anchor_id')
    anchor_name = data.get('anchor_name')
    new_name = data.get('new_anchor_name')
    new_latitude = data.get('latitude')
    new_longitude = data.get('longitude')
    new_altitude = data.get('altitude')

    # Ensure we got everything needed
    if anchor_id and anchor_name and new_name and new_latitude and new_longitude and new_altitude:
        try:
            # Connect to db
            con = sqlite3.connect('users.db')
            c = con.cursor()

            # Fetch the anchor's current details
            c.execute("SELECT * FROM anchors WHERE anchor_id=? and user_id=?", (anchor_id, user_id))
            anchor = c.fetchone()

            if anchor:  # make sure its a valid in 
                # Update anchor in the database
                c.execute("""UPDATE anchors SET anchor_id = ?, anchor_name = ?, latitude = ?, longitude = ?, altitude = ?, created_at = CURRENT_TIMESTAMP
                    WHERE anchor_name = ? and user_id = ?""", (anchor_id, new_name, new_latitude, new_longitude, new_altitude, anchor_name, user_id))
                con.commit()
                con.close()
                return jsonify({'message': 'Anchor updated successfully'}), 200
            else:
                return jsonify({'error': 'Anchor not found or not authorized to edit'}), 404
        except Exception as e:
            return jsonify({'error': f'Error occurred while updating anchor: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Missing data for anchor update'}), 400


# GET ANCHORS ROUTE
@app.route('/get_anchors', methods=['GET'])
def get_anchors():
    try:
        # ✅ Get user_id from session
        user_id = session.get('user_id') or request.args.get('user_id')

        if not user_id:
            return jsonify({'error': 'User not logged in'}), 401  # Unauthorized
        
       # print(f"User ID received: {user_id}")


        # ✅ Connect to SQLite database
        con = sqlite3.connect('users.db')
        cur = con.cursor()

        # ✅ Fetch only the anchors belonging to the logged-in user
        cur.execute("SELECT anchor_id, anchor_name, latitude, longitude, altitude FROM anchors WHERE user_id=?", (user_id,))
        anchors = cur.fetchall()
       # print("Anchors fetched from DB:", anchors)  # Debug print
        con.close()

        # ✅ Convert data to JSON format
        anchor_list = [
            {
                "id": int(row[0]),
                "name": row[1],     # Anchor name
                "latitude": row[2], # Latitude
                "longitude": row[3], # Longitude
                "altitude": row[4]  # Altitude
            }
            for row in anchors
        ]

        return jsonify({"anchors": anchor_list, "message": "Anchors fetched successfully"}), 200

    except Exception as e:
        return jsonify({"error": f"Error retrieving anchors: {str(e)}"}), 500



# DELETE ANCHOR ROUTE
@app.route('/delete_anchor', methods=['POST'])
def delete_anchor():
    try:
        # Extract data from the incoming JSON payload
        data = request.get_json()
        anchor_name = data.get('anchor_name')  # Get anchor name from request
        user_id = session.get('user_id')  # Get user_id from session

        print(f"🟢 Incoming Delete Request - Anchor Name: {anchor_name}, User ID: {user_id}")

        # Validate user session
        if not user_id:
            return jsonify({'error': 'User not logged in'}), 401

        # Validate anchor_name
        if not anchor_name:
            return jsonify({'error': 'Missing anchor name'}), 400

        # Database connection
        con = sqlite3.connect('users.db')
        cur = con.cursor()

        # ✅ Check if the anchor exists for the given user_id and anchor_name
        cur.execute("SELECT * FROM anchors WHERE user_id = ? AND anchor_name = ?", (user_id, anchor_name))
        anchor = cur.fetchone()

        if not anchor:
            print(f"❌ No anchor found for User ID {user_id} and Anchor Name {anchor_name}")
            return jsonify({'error': 'Anchor not found or unauthorized'}), 404

        # ✅ Delete the anchor
        cur.execute("DELETE FROM anchors WHERE user_id = ? AND anchor_name = ?", (user_id, anchor_name))
        con.commit()
        con.close()

        print(f"✅ Successfully deleted Anchor for User ID: {user_id} and Anchor Name: {anchor_name}")
        return jsonify({'message': 'Anchor deleted successfully'}), 200

    except Exception as e:
        print(f"❌ Error deleting anchor: {str(e)}")
        return jsonify({'error': f'Error deleting anchor: {str(e)}'}), 500



# —————————————————————————————————————————————————————— TAGS ——————————————————————————————————————————————————————


# NEED KEN TO SEND TAG INFO WITH TAG NAME, LATITUDE, and LONGITUDE
# Very SIMILAR TO ADDING AN ANCHOR

# Helper Function to help get latitude and longitude from the anisette server
# Will run the request_reports.py script and process the output
python_exec = "/home/sdp3/haystackk/FindMy/venv/bin/python3"
program_path = "/home/sdp3/haystackk/FindMy/request_reports.py"

def run_request_report():
    try:
        result = subprocess.run([python_exec, program_path],
        capture_output=True,
        text=True,
        check=True
        )
        start_index = result.stdout.find('[')
        end_index = result.stdout.rfind(']')

        if start_index != -1 and end_index != -1:
            json_str = result.stdout[start_index:end_index + 1]

            ble_data = json.loads(json_str)
            print(ble_data)
        return ble_data
    except subprocess.CalledProcessError as e:
        print("Error running request_reports.py:", e.stderr)
        return []

def fetch_ble_locations_periodically():
    while True:
        ble_data = run_request_report()

        
        try:
            con = sqlite3.connect('users.db', timeout=10)
            cur = con.cursor()

            for tag in ble_data:

                tag_id = tag['tag_id']
                lat = tag['latitude']
                lon = tag['longitude']
                timestamp = tag['timestamp']

                # Convert timestamp to SQL datetime format
                ble_datetime = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

                # Check if the tag already exists in the tags table by tag_name
                cur.execute("SELECT * FROM tags WHERE tag_id = ?", (tag_id,))
                existing_tag = cur.fetchone()

                # Get current number of tags in tag table
                cur.execute("SELECT COUNT(*) FROM tags")
                tag_count = cur.fetchone()[0]
                tag_name = f"tag {tag_count + 1}"

                if existing_tag:
                    # Tag exists, update latitude and longitude
                    cur.execute("""
                        UPDATE tags
                        SET user_id = ?, ble_lat = ?, ble_long = ?, ble_timestamp = ?
                        WHERE tag_id = ?
                    """, (1, lat, lon, ble_datetime, tag_id))
                    message = "Tag updated successfully!"

                else:
                    # Tag doesn't exists, add new tag
                    cur.execute("""
                        INSERT INTO tags (tag_id, user_id, tag_name, ble_lat, ble_long, ble_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (tag_id, 1, tag_name, lat, lon, ble_datetime))
                    message = "New tag added successfully!"

                # Insert into `tag_locations`
                cur.execute("""
                    INSERT INTO tag_locations (tag_id, latitude, longitude, timestamp)
                    VALUES (?, ?, ?, ?)
                    """, (tag_id, lat, lon, timestamp))

            con.commit()
            con.close()
            #    print(f"[BLE Worker] Successfully updated {len(ble_data)} tags.")
        except Exception as e:
            print(f"[BLE Worker] Error updating BLE data: {e}")

        time.sleep(10)  # Wait 30 seoncds
"""
@app.route('/add_tag', methods=['POST'])
def add_tag_location():
    # Get user_id from session
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401

    # Get data from the request
    data = request.get_json()
    tag_name = data.get('tag_name') 
    x_offset = data.get('x_offset')  # Relative position in meters on the X-axis
    y_offset = data.get('y_offset')  # Relative position in meters on the Y-axis

    if not tag_name or x_offset is None or y_offset is None:
        return jsonify({'error': 'Missing required data (tag_id, anchor_id, x_offset, y_offset)'}), 400

    try:
        # Connect to the database
        con = sqlite3.connect('users.db')
        c = con.cursor()

        # Check if the tag exists in the tags table
        c.execute("SELECT tag_name FROM tags WHERE tag_name = ?", (tag_name,))
        existing_tag = c.fetchone()

        if not existing_tag:
            # If the tag doesn't exist, insert it into the tags table
            c.execute("""
              #  INSERT INTO tags (tag_name, user_id, latitude, longitude)
               # VALUES (?, ?, ?, ?)
          #  """, (tag_name, user_id, x_offset, y_offset))  # Default location set to 0.0, 0.0

        # Fetch the anchor's GPS coordinates
        #c.execute("SELECT latitude, longitude FROM anchors WHERE id=?", (anchor_id,))

        # Update the tag's most recent location in the 'tags' table
       # c.execute("""
        #     UPDATE tags
        #     SET latitude = ?, longitude = ?
        #     WHERE tag_id = ?
        # """, (tag_lat, tag_lon, tag_id))

        # # Insert the new location into the tag_locations table to maintain the history
        # c.execute("""INSERT INTO tag_locations (tag_id, latitude, longitude, mode, timestamp) 
        #              VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""", 
        #           (tag_id, tag_lat, tag_lon, "UWB"))

        # # Commit the transaction
        #con.commit()
        #con.close()

        #return jsonify({'message': 'Tag location successfully added and updated'}), 201

    #except Exception as e:
        #return jsonify({'error': f'Error occurred while adding tag location: {str(e)}'}), 500


@app.route('/add_tag_tcp', methods=['POST'])
def add_tag_from_tcp():
    # Get JSON data from the TCP client
    data = request.json

    if not data:
        return jsonify({"message": "No data received or data is not valid JSON."}), 400

    tag_id = data.get('tag_id')
    tag_name = data.get('tag_name')
    tag_latitude = data.get('latitude')  # Latitude of the tag
    tag_longitude = data.get('longitude')  # Longitude of the tag
    user_id = data.get('user_id')

    # Connect to the SQLite database
    con = sqlite3.connect('users.db')
    cur = con.cursor()

    # Check if the tag already exists in the tags table by tag_name
    cur.execute("SELECT * FROM tags WHERE tag_id = ?", (tag_id,))
    existing_tag = cur.fetchone()

    if existing_tag:
        # Tag exists, update latitude and longitude
        cur.execute("""
            UPDATE tags
            SET user_id = ?, latitude = ?, longitude = ?, created_at = DATETIME('now', '-4 hours')
            WHERE tag_id = ?
        """, (user_id, tag_latitude, tag_longitude, tag_id))
        message = "Tag updated successfully!"

    else:
        # Tag doesn't exist, add a new tag
        cur.execute("""
            INSERT INTO tags (tag_id, user_id, tag_name, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
        """, (tag_id, user_id, tag_name, tag_latitude, tag_longitude))
        con.commit()
        message = "New tag added successfully!"

    # Fetch the user's boundary (assuming 4 corner points are stored)
    cur.execute("SELECT point1_lat, point1_lon, point2_lat, point2_lon, point3_lat, point3_lon, point4_lat, point4_lon FROM boundaries WHERE user_id = ?", (user_id,))
    boundary_points = cur.fetchone()

    if boundary_points:
        try:
            # Create the boundary polygon using Shapely
            boundary_polygon = Polygon([
                (boundary_points[0], boundary_points[1]),  # point 1
                (boundary_points[2], boundary_points[3]),  # point 2
                (boundary_points[4], boundary_points[5]),  # point 3
                (boundary_points[6], boundary_points[7])   # point 4
            ])

            # Create a Shapely Point object for the tag's location
            tag_point = Point(tag_longitude, tag_latitude)

            # Check if the tag is within the boundary
            if boundary_polygon.contains(tag_point):
                tag_status = True  # Inside the boundary
            else:
                tag_status = False  # Outside the boundary

            # Update the tag status
            cur.execute("""
                UPDATE tags
                SET status = ?
                WHERE tag_id = ?
            """, (tag_status, tag_id))
        except Exception as e:
            print("Boundary check failed:", e) # Safe logging
    else:
        print(f"No boundary found for user_id {user_id}. Skipping boundary check.")


    # Retrieve the tag_id of the newly inserted or updated tag
    cur.execute("SELECT tag_id FROM tags WHERE tag_id = ?", (tag_id,))
    print(type(cur))
    tag_id = cur.fetchone()[0]  # Fetch the tag_id after insert or update

    # Save the location into the tag_locations table
    cur.execute("""
        INSERT INTO tag_locations (tag_id, tag_name, latitude, longitude, mode)
        VALUES (?, ?, ?, ?, ?)
    """, (tag_id, tag_name, tag_latitude, tag_longitude, "TCP"))

    # Commit the transaction and close the connection
    con.commit()
    con.close()

    # Send response
    return jsonify({"message": message, "tag": tag_id, "latitude": tag_latitude, "longitude": tag_longitude})



# EDIT TAG PAGE
@app.route('/edit_tag', methods=['POST'])
def edit_tag():
    # Get user_id from session (assuming user is logged in)
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401  # Unauthorized if no user is logged in

    # Extract data from incoming JSON request
    data = request.get_json()

    # Extract tag details from the request
    tag_id = data.get('tag_id')  # the ID of the tag to edit
    new_tag_name = data.get('tag_name')  # new name for the tag
    new_latitude = data.get('latitude')  # new latitude for the initial position
    new_longitude = data.get('longitude')  # new longitude for the initial position


    new_mode = data.get('mode', 'UWB')  # new mode (default to 'UWB' if not provided)

    # Ensure that we have the required data
    if tag_id and (new_tag_name or new_latitude is not None or new_longitude is not None):
        try:
            # Connect to the database
            con = sqlite3.connect('users.db')
            c = con.cursor()

            # Fetch the tag's current details from the 'tags' table
            c.execute("SELECT * FROM tags WHERE tag_id=?", (tag_id,))
            tag = c.fetchone()

            if not tag:
                return jsonify({'error': 'Tag not found'}), 404  # If tag does not exist, return an error

            # Update the tag's name
            if new_tag_name:
                c.execute("""UPDATE tags SET tag_name = ?, created_at = CURRENT_TIMESTAMP WHERE tag_id = ?""",
                          (new_tag_name, tag_id))

            # If new latitude and longitude are provided, update the tag's initial position
            if new_latitude is not None and new_longitude is not None:
                # We assume we're updating the initial position in the 'tag_locations' table
                c.execute("""UPDATE tag_locations SET latitude = ?, longitude = ?, mode = ?, timestamp = CURRENT_TIMESTAMP
                             WHERE tag_id = ?""", (new_latitude, new_longitude, new_mode, tag_id))

            con.commit()
            con.close()

            # Return success response
            return jsonify({'message': 'Tag successfully updated'}), 200

        except Exception as e:
            # Handle any errors
            return jsonify({'error': f'Error occurred while updating tag: {str(e)}'}), 500

    else:
        return jsonify({'error': 'Missing required data (tag_id, tag_name, latitude, longitude)'}), 400

# DELETE TAG PAGE
@app.route('/delete_tag', methods=['POST'])
def delete_tag():
    # Get user_id from session (assuming the user is logged in)
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401  # Unauthorized if no user is logged in

    # Extract data from incoming JSON request
    data = request.get_json()

    # Extract the tag_id from the request
    tag_name = data.get('tag_name')

    # Ensure that the tag_id is provided
    if tag_name:
        try:
            # Connect to the database
            con = sqlite3.connect('users.db')
            c = con.cursor()

            # Fetch the tag's current details from the 'tags' table
            c.execute("SELECT * FROM tags WHERE tag_name=?", (tag_name,))
            tag = c.fetchone()

            if not tag:
                return jsonify({'error': 'Tag not found'}), 404  # If tag does not exist, return an error

            # Check if the user owns the tag (based on user_id)
            if tag[1] != user_id:  # Assuming 'user_id' is at index 1 in the fetched tag tuple
                return jsonify({'error': 'You do not have permission to delete this tag'}), 403  # Forbidden

            # Delete related entries in 'tag_locations'
            c.execute("DELETE FROM tag_locations WHERE tag_name=?", (tag_name,))

            # Delete the tag from the database
            c.execute("DELETE FROM tags WHERE tag_name=?", (tag_name,))
            con.commit()
            con.close()

            # Return success response
            return jsonify({'message': 'Tag successfully deleted'}), 200

        except Exception as e:
            # Handle any errors
            return jsonify({'error': f'Error occurred while deleting tag: {str(e)}'}), 500

    else:
        return jsonify({'error': 'Missing tag_id'}), 400  # Bad request if no tag_id is provided

# Acquire a Tag's most recent location
@app.route('/get_tags', methods=['GET'])
def get_tag_location():
    # Get user_id from session
    user_id = session.get('user_id') or request.args.get('user_id')
    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401  # Unauthorized if no user is logged in

    try:
        # Connect to Database
        con = sqlite3.connect('users.db')
        c = con.cursor()

        # Fetch the latitude, longitude, and tag_name for all tags of the given user_id
        c.execute("""
            SELECT tag_id, tag_name, latitude, longitude, altitude, status, created_at, ble_lat, ble_long, ble_timestamp
            FROM tags
            WHERE user_id = ?
            """, (user_id,))

        # Fetch the tag data
        tags_locations = c.fetchall()
        print(f"Tags fetched; {tags_locations}")
        # Fetch boundary points
        c.execute("""
            SELECT point1_lat, point1_lon, point2_lat, point2_lon,
                   point3_lat, point3_lon, point4_lat, point4_lon
            FROM boundaries WHERE user_id = ?
        """, (user_id,))
   

        boundary_polygon = Polygon([
            (boundary[1], boundary[0]),  # lon, lat
            (boundary[3], boundary[2]),
            (boundary[5], boundary[4]),
            (boundary[7], boundary[6])
        ])

        result = []
        for tag in tags_locations:
            tag_id, tag_name, lat, lon, alt, status, created_at, ble_lat, ble_long, ble_ts = tag

            # Determine which timestamp is more recent
            use_uwb = False
            if ble_ts and created_at:
                use_uwb = created_at > ble_ts
            elif created_at and not ble_ts:
                use_uwb = True
            elif ble_ts and not created_at:
                use_uwb = False
            else:
                # If both timestamps are missing, skip this tag
                continue

            if use_uwb:
                lat_to_use = lat
                lon_to_use = lon
            else:
                lat_to_use = ble_lat
                lon_to_use = ble_long

            # Check if point is within boundary
            tag_point = Point(lon_to_use, lat_to_use)
            inside = boundary_polygon.contains(tag_point)

            if inside != bool(status):
                c.execute("UPDATE tags SET status = ? WHERE tag_id = ?", (inside, tag_id))

            result.append({
                'id': tag_id,
                'name': tag_name,
                'latitude': lat_to_use,
                'longitude': lon_to_use,
                'altitude': alt,
                'status': inside,
            })
        
        con.commit()
        con.close()
        # Return the list of tags with their locations
        return jsonify({'tags_location': result}), 200
        

    except Exception as e:
        return jsonify({'error': f'Error occurred while fetching tags location: {str(e)}'}), 500

    

# Request 24-hour history of a tag
@app.route('/get_tag_location_history', methods=['GET'])
def get_tag_location_history():
    # Get user_id from session (assuming user is logged in)
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401  # Unauthorized if no user is logged in

    # Get tag_id from incoming JSON request
    data = request.get_json()
    tag_id = data.get('tag_id')

    if not tag_id:
        return jsonify({'error': 'Missing tag_id'}), 400  # Bad request if no tag_id is provided

    try:
        # Connect to Database
        con = sqlite3.connect('users.db')
        c = con.cursor()

        # Have to figure out how to acquire this data 

    except Exception as e:
        return jsonify({'error': f'Error occurred while fetching tag location history: {str(e)}'}), 500

@app.route('/clear_tag_locations', methods=['GET'])
def clear_tag_locations():
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401  # Unauthorized if no user is logged in

    
    try:
        con = sqlite3.connect('users.db')
        c = con.cursor()

        c.execute("""
            DELETE FROM tag_locations
                  """)
        con.commit()
        con.close()
        return jsonify({'message': 'Cleared out tag_locations successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Error occurred while deleting tag location history: {str(e)}'}), 500
    


# —————————————————————————————————————————————————————— BOUNDARY ——————————————————————————————————————————————————————

# Save the 4 coordinates of a boundary within a table
@app.route('/save_boundary', methods=['POST'])
def save_boundary():
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401 # Unauthorized if no user logged in
    
    data = request.get_json()
    points = data.get('points')

    if not points or len(points) != 4:
        return jsonify({"error": 'Exactly 4 boundary points are required'}), 400

    try:
        con = sqlite3.connect('users.db')
        cur = con.cursor()

        # Save or replace user's boundary
        cur.execute("""INSERT OR REPLACE INTO boundaries
            (user_id, point1_lat, point1_lon,
            point2_lat, point2_lon,
            point3_lat, point3_lon,
            point4_lat, point4_lon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                points[0]['lat'], points[0]['lon'],
                points[1]['lat'], points[1]['lon'],
                points[2]['lat'], points[2]['lon'],
                points[3]['lat'], points[3]['lon']
            )
        )


        con.commit()
        return jsonify({'success': True}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        con.close()


@app.route('/get_boundaries', methods=['GET'])
def get_boundaries():
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401

    con = sqlite3.connect('users.db')
    cur = con.cursor()

    cur.execute("""
        SELECT point1_lat, point1_lon,
               point2_lat, point2_lon,
               point3_lat, point3_lon,
               point4_lat, point4_lon
        FROM boundaries
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()
    con.close()

    if not row:
        return jsonify({'message': 'No boundary found'}), 404

    points = [
        {"lat": row[0], "lon": row[1]},
        {"lat": row[2], "lon": row[3]},
        {"lat": row[4], "lon": row[5]},
        {"lat": row[6], "lon": row[7]}
    ]

    return jsonify({"points": points})


@app.route('/delete_boundaries', methods=['POST'])
def delete_all_boundaries():
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401

    try:
        con = sqlite3.connect('users.db')
        cur = con.cursor()

        cur.execute("DELETE FROM boundaries WHERE user_id = ?", (user_id,))
        con.commit()
        con.close()

        return jsonify({'message': 'All boundaries deleted for this user.'}), 200

    except Exception as e:
        return jsonify({'error': f'Error deleting boundaries: {str(e)}'}), 500


@app.route('/set_tag_status', methods=['GET'])
def set_tag_status_by_id():
    tag_id = request.args.get('tag_id')
    status = request.args.get('status')

    if not tag_id or status is None:
        return jsonify({'error': 'Missing tag_id or status'}), 400

    try:
        status_bool = status.lower() == 'true'
    except:
        return jsonify({'error': 'Invalid status'}), 400

    con = sqlite3.connect('users.db')
    con.execute('UPDATE tags SET status = ? WHERE tag_id = ?', (status_bool, tag_id))
    con.commit()
    con.close()

    return jsonify({'message': 'Tag status updated successfully'})


if __name__ == "__main__":
    ble_thread = threading.Thread(target=fetch_ble_locations_periodically, daemon=True)
    ble_thread.start()

    app.run(debug=True, host="0.0.0.0", port=5000)
