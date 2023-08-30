import requests
from trakt_oauth import generate_headers, trakt_request

TRAKT_API_BASE_URL = "https://api.trakt.tv"

def post_trakt_list_from_imdb_ids(list_slug, media_list):
    trakt_list = get_trakt_list(list_slug)
    if not trakt_list:
        trakt_list = create_trakt_list(list_slug)
    else:
        clear_trakt_list(list_slug)

    response = add_movies_to_trakt_list(media_list, list_slug)
    new_trakt_list_items = get_trakt_list_items(list_slug)
    return new_trakt_list_items

def get_trakt_list(list_slug):
    url = f"{TRAKT_API_BASE_URL}/users/bassettmason/lists"
    headers = generate_headers()
    
    try:
        response = trakt_request("GET", url, headers=headers)
        user_lists = response.json()
        
        # Check if list_slug.replace("-", " ") matches any name in the lists
        for lst in user_lists:
            if lst["name"] == list_slug.replace("-", " "):
                return lst

    except requests.HTTPError:
        print("Error fetching lists.")
    
    return None



def create_trakt_list(list_slug):
    """Create a new list with the given name on Trakt."""
    url = f"{TRAKT_API_BASE_URL}/users/bassettmason/lists"
    data = {
        "name": f"{list_slug.replace('-', ' ')}",
        "description": "List created from MediaDjinn",
        "privacy": "public",
        "display_numbers": True,
        "allow_comments": True,
        "sort_by": "rank",
        "sort_how": "asc"
    }
    
    response = trakt_request("POST", url, headers=generate_headers(), json=data)
    
    if response.status_code != 201:
        raise Exception("Failed to create list. Please check your credentials and list name.")

    # Parse the JSON response
    response_data = response.json()

    # Extract the 'trakt' ID and 'slug' from the response
    trakt_id = response_data["ids"]["trakt"]
    slug = response_data["ids"]["slug"]

    return {"trakt_list_id": trakt_id, "trakt_list_slug": slug}

def clear_trakt_list(list_slug):
    # Get the old Trakt list items
    old_trakt_list_items = get_trakt_list_items(list_slug)
    
    # Extract movies trakt ids from the old list items
    movie_ids = [{"ids": {"trakt": item["movie"]["ids"]["trakt"]}} for item in old_trakt_list_items if item["type"] == "movie"]

    # Construct the request payload
    data = {
        "movies": movie_ids
    }
    
    # Set up headers and URL for deletion
    headers = generate_headers()
    
    url = f"{TRAKT_API_BASE_URL}/users/bassettmason/lists/{list_slug}/items/remove"
    
    # Send the delete request
    response = trakt_request("POST", url, headers=headers, json=data)
    
    # Check the response
    if response.status_code == 200:
        response_data = response.json()
        if response_data["list"]["item_count"] == 0:
            return response_data
        else:
            raise Exception(f"Failed to clear all movies from the list. Response: {response_data}")
    else:
        response.raise_for_status()


def get_trakt_list_items(list_slug, item_type="movies"):

    url = f"{TRAKT_API_BASE_URL}/users/bassettmason/lists/{list_slug}/items/{item_type}?extended=full"

    headers = generate_headers()

    response = trakt_request("GET", url, headers=headers)
    
    # Check if the response is successful
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()  # Raise an exception for HTTP errors

def add_movies_to_trakt_list(media_list, list_slug):

    # Base URL with user slug hardcoded
    url = f"{TRAKT_API_BASE_URL}/users/bassettmason/lists/{list_slug}/items"
    

    # Generate the movies data from the media_list
    movies_data = [{"ids": {"imdb": imdb_id}} for imdb_id in media_list]
    
    # Construct the data to send in the POST request
    data = {
        "movies": movies_data
    }
    
    headers = generate_headers()
    
    response = trakt_request("POST", url, headers=headers, json=data)
    
    if response.status_code != 201:
        raise Exception(f"Failed to add movies to the list {list_slug}. Response: {response.text}")

    return response.json()
