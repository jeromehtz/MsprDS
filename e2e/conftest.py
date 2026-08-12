"""
Configuration des tests E2E (Playwright) du frontend Streamlit.

Pré-requis pour exécuter ces tests :
  1. L'API FastAPI tourne (par défaut http://127.0.0.1:8000)
  2. Le frontend Streamlit tourne (par défaut http://localhost:8501)

URLs configurables via variables d'environnement :
  - STREAMLIT_URL (défaut: http://localhost:8501)

Si le frontend n'est pas joignable, les tests sont ignorés (skip) plutôt qu'en échec,
afin de ne pas casser un run où les services ne sont pas démarrés.
"""

import os
import urllib.request

import pytest

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")


def _service_up(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            return resp.status < 500
    except Exception:
        return False


@pytest.fixture(scope="session")
def base_url() -> str:
    return STREAMLIT_URL


@pytest.fixture(scope="session", autouse=True)
def _require_frontend():
    if not _service_up(STREAMLIT_URL):
        pytest.skip(
            f"Frontend Streamlit injoignable sur {STREAMLIT_URL} — "
            "démarrez-le avant de lancer les tests E2E.",
            allow_module_level=True,
        )


@pytest.fixture
def app_page(page, base_url):
    """Ouvre l'application et attend que Streamlit ait fini son rendu initial."""
    page.goto(base_url, wait_until="networkidle")
    # Streamlit rend l'application principale dans un conteneur identifiable
    page.wait_for_selector('[data-testid="stApp"]', timeout=15000)
    return page
