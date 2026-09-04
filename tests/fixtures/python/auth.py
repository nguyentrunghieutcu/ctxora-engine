def refresh_token():
    return "python-rotated"


def authenticate_request(token):
    return refresh_token() if token else None
