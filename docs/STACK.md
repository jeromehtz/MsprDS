# Lancement & architecture de la stack

## Démarrage en une commande

```bat
start.bat
```

Le script ([start.bat](../start.bat)) :
1. vérifie Docker, crée `API/.env` si absent ;
2. construit et démarre tous les conteneurs (`docker compose up -d --build`) ;
3. attend l'API puis MLflow ;
4. **enregistre le modèle XGBoost dans le Model Registry MLflow** (`model/register_mlflow.py`) ;
5. affiche les URLs d'accès.

Arrêt : `docker compose down`.

## Services

| Service | URL | Rôle |
|---------|-----|------|
| **Frontend** (Streamlit) | http://localhost:8501 | Dashboard ObRail |
| **API** (FastAPI) | http://localhost:8000/docs | Backend + prédiction CO₂ + KPI |
| **PostgreSQL** | `localhost:5432` | Base de données |
| **Prometheus** | http://localhost:9090 | Collecte des métriques `/metrics` |
| **Grafana** | http://localhost:3000 (admin/admin) | Tableaux de bord (dashboard **MSPR — API ObRail** auto-provisionné) |
| **MLflow** | http://localhost:5000 | Tracking + Model Registry (`co2-xgboost`) |

## Grafana

- Datasource Prometheus **auto-provisionnée** ([prometheus.yml](../monitoring/grafana/provisioning/datasources/prometheus.yml), `uid: prometheus`).
- Dashboard **auto-provisionné** ([api_dashboard.json](../monitoring/grafana/provisioning/dashboards/api_dashboard.json)) : requêtes/s, taux d'erreur 4xx/5xx, latence p50/p95/p99, trafic par statut et par endpoint.
- Disponible dès le démarrage dans le dossier **MSPR** de Grafana.

## MLflow

- Service `mlflow` (backend SQLite + artefacts sur volume) dans [docker-compose.yml](../docker-compose.yml).
- [model/register_mlflow.py](../model/register_mlflow.py) journalise hyper-paramètres, métriques (MAE/RMSE/R²), métadonnées de features et **enregistre le modèle** sous `co2-xgboost`.
- L'API peut **servir le modèle depuis le registry** : passer `USE_MLFLOW=true` (variable d'env du service `api`). Par défaut (`false`), l'API charge le `.pkl` local — donc fonctionne même si MLflow est vide.

```bat
REM Servir le modèle depuis MLflow plutôt que le .pkl local
set USE_MLFLOW=true && docker compose up -d
```

Le predictor ([API/ml/predictor.py](../API/ml/predictor.py)) tente MLflow si `USE_MLFLOW=true`,
avec **repli automatique** sur le `.pkl` en cas d'indisponibilité.

## Montages importants

Le conteneur `api` monte `./model` et `./data` (en lecture seule) pour accéder au
modèle `.pkl` et aux référentiels (od_flows, facteurs CO₂) requis par la prédiction.
