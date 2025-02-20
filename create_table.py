# Author: Sean Brown, University of Massachusetts Amherst
# Date: 4/4/2023
# Description: This python script assumes that you already have
# a database.db file at the root of your workspace.
# This python script will CREATE a table called students 
# in the database.db using SQLite3 which will be used
# to store the data collected by the forms in this app
# Execute this python script before testing or editing this app code. 
# Open a python terminal and execute this script:
# python create_table.py

import sqlite3

con = sqlite3.connect('users.db')

# creates table to store users
con.execute("CREATE TABLE profiles(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, phoneNumber TEXT, email TEXT)") 

# creates table to store anchors to associate with users
con.execute("CREATE TABLE anchors (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, anchor_name TEXT, latitude REAL, longitude REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES profiles(id))")

con.execute("CREATE TABLE tags (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tag_name TEXT, latitude REAL, longitude REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES profiles(id))")


con.close()
