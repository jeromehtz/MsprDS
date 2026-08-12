# Stratégie de tests — MSPR DS

Trois niveaux de tests couvrent l'application, conformément aux exigences :

| Niveau | Outil | Emplacement | Ce qui est couvert |
|--------|-------|-------------|--------------------|
| **Unitaires backend** | pytest | [`API/tests/test_unit_*.py`](../API/tests) | Hachage mot de passe, JWT, dépendances d'auth, schémas Pydantic, modèles ORM, **inférence CO₂ XGBoost** |
| **Intégration backend / BDD** | pytest + SQLAlchemy (SQLite) | [`API/tests/test_integration_*.py`](../API/tests) | Flux register/login, CRUD trajets, sécurité JWT, persistance, endpoints racine/monitoring, **prédiction CO₂**, **KPI agrégés** |
| **End-to-End frontend** | Playwright (Python) | [`e2e/`](../e2e) | Navigation, **parcours login → Prédiction / KPI**, accessibilité RGAA/WCAG |

> **Note modèle ML** : les tests de prédiction chargent le vrai modèle
> [`model/modele_XGB_co2_ULTIMATE.pkl`](../model) (XGBoost). Ils nécessitent donc
> `xgboost`, `scikit-learn` et `pandas` (présents dans `API/requirements.txt`),
> ainsi que les référentiels `data/etl_output/od_flows_enriched.csv` et
> `data/co2_comparaison_europe.csv`.

---

## 1. Tests backend (unitaires + intégration)

### Installation

```bash
cd API
pip install -r requirements-dev.txt
```

### Exécution

```bash
cd API
pytest                                   # toute la suite
pytest -m unit                           # uniquement les tests unitaires
pytest -m integration                    # uniquement l'intégration backend/BDD
pytest --cov=. --cov-report=term-missing # avec couverture (~99 %)
```

### Principe d'isolation

Les tests **ne nécessitent pas de PostgreSQL**. La dépendance `get_db` est
redirigée vers une base **SQLite en mémoire** (`StaticPool`) dans
[`API/tests/conftest.py`](../API/tests/conftest.py). Chaque test repart d'un
schéma vierge. Les variables d'environnement (`DATABASE_URL`, `SECRET_KEY`,
`ALGORITHM`) sont injectées par le conftest avant l'import de l'application.

---

## 2. Tests E2E (frontend Streamlit)

> Streamlit n'est pas une SPA React/Vue : **Playwright** est utilisé (plutôt que
> Cypress) car il pilote le DOM rendu de façon robuste et permet l'audit
> d'accessibilité via `axe-core`.

### Installation

```bash
pip install -r e2e/requirements.txt
python -m playwright install chromium
```

### Pré-requis : les deux services doivent tourner

```bash
# Terminal 1 — API (SQLite suffit pour les E2E)
cd API
DATABASE_URL="sqlite:///./e2e.db" SECRET_KEY="e2e" ALGORITHM="HS256" \
  uvicorn main:app --port 8000

# Terminal 2 — Frontend
API_URL="http://127.0.0.1:8000" streamlit run app/app.py --server.port 8501
```

### Exécution

```bash
cd e2e
pytest                       # headless
pytest --headed              # voir le navigateur
STREAMLIT_URL=http://localhost:8501 pytest
```

Si le frontend n'est pas joignable, les tests E2E sont **ignorés (skip)** au lieu
d'échouer.

### Accessibilité (RGAA / WCAG)

[`e2e/test_accessibility.py`](../e2e/test_accessibility.py) injecte `axe-core` et
analyse chaque page selon les règles **WCAG 2.1 A & AA** (socle technique du RGAA).

Le fichier [`e2e/a11y_baseline.json`](../e2e/a11y_baseline.json) liste les
violations **connues** (dette existante, dont une partie provient du chrome de
Streamlit). Le test **échoue sur toute nouvelle violation** (anti-régression) et
**rappelle les violations connues** restant à corriger. Objectif : vider
progressivement ce baseline.

**Violations RGAA actuellement à corriger :**
- `aria-allowed-attr` — attributs ARIA non supportés (éléments Streamlit)
- `button-name` — boutons d'interface sans intitulé accessible
- `color-contrast` — contraste à renforcer (ratio WCAG AA 4.5:1)

---

## 3. Intégration continue

Le workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) exécute :

1. **`test`** — tests backend pytest (avec couverture) + démarrage de l'API.
2. **`test-frontend`** — vérification syntaxe + démarrage Streamlit.
3. **`e2e`** — démarre API + frontend, installe Chromium et lance Playwright.

---

## Récapitulatif des fichiers

```
API/
├── pytest.ini                 # config pytest backend
├── requirements-dev.txt       # pytest, pytest-cov, httpx
└── tests/
    ├── conftest.py            # fixtures (client, db, auth) + BDD SQLite de test
    ├── test_unit_password.py
    ├── test_unit_jwt.py
    ├── test_unit_dependencies.py
    ├── test_unit_schemas.py
    ├── test_unit_models.py
    ├── test_unit_predictor.py      # inférence CO₂ XGBoost
    ├── test_integration_auth.py
    ├── test_integration_trajets.py
    ├── test_integration_app.py
    ├── test_integration_prediction.py  # endpoints /predict
    ├── test_integration_stats.py       # endpoint /stats/kpi (+ jour/nuit)
    ├── test_integration_monitoring.py  # endpoints /monitoring (santé + incidents)
    └── test_integration_mlflow.py      # round-trip MLflow (log/load) du modèle
e2e/
├── pytest.ini
├── requirements.txt           # pytest-playwright
├── conftest.py                # fixtures Playwright + skip si frontend absent
├── a11y_baseline.json         # baseline d'accessibilité RGAA
├── test_navigation.py         # navigation (incl. pages Prédiction & KPI)
├── test_features.py           # parcours login → Prédiction / KPI
└── test_accessibility.py
```
