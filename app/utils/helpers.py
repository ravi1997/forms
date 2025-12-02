from flask import request, current_app, g, jsonify
from functools import wraps
import traceback
import json


_SENSITIVE_KEYS = {
    'password', 'password_hash', 'confirm_password', 'csrf_token', 'token',
    'access_token', 'refresh_token', 'authorization', 'Authorization', 'secret',
    'stripe_signature', 'stripe-signature'
}


def _mask_sensitive(obj):
    """Recursively mask sensitive values in dicts/lists.

    Returns a copy suitable for logging.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _SENSITIVE_KEYS or any(sk in k.lower() for sk in _SENSITIVE_KEYS):
                out[k] = '***REDACTED***'
            else:
                out[k] = _mask_sensitive(v)
        return out
    elif isinstance(obj, (list, tuple)):
        return [_mask_sensitive(i) for i in obj]
    else:
        return obj


def get_request_data():
    """
    Get data from the request, regardless of the content type.
    """
    if request.is_json:
        return request.get_json()
    else:
        return request.form.to_dict()


def log_route(func):
    """Decorator to log entry, exit, response status and exceptions for route handlers.

    Logs request method/path, request id (if set on `g`), query args and JSON body (if present).
    Catches exceptions, logs full traceback, and returns a safe JSON 500 response so
    that unexpected errors are handled consistently.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = current_app.logger if current_app else None
        rid = getattr(g, 'request_id', None)
        try:
            body = None
            try:
                body = request.get_json(silent=True)
            except Exception:
                body = None

            # Mask sensitive data before logging
            try:
                masked_args = _mask_sensitive(dict(request.args))
            except Exception:
                masked_args = str(request.args)

            try:
                masked_body = _mask_sensitive(body) if body is not None else None
            except Exception:
                masked_body = None

            if logger:
                logger.info(
                    f"Enter {func.__name__} request_id={rid} method={request.method} path={request.path} "
                    f"remote_addr={request.remote_addr} args={masked_args} json={masked_body}"
                )

            result = func(*args, **kwargs)


            # Try to determine status code and response body if possible
            status_code = None
            response_preview = None
            try:
                if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[1], int):
                    status_code = result[1]
                    # If first element is a dict or list, log it
                    if isinstance(result[0], (dict, list)):
                        response_preview = _mask_sensitive(result[0])
                else:
                    # Some responses are Flask Response objects
                    status_code = getattr(result, 'status_code', None)
                    # If it's a Response with JSON mimetype, try to parse body
                    try:
                        mimetype = getattr(result, 'mimetype', '')
                        if mimetype and 'application/json' in mimetype:
                            data = result.get_data(as_text=True)
                            try:
                                parsed = json.loads(data)
                                response_preview = _mask_sensitive(parsed)
                            except Exception:
                                response_preview = data[:200]
                    except Exception:
                        response_preview = None
            except Exception:
                status_code = None

            if logger:
                logger.info(f"Exit {func.__name__} request_id={rid} status={status_code} response={response_preview}")

            return result

        except Exception as e:
            # Log full traceback and return a safe JSON response
            if logger:
                logger.exception(f"Unhandled exception in {func.__name__} request_id={rid}: {e}\n{traceback.format_exc()}")
            try:
                return jsonify({'error': 'server_error', 'message': 'An internal server error occurred'}), 500
            except Exception:
                # If jsonify fails for any reason, re-raise
                raise

    return wrapper
