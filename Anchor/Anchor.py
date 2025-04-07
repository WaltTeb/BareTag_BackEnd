import time

class Anchor:
    def __init__(self, id, x_coord, y_coord):
        self.id = id
        self.x_coord = x_coord
        self.y_coord = y_coord
        self.tag_distances = {} # Dictionary to store distances from an anchor to each tag
        self.last_updated = 0

    def update_x_y_coord(self, x_coord, y_coord):
        self.x_coord = x_coord
        self.y_coord = y_coord
    
    def update_dist(self, dist, tag_id):
        self.tag_distances[tag_id] = dist 
        self.last_updated = time.time() # Record when an anchor's distance is last updated
    
    def get_dist(self, tag_id):
        return self.tag_distances.get(tag_id) # Got rid of self.updated bc we will check this before calling for distance
    
    def updated_recently(self, threshold=10):
        if time.time() - self.last_updated > threshold:
            self.updated = False
        return self.updated

    def __str__(self):
        return f"id = {self.id}, x_coord = {self.x_coord}, y_coord = {self.y_coord}"