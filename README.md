# MSPR — Observatoire Rail Europe
## Plateforme d'Analyse Comparative des Trajectoires Ferroviaires Transfrontalières

---

## 1. Contexte et Enjeux

### 1.1 Description du Projet

MSPR (Mobilité Soutenable en Pôles Régionaux) est une plateforme de données intégrant les flux de trajets ferroviaires internationaux en Europe (2016–2024) couvrant six pays : France, Allemagne, Suisse, Italie, Portugal, Espagne.

**Objectif principal :** Centraliser, normaliser et analyser les données de mobilité ferroviaire transfrontalière pour identifier les tendances, évaluer la complétude des données, et supporter la prise de décision en matière de politique de mobilité.

### 1.2 Données Exploitées

- **Flux O/D (Origine-Destination)** : 3 070 trajets bidirectionnels
- **Indicateurs d'émission CO₂** : Comparaison européenne des modes ferroviaires
- **Fréquentation de gares** : Passagers par gare et par période
- **Calendriers de services** : Horaires GTFS normalisés (SNCF, Deutsche Bahn, etc.)
- **Complétude** : Taux de remplissage des champs d'émission (~94–98 % selon la période)

---

## 2. Spécifications Fonctionnelles

### 2.1 Fonctionnalités

| Module | Fonctionnalités |
|--------|-----------------|
| **API REST** | Authentification OAuth2/JWT, gestion utilisateurs, exposition données trajets |
| **Dashboard** | Visualisation complétude CO₂ par pays, service, année ; filtrage multi-critères |
| **Monitoring** | Prometheus + Grafana ; métriques de latence/requêtes API |
| **Données** | ETL CSV → PostgreSQL ; normalisation calendriers GTFS |

---

## 3. Proposition d'Intégration IA

### 3.1 Cas d'Usage IA Identifiés

#### 3.1.1 Prédiction d'Émission CO₂
**Objectif :** Estimer l'émission CO₂ pour trajets avec données manquantes.

- **Modèle** : Régression (Random Forest, Gradient Boosting)
- **Entrées** : distance, type de train, année, classe de service, densité passagers
- **Sortie** : émission CO₂ (kg/km)
- **Précision cible** : ≥ 92%
- **Cas d'usage** : compléter les 6–8% données manquantes

#### 3.1.2 Recommandation d'Itinéraire Optimal
**Objectif :** Suggérer le meilleur trajet selon critères utilisateur.

- **Modèle** : Scoring multi-critères (coût, temps, CO₂, confort)
- **Entrées** : O/D, date, profil utilisateur, budget
- **Sortie** : classement 3 trajets proposés avec justification
- **Intégration** : endpoint `/api/v1/trajet/recommend`
- **Accessibilité** : résultats aussi textuels (JSON) que graphiques

#### 3.1.3 Détection d'Anomalies Données
**Objectif :** Identifier données aberrantes/incohérentes.

- **Modèle** : Isolation Forest, Local Outlier Factor
- **Entrées** : profil trajet, émission, passagers, type service
- **Sortie** : score anomalie [0–1], recommandation nettoyage
- **Application** : flagging datasets pour validation manuelle

#### 3.1.4 Prévision de Trafic Annuel
**Objectif :** Anticiper volume passagers année N+1.

- **Modèle** : ARIMA / Prophet (séries temporelles)
- **Entrées** : historique 9 ans passagers, saisonnalité, événements
- **Sortie** : intervalle confiance [−15%, +20%]
- **Granularité** : par pays, service, pays-pair

### 3.2 Architecture IA

```
┌─────────────────────────────────────────────────────────┐
│           FRONTEND (Tableau de Bord)                    │
|        - Authentification (enregistrement et connexion  |
│        - Liste des itinéraires                          │
|        -                                                |
└────────────────┬────────────────────────────────────────┘
                 │ HTTP REST / WebSocket
┌────────────────▼────────────────────────────────────────┐
│          API GATEWAY (FastAPI)                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Endpoints Existants (Auth, CRUD)                │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Nouveaux Endpoints IA                           │    │
│  │ POST /trajet/predict-co2                        │    │
│  │ POST /trajet/recommend                          │    │
│  │ POST /data/check-anomalies                      │    │
│  │ POST /forecast/traffic                          │    │
│  └─────────────────────────────────────────────────┘    │
└────────────────┬────────────────────────────────────────┘
                 │
    ┌────────────┴─────────────┐
    │                          │
┌───▼──────────────────┐   ┌──▼────────────────────┐
│  ML Service (Python) │   │  PostgreSQL (Données) │
│  ┌────────────────┐  │   │  ┌─────────────────┐  │
│  │ Model Registry │  │   │  │ Models (binary) │  │
│  ├────────────────┤  │   │  ├─────────────────┤  │
│  │ CO₂ Predictor  │  │   │  │ Coefficients    │  │
│  │ Recommender    │  │   │  │ Métriques       │  │
│  │ Anomaly Det.   │  │   │  │ Versions        │  │
│  │ Traffic FCast  │  │   │  └─────────────────┘  │
│  └────────────────┘  │   │                       │
│                      │   │ Cache (Redis opt.)    │
└──────────────────────┘   └───────────────────────┘
         │
         └────► MLflow (Versioning, Serving)
```

### 3.3 Stack Technique IA

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| **Framework ML** | `scikit-learn` | Prédiction, anomalies (léger, prod-ready) |
| **Feature Store** | PostgreSQL + `Feast` (opt.) | Gestion features partagées |
| **Model Registry** | `MLflow` | Versioning, serving, A/B testing |
| **Inference** | `FastAPI` + `Pydantic` | Endpoints ML typés, validation |
| **Conteneurisation** | Docker | Exécuter le projet en local |
| **Monitoring API** | `Prometheus` + `Evidently AI` (opt.) | Drift détection, data quality |

---

## 4. Spécifications Fonctionnelles Détaillées

### 4.1 Endpoint 1 : Prédiction CO₂

```http
POST /api/v1/trajet/predict-co2
Content-Type: application/json

{
  "distance_km": 450.5,
  "train_type": "TGV",
  "year": 2025,
  "service_class": "Intercités",
  "passenger_density": 0.75
}

Response 200:
{
  "predicted_co2_kg_per_km": 23.4,
  "confidence_interval": [21.2, 25.6],
  "model_version": "1.2.0",
  "timestamp": "2025-06-23T14:32:00Z"
}
```

### 4.2 Endpoint 2 : Recommandation Itinéraire

```http
POST /api/v1/trajet/recommend
Content-Type: application/json

{
  "origin": "FR_PARIS",
  "destination": "DE_BERLIN",
  "departure_date": "2025-07-15",
  "user_profile": {
    "criteria_weight": {
      "cost": 0.2,
      "time": 0.3,
      "co2": 0.4,
      "comfort": 0.1
    },
    "accessibility_needs": ["wheelchair", "blind"]
  }
}

Response 200:
{
  "recommendations": [
    {
      "rank": 1,
      "route": "PARIS→LIÈGE→COLOGNE→BERLIN",
      "score": 0.87,
      "cost_eur": 89,
      "duration_hours": 18,
      "co2_kg": 42,
      "accessibility_score": 1.0,
      "justification": "Meilleur équilibre coût-CO₂-accessibilité"
    }
  ]
}
```

### 4.3 Endpoint 3 : Détection Anomalies

```http
POST /api/v1/data/check-anomalies
Content-Type: application/json

{
  "dataset_id": "od_flows_2024",
  "sample_size": 100
}

Response 200:
{
  "anomalies_detected": 7,
  "anomaly_rate": 0.07,
  "high_risk_records": [
    {
      "id": "TRAJET_12345",
      "anomaly_score": 0.92,
      "reason": "Émission CO₂ extrêmement faible pour distance",
      "recommended_action": "review_before_publish"
    }
  ]
}
```

### 4.4 Endpoint 4 : Prévision Trafic

```http
POST /api/v1/forecast/traffic
Content-Type: application/json

{
  "country": "FR",
  "service_type": "TER",
  "forecast_horizon_months": 12
}

Response 200:
{
  "forecast": [
    {
      "month": "2025-07",
      "predicted_passengers_millions": 12.5,
      "lower_bound": 10.2,
      "upper_bound": 14.8,
      "confidence": 0.95
    }
  ],
  "model_method": "Prophet"
}
```

---

## 5. Accessibilité et Usabilité

### 5.1 Dashboard

- ✅ **Textes alternatifs (alt)** pour graphiques, tableaux exportables JSON
- ✅ **Navigation clavier** : tabulation complète, focus visible
- ✅ **Contraste** : ratio ≥ 4.5:1 (AA)
- ✅ **Labels** : `aria-label="Filtre année"`, `aria-live="polite"` pour mises à jour dynamiques
- ✅ **Structure** : HTML5 sémantique (`<main>`, `<section>`, `<nav>`)
- ✅ **Résultats recommandation** : format texte + JSON + graphique

### 5.2 API REST

- ✅ **Content negotiation** : JSON, CSV, XML selon `Accept` header
- ✅ **Documentation** : Swagger/OpenAPI exhaustive, descriptions champs bilingues
- ✅ **Validations** : Pydantic, messages d'erreur clairs
- ✅ **Rate limiting** : Protection données / fairness

---

## 6. Architecture Technique et Applicative

### 6.1 Proposition d'Architecture Générale

```
                    ┌─────────────────────────┐
                    │  (tableauDeBord + IA UI)│
                    └────────────┬────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │ LB / Reverse Proxy (nginx)  │                           │
    └────────────────────────────┼────────────────────────────┘
                                 │
            ┌────────────────────┴────────────────────┐
            │                                         │
    ┌───────▼──────────────┐              ┌──────────▼────────┐
    │ API Tier (FastAPI)   │              │ ML Inference Tier │
    │ ┌─────────────────┐  │              │ (Served by MLflow)│
    │ │ Auth, CRUD      │  │              │ ┌──────────────┐  │
    │ │ Existing Routes │  │              │ │ Model Server │  │
    │ └─────────────────┘  │              │ │     REST     │  │
    │ ┌─────────────────┐  │              │ └──────────────┘  │
    │ │ IA Routes       │  │              │                   │
    │ │ Orchestration   │  │              │ ┌──────────────┐  │
    │ └─────────────────┘  │              │ │ Model Store  │  │
    └───────┬──────────────┘              │ │ (local)      │  │
            │ SQLAlchemy / psycopg2       │ └──────────────┘  │
            │                             └──────────┬────────┘
            │                                        │
    ┌───────▼────────────────────────────────────────▼────────┐
    │   PostgreSQL 16                                         │
    │ ┌────────────────────────────────────────────────────┐  │
    │ │ Tables: users, trajets, predictions, models, ...   │  │
    │ │ Séries temporelles : trafic_forecast, anomalies    │  │
    │ └────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────┐
    │  DevOps / Monitoring                                   │
    │ ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐   │
    │ │Prometheus│  │ Grafana  │  │MLflow  │  │ Evidently│   │
    │ │(Metrics) │  │(Dashboard)  │(Track) │  │(DataQA)  │   │
    │ └──────────┘  └──────────┘  └────────┘  └──────────┘   │
    └────────────────────────────────────────────────────────┘
```

### 6.2 Stack Technique Complète

| Couche | Technologie | Version | Justification |
|--------|-------------|---------|--------------|
| **Frontend** | Bibliothèque Streamlit | – | Léger, responsive, accessible |
| **API** | FastAPI | 0.100+ | Type hints, async, OpenAPI auto |
| **Serveur ASGI** | Uvicorn | 0.24+ | Perfs, déploiement simple |
| **ORM** | SQLAlchemy | 2.0+ | Typage, migrations (Alembic) |
| **Base de données** | PostgreSQL | 16 | JSONB, séries temporelles (PG-TimescaleDB opt.) |
| **IA/ML** | scikit-learn + statsmodels | 1.3+ | Léger, production-ready |
| **Model management** | MLflow | 2.9+ | Versioning, serving, registry |
| **Monitoring** | Prometheus + Grafana | latest | OSS, extensible |
| **Conteneurs** | Docker + Compose | 24+ | Reproducibilité, scaling |
| **CI/CD** | GitHub Actions | – | Gratuit, intégré repo |

---

## 7. Méthodologie de Développement

### 7.1 Approche Agile (Scrum)

- **Sprints** : 2 semaines
- **Roles** : Product Owner (données mobiles), Scrum Master, Dev Team

### 7.2 Standards de Qualité

#### Code
- **Linting** : `pylint`, `black` (formatage automatique)
- **Type checking** : `mypy` (vérification statique)
- **Tests** : `pytest` (unitaires, intégration, e2e)
- **Couverture** : ≥ 80%

#### IA/ML
- **Data splitting** : stratified 70/15/15 (train/val/test)
- **CV (Cross-validation)** : 5-fold pour modèles prédictifs
- **Métriques** : MAE, RMSE (régression) ; F1, AUC (classification)
- **Model card** : documentation type, limitations, biais connus

#### DevOps
- **Versioning** : GitHub
- **Gestion de projet** : Jira

### 7.3 Plan de Livraison

| Phase | Durée | Livrables |
|-------|-------|-----------|
| **Spec & Design** | 3 semaines | Spécifications IA, architecture, maquettes UI/UX |
| **MVP IA** | 8 semaines | Prédiction CO₂ + Dashboard 1.0 + Tests |
| **Recommandation** | 6 semaines | Endpoint recommandation, UI widgets |
| **Anomalies & Forecast** | 6 semaines | Détection, prévisions, monitoring IA |
| **Accessibilité** | 4 semaines | Audit WCAG, corrections, tests |
| **Production** | 2 semaines | Deployment, scaling, documentation |

---

## 8. Installation et Exécution

### 8.1 Prérequis

- Python 3.13+
- PostgreSQL 16+ et pgAdmin
- Docker & Docker Compose 24+
- Git

### 8.2 Installation Locale

#### Clone du repo
```bash
git clone https://github.com/yourusername/MsprDS.git
cd MsprDS
```

#### Récupération du container Docker stocké dans GiHub
[lien](https://github.com/jeromehtz/MsprDS/pkgs/container/msprds)

Exécuter la commande commande ci-dessous
```bash 
docker pull ghcr.io/jeromehtz/msprds:sha-e850fd4
```

#### Initialisation Base de données
Importer le fichier .backup dans pgAdmin

#### Configuration .env
```bash
cp API/.env.example API/.env
# Éditer API/.env : DATABASE_URL, SECRET_KEY, etc.
```

#### Installation Python & dépendances
```bash
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate (Windows)
pip install -r API/requirements.txt
pip install -r API/requirements-ml.txt  # (Phase 2)
```

### 8.3.1 Lancement API locale
```bash
cd API
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 8.3.2 Docker Compose (Recommandé)

```bash
# Lancement stack complète
docker compose up -d

# Accès services
# API       : http://localhost:8000
# Dashboard : http://localhost
# Prometheus: http://localhost:9090
# Grafana   : http://localhost:3000 (admin/admin)
```

### 8.4 Tests

```bash
# Tests unitaires
pytest API/tests/ -v --cov=API --cov-report=html

# Tests API (intégration)
pytest API/tests/test_api_integration.py -v

# Tests IA/ML (Phase 2)
pytest ml_tests/ -v
```

---

## 9. Documentation et Ressources

- Swagger UI : http://localhost:8000/docs
- Dashboard Streamlit (**revérifier le port**) : http://localhost
- Prometheus : http://localhost:9090
- Grafana : http://localhost:3000 (admin/admin)
- Base de données (**revérifier le port**) : http://localhost
