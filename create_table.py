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
con.execute("CREATE TABLE IF NOT EXISTS profiles(user_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, phoneNumber TEXT, email TEXT)") 

# creates table to store anchors to associate with users
con.execute("CREATE TABLE IF NOT EXISTS anchors (anchor_id INTEGER PRIMARY KEY, user_id INTEGER, anchor_name TEXT, latitude REAL, longitude REAL, altitude REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES profiles(user_id))")

# creates table to store current location of tags of every user
con.execute("CREATE TABLE IF NOT EXISTS tags (tag_id TEXT, user_id INTEGER, tag_name TEXT, latitude REAL, longitude REAL,  altitude REAL, status BOOLEAN, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES profiles(user_id))")

# creates table to store entire history of every tag
con.execute("CREATE TABLE IF NOT EXISTS tag_locations (location_id INTEGER PRIMARY KEY AUTOINCREMENT, tag_id TEXT, tag_name TEXT, latitude REAL, longitude REAL,  altitude REAL, mode TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (tag_id) REFERENCES tags(tag_id))")

con.execute("CREATE TABLE IF NOT EXISTS boundaries(user_id INTEGER PRIMARY KEY, point1_lat REAL, point1_lon REAL, point2_lat REAL, point2_lon REAL, point3_lat REAL, point3_lon REAL, point4_lat REAL, point4_lon REAL, FOREIGN KEY(user_id) REFERENCES profiles(user_id)")

con.close()
