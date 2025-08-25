import os
import pytest

# Enable database access for all tests by default (pytest-django)
pytestmark = pytest.mark.django_db

# Alternative enforcement for some environments: autouse DB fixture
import pytest

@pytest.fixture(autouse=True)
def _enable_db_access_for_all_tests(db):
    pass


def pytest_collection_modifyitems(config, items):
    """Skip external/live endpoint tests unless explicitly enabled.
    Skips tests in files named 'test_pk_endpoints_local.py' unless RUN_E2E=1.
    """
    run_e2e = os.environ.get("RUN_E2E") == "1"
    skip_e2e = pytest.mark.skip(reason="Skipping E2E tests (set RUN_E2E=1 to enable)")

    for item in items:
        # File-based skip
        path = str(getattr(item, "fspath", ""))
        if path.endswith("test_pk_endpoints_local.py") and not run_e2e:
            item.add_marker(skip_e2e)

