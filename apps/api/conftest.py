"""Load the repository-wide test isolation plugin for API-local pytest runs."""

import sys

pytest_plugins = (
    ()
    if "phase23_test_isolation" in sys.modules
    else ("phase23_test_isolation",)
)
