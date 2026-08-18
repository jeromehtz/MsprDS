import os
import requests
import pytest
from playwright.async_api import async_playwright


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
BASE_URL = os.getenv("STREAMLIT_URL", "http://127.0.0.1:8501")

TEST_EMAIL = os.getenv("TEST_EMAIL", "test@example.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "test1234")


# ============================================================
# VÉRIFICATION API
# ============================================================

def check_api():
    print("\n========== VÉRIFICATION API ==========")
    print(f"URL : {API_URL}")

    try:
        response = requests.get(
            API_URL,
            timeout=10
        )

        print(f"STATUS : {response.status_code}")

        if response.status_code != 200:
            raise AssertionError(
                f"\n❌ API inaccessible sur {API_URL}\n"
                f"Status HTTP : {response.status_code}\n"
                f"Réponse : {response.text}"
            )

        print("✅ API disponible")

    except requests.RequestException as e:
        raise AssertionError(
            f"\n❌ API inaccessible sur {API_URL}\n"
            f"Erreur : {e}\n\n"
            f"Assure-toi que FastAPI est lancé avant le test."
        )


# ============================================================
# TEST LOGIN
# ============================================================

@pytest.mark.asyncio
async def test_login_local():

    print("\n")
    print("=" * 60)
    print("              TEST E2E LOGIN LOCAL")
    print("=" * 60)

    # --------------------------------------------------------
    # Vérification API
    # --------------------------------------------------------

    check_api()

    # --------------------------------------------------------
    # Playwright
    # --------------------------------------------------------

    print("========== DÉMARRAGE PLAYWRIGHT ==========")

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        try:

            # ------------------------------------------------
            # Ouverture Streamlit
            # ------------------------------------------------

            print(f"Ouverture : {BASE_URL}")

            await page.goto(
                BASE_URL,
                wait_until="domcontentloaded",
                timeout=30000
            )

            # ------------------------------------------------
            # Attente du chargement
            # ------------------------------------------------

            await page.wait_for_timeout(3000)

            print(f"Titre : {await page.title()}")

            # ------------------------------------------------
            # Vérification page
            # ------------------------------------------------

            body_text = await page.locator("body").inner_text()

            print("\n========== CONTENU PAGE ==========")
            print(body_text[:3000])

            # ------------------------------------------------
            # Navigation vers authentification
            # ------------------------------------------------

            auth_link = page.get_by_text(
                "Authentification",
                exact=True
            )

            if await auth_link.count() > 0:

                print("➡️ Navigation vers Authentification")

                await auth_link.first.click()

                await page.wait_for_timeout(2000)

            else:

                print(
                    "⚠️ Lien Authentification non trouvé, "
                    "la page actuelle est peut-être déjà la page de connexion."
                )

            # ------------------------------------------------
            # Vérification formulaire
            # ------------------------------------------------

            body_text = await page.locator("body").inner_text()

            print("\n========== PAGE AUTHENTIFICATION ==========")
            print(body_text[:3000])

            # ------------------------------------------------
            # Recherche champs
            # ------------------------------------------------

            email_input = page.locator(
                'input[type="email"]'
            ).first

            if await email_input.count() == 0:

                email_input = page.locator(
                    'input[placeholder*="mail" i]'
                ).first

            password_input = page.locator(
                'input[type="password"]'
            ).first

            # ------------------------------------------------
            # Vérification
            # ------------------------------------------------

            assert await email_input.count() > 0, (
                "❌ Champ email introuvable"
            )

            assert await password_input.count() > 0, (
                "❌ Champ mot de passe introuvable"
            )

            print("✅ Champs de connexion trouvés")

            # ------------------------------------------------
            # Remplissage
            # ------------------------------------------------

            await email_input.fill(TEST_EMAIL)

            await password_input.fill(TEST_PASSWORD)

            print("✅ Identifiants renseignés")

            # ------------------------------------------------
            # Bouton connexion
            # ------------------------------------------------

            login_button = page.get_by_role(
                "button",
                name="Connexion"
            )

            if await login_button.count() == 0:

                login_button = page.get_by_text(
                    "Connexion",
                    exact=True
                )

            assert await login_button.count() > 0, (
                "❌ Bouton Connexion introuvable"
            )

            print("✅ Bouton Connexion trouvé")

            # ------------------------------------------------
            # Connexion
            # ------------------------------------------------

            await login_button.first.click()

            print("➡️ Connexion en cours...")

            # ------------------------------------------------
            # Attente résultat
            # ------------------------------------------------

            await page.wait_for_timeout(2000)

            body_text = await page.locator("body").inner_text()

            print("\n========== APRÈS CONNEXION ==========")
            print(body_text[:3000])

            # ------------------------------------------------
            # Vérification succès
            # ------------------------------------------------

            success = (
                "Connexion réussie" in body_text
                or "Bienvenue" in body_text
                or "Déconnexion" in body_text
                or "Se déconnecter" in body_text
            )

            # ------------------------------------------------
            # Vérification erreur
            # ------------------------------------------------

            error_messages = [
                "Identifiants incorrects",
                "Connexion échouée",
                "Erreur de connexion",
                "Unauthorized",
                "401",
                "Invalid credentials",
            ]

            detected_errors = [
                error
                for error in error_messages
                if error in body_text
            ]

            if detected_errors:

                print(
                    f"❌ Erreur de connexion détectée : "
                    f"{detected_errors}"
                )

            assert not detected_errors, (
                f"❌ La connexion a échoué : {detected_errors}"
            )

            assert success, (
                "❌ Aucun indicateur de connexion réussie "
                "n'a été trouvé."
            )

            print("✅ Connexion réussie")

        finally:

            # ------------------------------------------------
            # Screenshot en cas de problème
            # ------------------------------------------------

            try:

                await page.screenshot(
                    path="login_local_result.png",
                    full_page=True
                )

                print(
                    "📸 Screenshot enregistré : "
                    "login_local_result.png"
                )

            except Exception:
                pass

            await browser.close()

            print("========== PLAYWRIGHT TERMINÉ ==========")