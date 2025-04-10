import numpy as np
import sqlite3
from Multilateration-3D-Positioning import multilat_lib

def fetch_anchors(user_id, measured_distances=None):
    """
    Fetch anchors for a given user and prepare (anchors, distances) as numpy arrays
    for multilateration.

    Parameters:
    - user_id: the user whose anchors will be fetched
    - measured_distances: list or np.array of distances to each anchor

    Returns:
    - anchors: np.array shape (n, 3)
    - distances: np.array shape (n,)
    """

    # Fetch Anchors' Informations from SQL Database
    con = sqlite3.connect('users.db')
    cur = con.cursor()

    cur.execute("SELECT anchor_id, anchor_name, latitude, longitude, altitude FROM anchors WHERE user_id=?", (user_id,))
    anchors = cur.fetchall()
    con.close()

    print("Anchors fetched from DB:", anchors)  # Debug print

    # Parse the anchor data for the latitude, longitude, and altitude
    anchor_coords = np.array([
        [row[2], row[3], row[4]]  # latitude, longitude, altitude
        for row in anchors
    ])
    distances = np.array(measured_distances)    

    # Check if any tag responses (distances) are given
    if measured_distances == None:
        return anchor_coords
    # Check if the number of anchor matches the numer of tag responses
    elif len(anchors) != len(measured_distances):
        raise ValueError(f"Anchor and distance count mismatch: {len(anchors)} anchors, {len(measured_distances)} distances")

    return anchor_coords, distances


if __name__=="__main__":
    user_id = 1
    anchors = fetch_anchors(user_id)
    distances = [343,234,123]
    multilat_lib(anchors,distances)