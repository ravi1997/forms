import os
import sys
import threading
import time
from app import create_app

# Ensure the application package is importable when pytest is invoked via
# the console script entry point (which does not automatically add the
# project root to sys.path).
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="session")
def flask_app():
    """Create and configure a test app instance."""
    app = create_app('testing')
    return app


@pytest.fixture(scope="session")
def flask_server(flask_app):
    """Start the Flask app in a separate thread for Playwright tests."""
    def run_app():
        flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

    server_thread = threading.Thread(target=run_app, daemon=True)
    server_thread.start()

    # Wait for the server to start
    time.sleep(2)

    yield flask_app

    # Cleanup if needed
