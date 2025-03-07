import time

class Anchor:
    def __init__(self, id, x_coord, y_coord):
        self.id = id
        self.x_coord = x_coord
        self.y_coord = y_coord
        self.dist = 0
        self.updated = False
        self.last_updated = 0

    def update_x_y_coord(self, x_coord, y_coord):
        self.x_coord = x_coord
        self.y_coord = y_coord
    
    def update_dist(self, dist):
        self.dist = dist
        self.updated = True
        self.last_updated = time.time() # Record when an anchor's distance is last updated
    
    def get_dist(self):
        return self.dist  # Got rid of self.updated bc we will check this before calling for distance
    
    def updated_recently(self, threshold=10):
        if time.time() - self.last_updated > threshold:
            self.updated = False
        return self.updated

    def __str__(self):
        return f"id = {self.id}, x_coord = {self.x_coord}, y_coord = {self.y_coord}"