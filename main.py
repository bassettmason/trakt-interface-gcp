import logging
from utils import post_trakt_list_from_imdb_ids, get_trakt_list

def trakt_api_handler(request):

    headers = {"Content-Type": "application/json"}

    # Handling POST requests
    if request.method == 'POST':
        data = request.get_json(silent=True)  # Get JSON body
        
        list_slug = data.get("name")
        list_data = data.get("media_list")  # Extract media list from JSON body

        if not list_slug or not list_data:
            logging.warning("Missing 'name' or 'media_list' in request data.")
            return ({"error": "Missing 'name' or 'media_list' in request data."}, 400, headers)

        try:
            response = post_trakt_list_from_imdb_ids(list_slug, list_data)
            return (response, 200, headers)
        except Exception as e:
            logging.error(f"Failed to post Trakt list: {e}")
            return ({"error": str(e)}, 500, headers)

    # Handling GET requests
    elif request.method == 'GET':
        id = request.args.get("id")
        if not id:
            logging.warning("Missing 'id'.")
            return ({"error": "Missing id."}, 400, headers)

        try:
            data = get_trakt_item(id)
            return (data, 200, headers)
        except Exception as e:
            logging.error(f"Failed to get Trakt list: {e}")
            return ({"error": str(e)}, 500, headers)

    else:
        return ({"error": "Invalid HTTP method. Use either POST or GET."}, 400, headers)
