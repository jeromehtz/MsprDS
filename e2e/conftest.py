import os
import urllib.request

import pytest


STREAMLIT_URL = os.getenv(
    "STREAMLIT_URL",
    "http://localhost:8501"
)


def _service_up(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            return resp.status < 500
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def _require_frontend():
    if not _service_up(STREAMLIT_URL):
        pytest.skip(
            f"Frontend Streamlit injoignable sur {STREAMLIT_URL} — "
            "démarrez-le avant de lancer les tests E2E.",
            allow_module_level=True,
        )


@pytest.fixture
def app_page(page):
    """Ouvre l'application Streamlit et attend son rendu initial."""
    page.goto(STREAMLIT_URL, wait_until="networkidle")
    page.wait_for_selector(
        '[data-testid="stApp"]',
        timeout=15000
    )
    return page