from flask import Flask, render_template, request, redirect, url_for, session
import json
import sqlite3
from formsubmission import RegistrationForm
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "__privatekey__"

@app.route('/') # home page
def Home():
    return render_template('home.html')

#LOGIN PAGE
@app.route('/login', methods=['POST','GET'])
def login():
    if request.method == 'POST':
        userName = request.form['name']
        passWord = request.form['passWord']
        con = sqlite3.connect('users.db')
        c = con.cursor()
        c.execute("SELECT * FROM profiles WHERE name=?", (userName,)) # grabs the user with this username and login
        user = c.fetchone()
        con.close()
        
        if user is None or not check_password_hash(user[2], passWord):  # not a valid user
            return render_template('login.html', error="Invalid Credentials!")
        else: # valid user bring them to their dashboard
            session['user_id'] = user[0] # store user id in session
            session['user_name'] = userName # store user name in session
            return redirect(url_for('dashboard', user_id=user[0], name=userName))
    
    else:
        request.method == 'GET'
        return render_template('login.html')


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


# Function to use to Add an Anchor to a User's Dashboard
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

        # Fetch the user's anchor
        con = sqlite3.connect('users.db')
        c = con.cursor()
        c.execute("SELECT * FROM anchors WHERE user_id=?", (user_id,))
        anchors = c.fetchall()

        # Fetch the user's tags
        c.execute("SELECT * FROM tags WHERE user_id=?", (user_id,))
        tags = c.fetchall() # Fetch updated tags list
        con.close()

        return render_template('dashboard.html', name=name, anchors=anchors, tags=tags, user_id=user_id)
    
    # Handle GET request
    else: # Fetch the user's anchors for the GET request
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
    c.execute("SELECT * FROM anchors WHERE id=?", (anchor_id,))
    anchor = c.fetchone()
    
    # Handle the POST request to update the anchor
    if request.method == 'POST':
        new_name = request.form['anchor_name']
        new_latitude = request.form['latitude']
        new_longitude = request.form['longitude']
        last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Update anchor in the database
        c.execute("""UPDATE anchors SET anchor_name = ?, latitude = ?, longitude = ?, created_at = ?
            WHERE id = ?""", (new_name, new_latitude, new_longitude, last_updated, anchor_id))
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
    c.execute("SELECT * FROM tags WHERE id=?", (tag_id,))
    tag = c.fetchone()

    # Handle the POST request to update the tag
    if request.method == 'POST':
        new_name = request.form['tag_name']
        new_latitude = request.form['latitude']
        new_longitude = request.form['longitude']
        last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Update tag in the database
        c.execute("""UPDATE tags SET tag_name = ?, latitude = ?, longitude = ?, created_at = ? 
                     WHERE id = ?""", (new_name, new_latitude, new_longitude, last_updated, tag_id))
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

    c.execute("DELETE FROM anchors where id=?", (anchor_id,))
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
    c.execute("DELETE FROM tags WHERE id=?", (tag_id,))
    con.commit()
    con.close()

    # Redirect back to dashboard
    return redirect(url_for('dashboard', user_id=user_id, name=name))
     
    
# LOGOUT PAGE
@app.route('/logout')
def logout():
    # Clear the session data (if you're using session for tracking login)
    session.clear()
    return redirect(url_for('login'))

    
if __name__ =="__main__":
    app.run(debug=True)
    



