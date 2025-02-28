from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import sqlite3
from formsubmission import RegistrationForm
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import math
from flask_session import Session  # ✅ Import Flask-Session
from flask_cors import CORS



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



# # LOGOUT PAGE
# @app.route('/logout')
# def logout():
#     # Clear the session data
#     session.clear()
#     return redirect(url_for('login'))


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
    anchor_name = data.get('anchor_name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    # Check if all required data was received
    if anchor_name and latitude and longitude:
        try:
            # Insert the received anchor data into the 'anchors' table
            con = sqlite3.connect('users.db')
            c = con.cursor()
            c.execute("""INSERT INTO anchors (user_id, anchor_name, latitude, longitude, created_at) 
                         VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                      (user_id, anchor_name, latitude, longitude))
            con.commit()
            con.close()

            # Return a success response to the frontend
            return jsonify({'message': 'Anchor successfully added to dashboard!'}), 201
        except Exception as e:
            # In case of an error, return an error response
            return jsonify({'error': f'Error occurred while adding anchor: {str(e)}'}), 500
    else:
        # If any of the required fields are missing, return a bad request error
        return jsonify({'error': 'Missing data (anchor_id, anchor_name, latitude, or longitude)'}), 400


# EDIT ANCHOR PAGE
@app.route('/edit_anchor', methods=['POST'])
def edit_anchor():
    # Get user_id from the session
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401 # Unauthorized no user logged in
    

    # Extract data from incoming frontend payload
    data = request.get_json()
    anchor_name = data.get('anchor_name')
    new_name = data.get('new_anchor_name')
    new_latitude = data.get('latitude')
    new_longitude = data.get('longitude')

    # Ensure we got everything needed
    if anchor_name and new_name and new_latitude and new_longitude:
        try:
            # Connect to db
            con = sqlite3.connect('users.db')
            c = con.cursor()

            # Fetch the anchor's current details
            c.execute("SELECT * FROM anchors WHERE anchor_name=? and user_id=?", (anchor_name, user_id))
            anchor = c.fetchone()

            if anchor:  # make sure its a valid in 
                # Update anchor in the database
                c.execute("""UPDATE anchors SET anchor_name = ?, latitude = ?, longitude = ?, created_at = CURRENT_TIMESTAMP
                    WHERE anchor_name = ? and user_id = ?""", (new_name, new_latitude, new_longitude, anchor_name, user_id))
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
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'error': 'User not logged in'}), 401  # Unauthorized

        # ✅ Connect to SQLite database
        con = sqlite3.connect('users.db')
        cur = con.cursor()

        # ✅ Fetch only the anchors belonging to the logged-in user
        cur.execute("SELECT id, anchor_name, latitude, longitude FROM anchors WHERE user_id=?", (user_id,))
        anchors = cur.fetchall()
        con.close()

        # ✅ Convert data to JSON format
        anchor_list = [
            {
                "id": str(row[0]),  # Convert ID to string
                "name": row[1],     # Anchor name
                "latitude": row[2], # Latitude
                "longitude": row[3] # Longitude
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
        data = request.get_json()
        anchor_id = data.get('anchor_id')
        user_id = session.get('user_id')  

        print(f"🟢 Incoming Delete Request - Anchor ID: {anchor_id}, User ID: {user_id}")  # ✅ Debugging

        if not user_id:
            return jsonify({'error': 'User not logged in'}), 401

        if not anchor_id:
            return jsonify({'error': 'Missing anchor ID'}), 400

        con = sqlite3.connect('users.db')
        cur = con.cursor()

        # ✅ Check if anchor exists before deleting
        cur.execute("SELECT * FROM anchors WHERE id=? AND user_id=?", (anchor_id, user_id))
        anchor = cur.fetchone()

        if not anchor:
            print(f"❌ Anchor ID {anchor_id} not found for User ID {user_id}")
            return jsonify({'error': 'Anchor not found or unauthorized'}), 404

        # ✅ Delete anchor
        cur.execute("DELETE FROM anchors WHERE id=? AND user_id=?", (anchor_id, user_id))
        con.commit()
        con.close()

        print(f"✅ Successfully deleted Anchor ID: {anchor_id} for User ID: {user_id}")
        return jsonify({'message': 'Anchor deleted successfully'}), 200

    except Exception as e:
        print(f"❌ Error deleting anchor: {str(e)}")
        return jsonify({'error': f'Error deleting anchor: {str(e)}'}), 500






# —————————————————————————————————————————————————————— TAGS ——————————————————————————————————————————————————————


# NEED KEN TO SEND TAG INFO WITH TAG NAME, LATITUDE, and LONGITUDE
# Very SIMILAR TO ADDING AN ANCHOR

@app.route('/add_tag', methods=['POST'])
def add_tag():
    # Get user_id from session
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401  # No user logged in

    # Extract data from incoming JSON request
    data = request.get_json()

    # Extract tag details
    tag_name = data.get('tag_name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    # Check if required fields are provided
    if tag_name and latitude is not None and longitude is not None:
        try:
            # Connect to the database
            con = sqlite3.connect('users.db')
            c = con.cursor()

            # Insert the tag into the 'tags' table
            c.execute("""INSERT INTO tags (user_id, tag_name, created_at)
                         VALUES (?, ?, CURRENT_TIMESTAMP)""",
                      (user_id, tag_name))
            con.commit()

            # Get the tag_id of the newly inserted tag (so we can insert it into tag_locations)
            tag_id = c.lastrowid

            # Set mode to default UWB for now, will figure out with logic
            mode = 'UWB'

            # Insert the location data (latitude, longitude, mode) into the 'tag_locations' table
            c.execute("""INSERT INTO tag_locations (tag_id, latitude, longitude, mode, timestamp)
                         VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                      (tag_id, latitude, longitude, mode))
            con.commit()
            con.close()

            # Return success response
            return jsonify({'message': 'Tag successfully added to dashboard'}), 201

        except Exception as e:
            # Handle any errors
            return jsonify({'error': f'Error occurred while adding tag: {str(e)}'}), 500

    else:
        return jsonify({'error': 'Missing data (tag_name, latitude, longitude)'}), 400


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
    tag_id = data.get('tag_id')

    # Ensure that the tag_id is provided
    if tag_id:
        try:
            # Connect to the database
            con = sqlite3.connect('users.db')
            c = con.cursor()

            # Fetch the tag's current details from the 'tags' table
            c.execute("SELECT * FROM tags WHERE tag_id=?", (tag_id,))
            tag = c.fetchone()

            if not tag:
                return jsonify({'error': 'Tag not found'}), 404  # If tag does not exist, return an error

            # Check if the user owns the tag (based on user_id)
            if tag[1] != user_id:  # Assuming 'user_id' is at index 1 in the fetched tag tuple
                return jsonify({'error': 'You do not have permission to delete this tag'}), 403  # Forbidden

            # Delete related entries in 'tag_locations'
            c.execute("DELETE FROM tag_locations WHERE tag_id=?", (tag_id,))

            # Delete the tag from the database
            c.execute("DELETE FROM tags WHERE tag_id=?", (tag_id,))
            con.commit()
            con.close()

            # Return success response
            return jsonify({'message': 'Tag successfully deleted'}), 200

        except Exception as e:
            # Handle any errors
            return jsonify({'error': f'Error occurred while deleting tag: {str(e)}'}), 500

    else:
        return jsonify({'error': 'Missing tag_id'}), 400  # Bad request if no tag_id is provided

# Function needed to find a tag's gps coordinates
# Assumes the grid is in meters, and the location of the anchor is in lat, lon format
def convert_to_gps(anchor_lat, anchor_lon, x_offset, y_offset):
    # Earth radius in meters
    R = 6371000  

    # Convert latitude and longitude to radians
    lat_rad = math.radians(anchor_lat)
    lon_rad = math.radians(anchor_lon)

    # Calculate new latitude and longitude based on the offsets (in meters)
    new_lat = lat_rad + (y_offset / R)
    new_lon = lon_rad + (x_offset / (R * math.cos(math.pi * lat_rad / 180)))

    # Convert back to degrees
    new_lat = math.degrees(new_lat)
    new_lon = math.degrees(new_lon)

    return new_lat, new_lon

# ADD TAG LOCATION ROUTE
@app.route('/add_tag_location', methods=['POST'])
def add_tag_location():
    # Get user_id from session
    user_id = session.get('user_id')

    if user_id is None:
        return jsonify({'error': 'User not logged in'}), 401

    # Get data from the request
    data = request.get_json()
    tag_id = data.get('tag_id')
    anchor_id = data.get('anchor_id')
    x_offset = data.get('x_offset')  # Relative position in meters on the X-axis
    y_offset = data.get('y_offset')  # Relative position in meters on the Y-axis

    if not tag_id or not anchor_id or x_offset is None or y_offset is None:
        return jsonify({'error': 'Missing required data (tag_id, anchor_id, x_offset, y_offset)'}), 400

    try:
        # Connect to the database
        con = sqlite3.connect('users.db')
        c = con.cursor()

        # Fetch the anchor's GPS coordinates
        c.execute("SELECT latitude, longitude FROM anchors WHERE id=?", (anchor_id,))
        anchor = c.fetchone()

        if not anchor:
            return jsonify({'error': 'Anchor not found'}), 404

        anchor_lat = anchor[0]
        anchor_lon = anchor[1]

        # Calculate the tag's GPS coordinates based on the anchor's position
        tag_lat, tag_lon = convert_to_gps(anchor_lat, anchor_lon, x_offset, y_offset)

        # Insert the calculated location into the tag_locations table
        c.execute("""INSERT INTO tag_locations (tag_id, latitude, longitude, mode, timestamp) 
                     VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""", 
                  (tag_id, tag_lat, tag_lon, "UWB"))
        con.commit()
        con.close()

        return jsonify({'message': 'Tag location successfully added'}), 201

    except Exception as e:
        return jsonify({'error': f'Error occurred while adding tag location: {str(e)}'}), 500






if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
