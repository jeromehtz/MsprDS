"""
Tests E2E d'accessibilité (RGAA / WCAG) du frontend Streamlit.

On injecte axe-core (moteur d'audit d'accessibilité, base technique du RGAA qui
s'appuie sur WCAG) depuis le CDN, puis on exécute l'analyse sur chaque page.

Politique de validation :
- On ne considère que les violations d'impact « critical » ou « serious ».
- Un fichier `a11y_baseline.json` répertorie les violations connues (dette existante,
  dont une partie issue du framework Streamlit).
- Le test ÉCHOUE uniquement sur une NOUVELLE violation (régression) absente du baseline.
- Les violations connues encore présentes sont affichées comme rappel à corriger.

Objectif : garder un garde-fou anti-régression tout en pilotant la résorption
progressive de la dette d'accessibilité jusqu'à vider le baseline.
"""

import json
import os
import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.a11y]

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
BLOCKING_IMPACTS = {"critical", "serious"}
BASELINE_PATH = os.path.join(os.path.dirname(__file__), "a11y_baseline.json")


def _baseline_ids():
    with open(BASELINE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {v["id"] for v in data["known_violations"]}


def _run_axe(page):
    page.add_script_tag(url=AXE_CDN)
    page.wait_for_function("() => window.axe !== undefined", timeout=10000)
    # Analyse selon les règles WCAG 2.1 A & AA (socle du RGAA)
    return page.evaluate(
        """async () => {
            const res = await window.axe.run(document, {
                runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] }
            });
            return res.violations;
        }"""
    )


def _check(page):
    violations = _run_axe(page)
    blocking = [v for v in violations if v.get("impact") in BLOCKING_IMPACTS]
    baseline = _baseline_ids()

    new_violations = [v for v in blocking if v["id"] not in baseline]
    known_present = [v for v in blocking if v["id"] in baseline]

    if known_present:
        print("\n[RGAA] Violations connues encore présentes (à corriger) :")
        for v in known_present:
            print(f"  - {v['id']} ({v['impact']}) : {v['help']} — {len(v['nodes'])} éléments")

    if new_violations:
        summary = json.dumps(
            [{"id": v["id"], "impact": v["impact"], "help": v["help"],
              "nodes": len(v["nodes"])} for v in new_violations],
            indent=2, ensure_ascii=False,
        )
        pytest.fail(f"NOUVELLE(S) violation(s) d'accessibilité (régression RGAA/WCAG) :\n{summary}")


def test_home_page_accessibility(app_page):
    _check(app_page)


def test_auth_page_accessibility(app_page):
    app_page.get_by_test_id("stSidebar").get_by_text("Authentification").click()
    app_page.wait_for_selector("text=Login", timeout=10000)
    _check(app_page)


def test_page_has_lang_attribute(app_page):
    # Critère RGAA : la langue de la page doit être renseignée
    lang = app_page.get_attribute("html", "lang")
    assert lang, "L'attribut lang de <html> est requis (RGAA — langue de la page)"
