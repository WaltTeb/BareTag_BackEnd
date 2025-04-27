import requests

def fetch_tags(user_id=None):
    url = 'http://172.24.131.25:5000/get_tags'
    params = {}

    if user_id:
        params['user_id'] = user_id

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise error for bad status codes
        data = response.json()

        if 'tags_location' in data:
            print("Tags Info:")
            for tag in data['tags_location']:
                print(f"ID: {tag['id']}")
                print(f"Name: {tag['name']}")
                print(f"Latitude: {tag['latitude']}")
                print(f"Longitude: {tag['longitude']}")
                print(f"Altitude: {tag['altitude']}")
                print(f"Status (Inside boundary): {tag['status']}")
                print("-" * 30)
        else:
            print(f"Error or unexpected response: {data}")
    
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    # You can optionally provide a user_id if needed
    user_id = input("Enter user_id (or leave blank if session handles it): ").strip()
    if not user_id:
        user_id = None
    fetch_tags(user_id)
