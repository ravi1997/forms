from flask import request

def get_request_data():
    """
    Get data from the request, regardless of the content type.
    """
    if request.is_json:
        return request.get_json()
    else:
        return request.form.to_dict()
