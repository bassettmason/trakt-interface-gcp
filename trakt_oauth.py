import time
import json
import requests
from google.cloud import secretmanager

TRAKT_API_BASE_URL = "https://api.trakt.tv"

def access_secret_version(project_id, secret_id, version_id="latest"):
    """Fetch the specified version of a secret."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def add_secret_version(project_id, secret_id, secret_value):
    """Adds a new version to the given secret."""
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{project_id}/secrets/{secret_id}"

    payload = secret_value.encode("UTF-8")
    client.add_secret_version(request={"parent": parent, "payload": {"data": payload}})

def is_token_expired(expiration_time, buffer_time=300):
    """Check if the token is expired based on the expiration timestamp."""
    current_time = int(time.time())
    return current_time >= (expiration_time - buffer_time)


def refresh_auth_token():
    """Refresh the Trakt auth token using the refresh token."""
    trakt_secret = json.loads(access_secret_version("media-djinn", "TRAKT_SECRET"))

    # Create the payload for the POST request to refresh the token.
    payload = {
        "refresh_token": trakt_secret["OAUTH_REFRESH"],
        "client_id": trakt_secret["CLIENT_ID"],
        "client_secret": trakt_secret["CLIENT_SECRET"],
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "grant_type": "refresh_token"
    }

    headers = {
        'Content-Type': 'application/json'
    }
    
    # Sending POST request to Trakt API to refresh the token.
    response = requests.post(f'{TRAKT_API_BASE_URL}/oauth/token', json=payload, headers=headers)
    
    # If the request was successful, update the trakt_secret with the new values.
    if response.status_code == 200:
        data = response.json()
        trakt_secret["OAUTH_TOKEN"] = data["access_token"]
        trakt_secret["OAUTH_REFRESH"] = data["refresh_token"]
        # Calculate the expiration time based on the current time and expires_in value.
        trakt_secret["OAUTH_EXPIRES_AT"] = int(time.time()) + data["expires_in"]

        # Update the secret in Secret Manager.
        add_secret_version("media-djinn", "TRAKT_SECRET", json.dumps(trakt_secret))
    else:
        # Handle the error. You might want to log this or handle it appropriately for your application.
        # For now, we'll just raise an exception with the error description.
        raise Exception(f"Failed to refresh token. Error: {response.json()['error_description']}")

    return trakt_secret


def generate_headers():
    """Generate headers for Trakt API requests, ensuring a fresh token."""
    trakt_secret = json.loads(access_secret_version("media-djinn", "TRAKT_SECRET"))
    
    if is_token_expired(trakt_secret["OAUTH_EXPIRES_AT"]):
        trakt_secret = refresh_auth_token()

    return {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": trakt_secret["CLIENT_ID"],
        "Authorization": f"Bearer {trakt_secret['OAUTH_TOKEN']}"
    }


def trakt_request(method, url, **kwargs):
    # Constants for rate limits
    POST_LIMIT_DELAY = 1  # 1 second delay for POST, PUT, DELETE
    GET_LIMIT_DELAY = 5 * 60 / 1000  # 5 minutes for 1000 requests for GET, roughly 0.3 second per request

    headers = kwargs.get('headers', {})
    
    # First, attempt the request
    response = requests.request(method, url, **kwargs)

    # Handle rate limiting based on the HTTP method
    if response.status_code == 429:  # 429 HTTP status code indicates rate limit exceeded
        if method in ["POST", "PUT", "DELETE"]:
            time.sleep(POST_LIMIT_DELAY)
        else:  # GET
            # If you're hitting the rate limit for GET, it's a bit tricky since you're likely making requests too fast.
            # One way is to throttle each GET request, but this might slow down your app considerably. For now, we'll use a basic delay:
            time.sleep(GET_LIMIT_DELAY)

        # Retry the request after waiting
        response = requests.request(method, url, **kwargs)

    response.raise_for_status()  # If the retry or the original request was unsuccessful, raise an exception.
    return response
