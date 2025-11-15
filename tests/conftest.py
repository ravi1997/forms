import os
import sys

# Ensure the application package is importable when pytest is invoked via
# the console script entry point (which does not automatically add the
# project root to sys.path).
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
