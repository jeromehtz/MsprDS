"""
Tests E2E — navigation et parcours utilisateur du dashboard ObRail (Streamlit).

Vérifie que l'application se charge, que le menu latéral fonctionne et que
les différentes pages s'affichent correctement (navigation fluide et intuitive).
"""

import re
import pytest

pytestmark = pytest.mark.e2e


def test_app_loads_with_title(app_page):
    # La page d'accueil affiche le titre du dashboard.
    # (Streamlit met à jour la balise <title> de façon asynchrone : on s'appuie
    #  donc sur le contenu rendu plutôt que sur app_page.title().)
    heading = app_page.get_by_role("heading", name=re.compile("ObRail", re.IGNORECASE))
    heading.first.wait_for(state="visible", timeout=15000)
    assert heading.first.is_visible()


def test_sidebar_navigation_options_present(app_page):
    sidebar = app_page.get_by_test_id("stSidebar")
    sidebar.wait_for(state="visible", timeout=10000)
    # Les 4 options de navigation du menu radio sont présentes et cliquables
    for label in ["Accueil", "Authentification", "Trajets", "API Status"]:
        option = sidebar.get_by_text(label, exact=False).first
        option.wait_for(state="visible", timeout=10000)
        assert option.is_visible()


def test_navigate_to_authentication_page(app_page):
    app_page.get_by_test_id("stSidebar").get_by_text("Authentification").click()
    # La page Auth présente les onglets Login / Register
    app_page.wait_for_selector("text=Login", timeout=10000)
    assert app_page.get_by_text("Login").first.is_visible()
    assert app_page.get_by_text("Register").first.is_visible()


def test_navigate_to_trajets_page(app_page):
    app_page.get_by_test_id("stSidebar").get_by_text("Trajets").click()
    app_page.wait_for_selector("text=filtrage des trajets", timeout=10000)
    assert app_page.get_by_text("filtrage des trajets").first.is_visible()


def test_navigate_to_prediction_page(app_page):
    app_page.get_by_test_id("stSidebar").get_by_text("Prédiction").click()
    app_page.wait_for_selector("text=Prédiction de l'empreinte CO", timeout=10000)
    assert app_page.get_by_text("Prédiction de l'empreinte CO").first.is_visible()


def test_navigate_to_kpi_page(app_page):
    app_page.get_by_test_id("stSidebar").get_by_text("KPI").click()
    app_page.wait_for_selector("text=Indicateurs clés", timeout=10000)
    assert app_page.get_by_text("Indicateurs clés").first.is_visible()


def test_navigate_to_monitoring_page(app_page):
    app_page.get_by_test_id("stSidebar").get_by_text("Monitoring").click()

    db_status = app_page.get_by_text("Base de données").first
    db_status.wait_for(state="visible", timeout=15000)

    assert db_status.is_visible()


def test_navigate_to_api_status_page(app_page):
    app_page.get_by_test_id("stSidebar").get_by_text("API Status").click()

    status_code = app_page.get_by_text("Status code").first
    status_code.wait_for(state="visible", timeout=15000)

    assert status_code.is_visible()
