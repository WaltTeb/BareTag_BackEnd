import sqlite3

try:
    con = sqlite3.connect('users.db', timeout=10)
    cur = con.cursor()

    # Delete all rows from the tags table
    cur.execute("DELETE FROM tags")
    con.commit()

    print("All tags have been deleted.")

except sqlite3.Error as e:
    print(f"Database error: {e}")
finally:
    if con:
        con.close()
