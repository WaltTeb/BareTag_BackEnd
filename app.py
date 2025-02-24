from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import sqlite3
from formsubmission import RegistrationForm
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = "__privatekey__"

@app.route('/') # home page
def Home():
    return render_template('home.html')

# LOGIN PAGE
@app.route('/login', methods=['POST','GET'])
def login():
    if request.method == 'POST':
        userName = request.get_json()['username']
        passWord = request.get_json()['password']
        con = sqlite3.connect('users.db')
        c = con.cursor()
        c.execute("SELECT * FROM profiles WHERE name=?", (userName,))  # Updated to match profiles table column
        user = c.fetchone()
        con.close()
        
        if user is None or not check_password_hash(user[2], passWord):  # not a valid user
            return jsonify({'error': 'Invalid credentials, please check your username and password'}), 401


        else:  # valid user bring them to their dashboard

            session['user_id'] = user[0]  # store user id in session
            session['user_name'] = userName  # store user name in session
            return jsonify({'message': 'Login successful', 'user_id': user[0], 'user_name': userName}), 200


# REGISTRATION PAGE
@app.route('/registrationform', methods = ['POST', 'GET'])
def registrationform():
    registrationForm = RegistrationForm()
    con = sqlite3.connect('users.db')
    c = con.cursor()
    
    if request.method == 'POST':
        if (request.form["name"]!="" and request.form["passWord"]!=""):
            name = request.form["name"]
            passWord = request.form["passWord"]
            phoneNumber = request.form["phoneNumber"]
            email = request.form["email"]

            # Hash the Password
            hashed_password = generate_password_hash(passWord)

            # Check if the user already exists
            statement = f"SELECT * from profiles WHERE name='{name}';"
            c.execute(statement)
            data = c.fetchone()
            
            if data:   # If user exists, show error message but do not continue with registration
                return render_template("error.html", error="User Already Exists! Please try a new username.")
            
            else:
                # Insert new user if they do not exist
                c.execute("INSERT INTO profiles (name,passWord, phoneNumber, email) VALUES (?,?,?,?)", (name, hashed_password, phoneNumber, email))
                con.commit()
                con.close()

                # Clear session before redirecting to login
                session.clear()

                # After registration, go to login
                return redirect(url_for('login'))  

    elif request.method == 'GET':
        return render_template('register.html', form=registrationForm)


# Function to Add an Anchor to a User's Dashboard
def add_anchor(user_id, anchor_name, latitude, longitude):
    con = sqlite3.connect('users.db')
    c = con.cursor()
    c.execute("""INSERT INTO anchors (user_id, anchor_name, latitude, longitude, created_at)
              VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""", (user_id, anchor_name, latitude, longitude))
    con.commit()
    con.close()

# Function to Add a Tag to a User's Dashboard
def add_tag(user_id, tag_name, latitude, longitude):
    con = sqlite3.connect('users.db')
    c = con.cursor()
    c.execute("""INSERT INTO tags (user_id, tag_name, latitude, longitude, created_at) 
              VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""", (user_id, tag_name, latitude, longitude))
    con.commit()
    con.close()

# FILE UPLOAD AND INSERT ANCHORS FROM JSON
@app.route('/upload_anchors/<int:user_id>/<name>', methods=['POST'])
def upload_anchors(user_id, name):
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and file.filename.endswith('.json'):
        # Securely save the file
        filename = secure_filename(file.filename)
        file_path = f"{filename}"
        file.save(file_path)

        # Open and read the JSON file
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)

        # Insert the anchors into the database
        con = sqlite3.connect('users.db')
        c = con.cursor()

        for anchor in data:
            anchor_name = anchor['id']
            latitude = anchor['latitude']
            longitude = anchor['longitude']

            # Insert anchor into the database for the user
            try:
                c.execute(""" 
                    INSERT INTO anchors (user_id, anchor_name, latitude, longitude, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, anchor_name, latitude, longitude))
            except Exception as e:
                print(f"Error inserting anchor {anchor_name}: {e}")  # Debugging line, you can remove it later

        con.commit()
        con.close()

        # Redirect back to the dashboard after uploading anchors
        return redirect(url_for('dashboard', user_id=user_id, name=name))

    else:
        return "Invalid file format. Please upload a .json file."
    
@app.route('/receive_location', methods=['POST'])
def receive_location():
    # Extract data from incoming JSON payload
    data = request.get_json()

    tag_id = data.get('tag_id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    timestamp = data.get('timestamp')
    
    # Check to make sure JSON had everything you need
    if tag_id and latitude and longitude and timestamp:

        # Insert received location into the 'tag_locations' table
        con = sqlite3.connect('users.db')
        c = con.cursor()
        # Insert the received location data into the 'tag_locations' table
        c.execute("""INSERT INTO tag_locations(tag_id, latitude, longitude, timestamp)
                VALUES (?, ?, ?, ?)""", (tag_id, latitude, longitude, timestamp))
        con.commit()
        con.close()

        return 'Successfully saved', 200 # Successful return message code
    else:
        return 'Error', 400
    


# Dashboard PAGE (User Profile + Anchors + Tags)
@app.route('/dashboard/<int:user_id>/<name>', methods = ['GET', 'POST'])
def dashboard(user_id, name):
    # Handle POST request
    if request.method == 'POST':
        # Add new anchor to the user's profile
        if 'anchor_name' in request.form:
            anchor_name = request.form['anchor_name']
            latitude = request.form['latitude']
            longitude = request.form['longitude']
            if anchor_name:
                add_anchor(user_id, anchor_name, latitude, longitude)
        
        # Add new tag to the user's profile
        if 'tag_name' in request.form:
            tag_name = request.form['tag_name']
            latitude = request.form['tag_latitude']
            longitude = request.form['tag_longitude']
            if tag_name:
                add_tag(user_id, tag_name, latitude, longitude)

        # Fetch the user's anchors
        con = sqlite3.connect('users.db')
        c = con.cursor()
        c.execute("SELECT * FROM anchors WHERE user_id=?", (user_id,))
        anchors = c.fetchall()

        # Fetch the user's tags
        c.execute("SELECT * FROM tags WHERE user_id=?", (user_id,))
        tags = c.fetchall()  # Fetch updated tags list
        con.close()

        return render_template('dashboard.html', name=name, anchors=anchors, tags=tags, user_id=user_id)
    
    # Handle GET request
    else:  # Fetch the user's anchors for the GET request
        con = sqlite3.connect('users.db')
        c = con.cursor()
        c.execute("SELECT* FROM anchors WHERE user_id=?", (user_id,))
        anchors = c.fetchall()

        c.execute("SELECT * FROM tags WHERE user_id=?", (user_id,))
        tags = c.fetchall()
        con.close()
        
        return render_template('dashboard.html', name=name, anchors=anchors, tags=tags, user_id=user_id)
    
# EDIT ANCHOR PAGE
@app.route('/edit_anchor/<int:anchor_id>/<int:user_id>/<name>', methods=['GET', 'POST'])
def edit_anchor(anchor_id, user_id, name):
    con = sqlite3.connect('users.db')
    c = con.cursor()

    # Fetch the anchor's current details
    c.execute("SELECT * FROM anchors WHERE anchor_id=?", (anchor_id,))
    anchor = c.fetchone()
    
    # Handle the POST request to update the anchor
    if request.method == 'POST':
        new_name = request.form['anchor_name']
        new_latitude = request.form['latitude']
        new_longitude = request.form['longitude']
        last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Update anchor in the database
        c.execute("""UPDATE anchors SET anchor_name = ?, latitude = ?, longitude = ?, created_at = ?
            WHERE anchor_id = ?""", (new_name, new_latitude, new_longitude, last_updated, anchor_id))
        con.commit()
        con.close()

        # Redirect back to the dashboard after updating
        return redirect(url_for('dashboard', user_id=user_id, name=name))

    # Handle the GET request
    else:
        con.close()
        return render_template('edit_anchor.html', anchor=anchor, user_id=user_id, name=name)

# EDIT TAG PAGE
@app.route('/edit_tag/<int:tag_id>/<int:user_id>/<name>', methods=['GET', 'POST'])
def edit_tag(tag_id, user_id, name):
    con = sqlite3.connect('users.db')
    c = con.cursor()

    # Fetch the tag's current details
    c.execute("SELECT * FROM tags WHERE tag_id=?", (tag_id,))
    tag = c.fetchone()

    # Handle the POST request to update the tag
    if request.method == 'POST':
        new_name = request.form['tag_name']
        new_latitude = request.form['latitude']
        new_longitude = request.form['longitude']
        last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Update tag in the database
        c.execute("""UPDATE tags SET tag_name = ?, latitude = ?, longitude = ?, created_at = ? 
                     WHERE tag_id = ?""", (new_name, new_latitude, new_longitude, last_updated, tag_id))
        con.commit()
        con.close()

        # Redirect back to the dashboard after updating
        return redirect(url_for('dashboard', user_id=user_id, name=name))

    # Handle the GET request to display the edit form
    else:
        con.close()
        return render_template('edit_tag.html', tag=tag, user_id=user_id, name=name)


# DELETE ANCHOR PAGE
@app.route('/delete_anchor/<int:anchor_id>/<int:user_id>/<name>', methods=['GET','POST'])
def delete_anchor(anchor_id, user_id, name):
    con = sqlite3.connect('users.db')
    c = con.cursor()

    c.execute("DELETE FROM anchors WHERE anchor_id=?", (anchor_id,))
    con.commit()
    con.close()

    # Redirect back to the dashboard after deletion
    return redirect(url_for('dashboard', user_id=user_id, name=name))

# DELETE TAG PAGE
@app.route('/delete_tag/<int:tag_id>/<int:user_id>/<name>', methods=['GET', 'POST'])
def delete_tag(tag_id, user_id, name):
    con = sqlite3.connect('users.db')
    c = con.cursor()

    # Delete Tag
    c.execute("DELETE FROM tags WHERE tag_id=?", (tag_id,))
    con.commit()
    con.close()

    # Redirect back to dashboard
    return redirect(url_for('dashboard', user_id=user_id, name=name))

# LOGOUT PAGE
@app.route('/logout')
def logout():
    # Clear the session data
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
