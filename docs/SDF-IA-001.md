# Spécifications Fonctionnelles — Intégration IA
## MSPR v2.0 — Plateforme d'Analyse Ferroviaire Intelligente

**Document** : SDF-IA-001  
**Version** : 1.0  
**Date** : 23 juin 2025  
**Auteurs** : Équipe Architecture / Ingénierie IA  
**Statut** : Approuvé Phase 1.2

---

## 1. Synthèse Exécutive

### 1.1 Objectif Global

Intégrer des capacités de machine learning et d'intelligence artificielle à la plateforme MSPR pour :
- **Améliorer la complétude des données** : prédiction d'émissions CO₂ manquantes
- **Guider les utilisateurs** : recommandations d'itinéraires optimisés multi-critères
- **Assurer la qualité** : détection automatique d'anomalies et incohérences
- **Anticiper la demande** : prévisions de trafic ferroviaire

### 1.2 Périmètre et Exclusions

| Inclus | Exclu |
|--------|-------|
| Prédictions ML classiques (sklearn) | NLP/LLM (hors scope initial) |
| Recommandations déterministes + scoring | Chatbot, assistants conversationnels |
| Monitoring drift modèles | Blockchain / Web3 |
| Serving modèles via REST | Edge computing (IoT) |

### 1.3 Drivers Métier

- **Critère 1** : Accroître exploitabilité données (−50% valeurs manquantes)
- **Critère 2** : Réduire time-to-insight pour planificateurs ferroviaires
- **Critère 3** : Respecter WCAG 2.1 AA (accessibilité)
- **Critère 4** : Maintenir SLA API : latence < 500ms (p95)

---

## 2. Cas d'Usage — Détail Fonctionnel

### 2.1 CU-IA-001 : Prédiction Émission CO₂

#### 2.1.1 Description

L'utilisateur (analyste données, chercheur) soumet un trajet incomplet (sans émission CO₂).  
Le système prédit l'émission probable basée sur l'historique et les caractéristiques du trajet.

#### 2.1.2 Acteurs

- **Primaire** : Analyste MSPR, chercheur mobilité
- **Secondaire** : API Gateway, ML Service, PostgreSQL

#### 2.1.3 Conditions Préalables

- Authentification utilisateur valide (OAuth2/JWT)
- Modèle prédictif entraîné et déployé (MLflow)
- Données historiques ≥ 500 trajets complets dans BD

#### 2.1.4 Flux Principal

1. Utilisateur appelle `POST /api/v1/trajet/predict-co2`
2. API valide payload (distance, train_type, year, service_class, passenger_density)
3. IA Service récupère modèle version active (MLflow registry)
4. Prédiction effectuée : co2_pred = model.predict([input_features])
5. Calcul intervalle confiance : [co2_pred − 2×std, co2_pred + 2×std]
6. Logging événement + stockage résultat dans `predictions` table
7. Retour au client : JSON avec prédiction + confiance + metadata

#### 2.1.5 Flux Alternatifs

- **Alt-A** : Modèle non disponible → Retour erreur 503, fallback valeur historique moyenne
- **Alt-B** : Inputs invalides → 400 Bad Request, message validation Pydantic
- **Alt-C** : Rate limit dépassé → 429 Too Many Requests (protection API)

#### 2.1.6 Résultat Attendu

```json
{
  "id_prediction": "PRED-2025-06-23-001",
  "input": {
    "distance_km": 450.5,
    "train_type": "TGV",
    "year": 2025,
    "service_class": "Intercités",
    "passenger_density": 0.75
  },
  "predicted_co2_kg_per_km": 23.4,
  "confidence_interval": {
    "lower_bound": 21.2,
    "upper_bound": 25.6,
    "confidence_level": 0.95
  },
  "model_info": {
    "name": "co2_predictor_rf_v1.2",
    "version": "1.2.0",
    "trained_date": "2025-06-15",
    "metric_rmse": 2.34
  },
  "timestamp": "2025-06-23T14:32:00Z"
}
```

#### 2.1.7 Règles Métier

- Prédiction valide pour trajets ±20% distance historique
- Pas de prédiction si `year > 2026` (hors domaine d'entraînement)
- Intervalle confiance toujours symétrique autour valeur centrale

---

### 2.2 CU-IA-002 : Recommandation Itinéraire Optimal

#### 2.2.1 Description

Utilisateur demande : « Quel meilleur trajet de Paris à Berlin le 15 juillet, en minimisant CO₂ et coûts ? »  
Système retourne 3 itinéraires classés avec justification.

#### 2.2.2 Acteurs

- **Primaire** : Voyageur, planificateur transport, développeur client
- **Secondaire** : API, Database, Recommender Engine

#### 2.2.3 Conditions Préalables

- Données O/D couvrant trajet demandé
- Profil utilisateur renseigné (poids critères, besoins accessibilité)
- Services disponibles à date demandée (calendrier GTFS)

#### 2.2.4 Flux Principal

1. Appel `POST /api/v1/trajet/recommend`
2. Validation origin, destination, date, user_profile
3. Recherche trajets directs et correspondances (algorithme Dijkstra + variants)
4. Scoring multi-critères pour chaque itinéraire :
   - score = (w_cost × norm(cost) + w_time × norm(time) + w_co2 × norm(co2) + w_comfort × norm(comfort)) / Σw
5. Filtrage trajets accessibles si besoins spécifiés
6. Tri décroissant score, retour top 3 + explications
7. Logging recommandation + réaction utilisateur (feedback loop futur)

#### 2.2.5 Matrices de Pondération (Exemples)

**Profil Écolo :**  
{ cost: 0.1, time: 0.2, co2: 0.6, comfort: 0.1 }

**Profil Confort :**  
{ cost: 0.15, time: 0.15, co2: 0.2, comfort: 0.5 }

**Profil Budget :**  
{ cost: 0.5, time: 0.2, co2: 0.2, comfort: 0.1 }

#### 2.2.6 Résultat Attendu

```json
{
  "request_id": "REC-2025-06-23-042",
  "origin": "FR_PARIS",
  "destination": "DE_BERLIN",
  "date": "2025-07-15",
  "recommendations": [
    {
      "rank": 1,
      "route_id": "ROUTE-PAR-BER-001",
      "route_description": "PARIS→LIÈGE→COLOGNE→BERLIN",
      "segments": [
        {
          "from": "PARIS",
          "to": "LIÈGE",
          "duration_minutes": 180,
          "carrier": "THALYS"
        },
        {
          "from": "LIÈGE",
          "to": "COLOGNE",
          "duration_minutes": 120,
          "carrier": "DEUTSCHE_BAHN"
        }
      ],
      "metrics": {
        "cost_eur": 89,
        "duration_hours": 18.0,
        "co2_kg": 42.0,
        "comfort_score": 0.85,
        "accessibility_score": 1.0
      },
      "composite_score": 0.87,
      "score_breakdown": {
        "cost_component": 0.15,
        "time_component": 0.22,
        "co2_component": 0.38,
        "comfort_component": 0.12
      },
      "justification": "Meilleur équilibre coût-CO₂-accessibilité. CO₂ réduit de 32% vs option avion.",
      "accessibility_notes": {
        "wheelchair_accessible": true,
        "blind_friendly": false,
        "recommendations": ["Prévoir assistance gare LIÈGE"]
      }
    },
    {
      "rank": 2,
      "route_id": "ROUTE-PAR-BER-002",
      "route_description": "PARIS→Brussels→AMSTERDAM→BERLIN",
      "composite_score": 0.76,
      "metrics": {
        "cost_eur": 76,
        "duration_hours": 20.5,
        "co2_kg": 38.0
      },
      "justification": "Option moins chère, mais plus long."
    }
  ],
  "timestamp": "2025-06-23T15:00:00Z"
}
```

---

### 2.3 CU-IA-003 : Détection Anomalies Données

#### 2.3.1 Description

Administrateur BD soumet dataset pour vérifier cohérence.  
Système identifie trajets aberrants (émission extrême, passagers incohérents, etc.).

#### 2.3.2 Acteurs

- **Primaire** : Data steward, responsable qualité données
- **Secondaire** : API, Anomaly Detector (Isolation Forest), BD

#### 2.3.3 Conditions Préalables

- Dataset nettoyé (pas de NaN non masqués)
- ≥ 100 trajets dans dataset analysé

#### 2.3.4 Flux Principal

1. Appel `POST /api/v1/data/check-anomalies` avec dataset_id
2. Récupération dataset depuis BD
3. Normalisation features (StandardScaler)
4. Exécution Isolation Forest (n_estimators=100, contamination=0.05)
5. Calcul anomaly score pour chaque enregistrement
6. Flagging records avec score > seuil (p.ex., 0.85)
7. Retour liste anomalies avec cause probable
8. Sauvegarde rapport contrôle qualité dans audit table

#### 2.3.5 Résultat Attendu

```json
{
  "analysis_id": "QA-2025-06-23-156",
  "dataset": "od_flows_2024",
  "total_records": 3070,
  "anomalies_detected": 42,
  "anomaly_rate": 0.0137,
  "method": "Isolation Forest (v1.3)",
  "high_risk_records": [
    {
      "id_trajet": "TRAJET-12345",
      "anomaly_score": 0.92,
      "features": {
        "distance_km": 450,
        "co2_kg_per_km": 0.5,
        "passenger_count": 12000
      },
      "reason": "Émission CO₂ extrêmement faible (vs historique +2σ)",
      "recommended_action": "review_before_publish",
      "confidence": 0.95
    },
    {
      "id_trajet": "TRAJET-12346",
      "anomaly_score": 0.87,
      "reason": "Passagers disproportionnés pour service régional",
      "recommended_action": "data_entry_error"
    }
  ],
  "timestamp": "2025-06-23T16:00:00Z"
}
```

---

### 2.4 CU-IA-004 : Prévision Trafic Annuel

#### 2.4.1 Description

Planificateur demande : « Quel trafic TER France en 2026 ? »  
Système retourne prévision ponctuelle + intervalle de confiance basée sur 9 ans historiques.

#### 2.4.2 Acteurs

- **Primaire** : Planificateur transport, analyste stratégie
- **Secondaire** : API, Forecast Engine (Prophet/ARIMA)

#### 2.4.3 Conditions Préalables

- Historique trafic ≥ 9 années (données 2016–2024)
- Saisonnalité identifiée (pics été/ski, creux été)
- Pas d'événement majeur inconnu (grève, pandémie)

#### 2.4.4 Flux Principal

1. Appel `POST /api/v1/forecast/traffic`
2. Sélection données historiques (country, service_type, time window)
3. Désaisonnalisation (seasonal decomposition)
4. Entraînement modèle Prophet (growth='linear', seasonality_mode='additive')
5. Prévision pour horizon_months (p.ex., 12 mois)
6. Calcul intervalle confiance (80%, 95%)
7. Retour forecast mensuel avec tendance, saisonnalité
8. Logging prévision + réalisation ultérieure (feedback accuracy)

#### 2.4.5 Résultat Attendu

```json
{
  "forecast_id": "FCT-2025-06-23-089",
  "country": "FR",
  "service_type": "TER",
  "forecast_start": "2025-07-01",
  "forecast_horizon": "12 months",
  "model": {
    "name": "Prophet",
    "version": "1.1",
    "training_period": "2016-2024",
    "mape": 0.083
  },
  "forecast_monthly": [
    {
      "date": "2025-07-01",
      "predicted_passengers_millions": 12.5,
      "lower_bound_80": 11.2,
      "upper_bound_80": 13.8,
      "lower_bound_95": 10.5,
      "upper_bound_95": 14.5,
      "season_component": 0.8,
      "trend_component": 11.7
    },
    {
      "date": "2025-08-01",
      "predicted_passengers_millions": 13.2,
      "lower_bound_80": 11.9,
      "upper_bound_80": 14.5
    }
  ],
  "aggregate_2025_h2": {
    "total_passengers_millions": 75.3,
    "confidence_interval_95": [71.2, 79.4]
  },
  "timestamp": "2025-06-23T17:00:00Z"
}
```

---

## 3. Exigences Non-Fonctionnelles

### 3.1 Performance

| Endpoint | Latence P95 | Throughput |
|----------|------------|-----------|
| `/predict-co2` | < 200ms | ≥ 100 req/s |
| `/recommend` | < 500ms | ≥ 50 req/s |
| `/check-anomalies` | < 5s (batch) | ≥ 5 analyses/h |
| `/forecast/traffic` | < 2s | ≥ 20 req/h |

### 3.2 Fiabilité

- **Uptime API** : ≥ 99.5% (SLA)
- **Model Accuracy**
  - CO₂ pred : RMSE < 5 kg/km
  - Recommandations : user satisfaction ≥ 4/5
  - Anomaly detection : precision ≥ 0.85
  - Traffic forecast : MAPE < 10%

### 3.3 Scalabilité

- Supporter 1M+ trajets en BD
- Concurrent users : ≥ 1000
- Modèles : inference parallelisé (batch prediction possible)

### 3.4 Sécurité

- Authentification : OAuth2 + JWT (exp. 60 min)
- Autorisation : RBAC (admin, analyst, read-only)
- Chiffrement : données en transit (HTTPS), en repos (optionnel AES-256 collocations sensibles)
- Audit : logging toutes prédictions, recommandations

### 3.5 Accessibilité (WCAG 2.1 AA)

- ✅ Textes alternatifs pour graphiques recommandations
- ✅ Navigation clavier complète
- ✅ Contraste texte ≥ 4.5:1
- ✅ ARIA labels, live regions pour mises à jour dynamiques
- ✅ Formats texte + JSON pour résultats

### 3.6 Maintenabilité

- Code documenté (docstrings Python)
- Tests unitaires : ≥ 80% coverage
- Versioning modèles : SemVer
- Rollback prédictions : historique 12 mois

---

## 4. Exigences Techniques

### 4.1 Stack Développement (Phase 2)

```requirements.txt
# Core API
fastapi==0.100.1
uvicorn==0.24.0
sqlalchemy==2.0.22
psycopg2-binary==2.9.9
pydantic==2.4.2

# IA/ML
scikit-learn==1.3.2
numpy==1.24.3
pandas==2.1.1
statsmodels==0.14.0
prophet==1.1.5
scipy==1.11.3

# Model Management
mlflow==2.9.1
joblib==1.3.2

# Monitoring IA
evidently==0.4.10

# Testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1

# Development
black==23.11.0
pylint==3.0.2
mypy==1.7.0
```

### 4.2 Environnement Runtime

- Python 3.13+
- PostgreSQL 16+ (avec extension TimescaleDB optionnelle)
- Redis 7+ (caching optionnel)
- MLflow tracking server
- Docker 24+

### 4.3 Déploiement

- Conteneurs : `api:latest`, `ml-service:latest`
- Orchestration : Docker Compose (dev/staging), Kubernetes (production future)
- CI/CD : GitHub Actions (build, test, deploy)

---

## 5. Critères d'Acceptation

### 5.1 Critères CO₂ Prediction

- [ ] Endpoint `/predict-co2` répond < 200ms
- [ ] RMSE validation < 5 kg/km
- [ ] Intervalle confiance couvre 95% cas réels
- [ ] Interface accessible (WCAG AA)
- [ ] Tests unitaires ≥ 85% couverture

### 5.2 Critères Recommandation

- [ ] Endpoint `/recommend` répond < 500ms pour 3 trajets
- [ ] Top 1 recommandation acceptée par ≥ 80% utilisateurs (feedback)
- [ ] Explications lisibles et claires
- [ ] Accessibilité clavier + lecteur écran
- [ ] Documentation API exhaustive (Swagger)

### 5.3 Critères Anomaly Detection

- [ ] Détecte ≥ 90% anomalies connues dans dataset test
- [ ] Faux positifs < 15%
- [ ] Rapport qualité exploitable par data stewards

### 5.4 Critères Forecast

- [ ] MAPE < 10% sur données validation 2024
- [ ] Intervalles confiance statistiquement valides
- [ ] Intégration dans dashboard de reporting

---

## 6. Timeline et Jalons

| Semaine | Jalon | Livrables |
|---------|-------|-----------|
| 1–3 | Spécs finales + Design IA | SDF-IA-001, Architecture diagram |
| 4–6 | Exploration données | Notebooks EDA, feature engineering |
| 7–10 | Modèle CO₂ | Trained model, validation metrics |
| 11–13 | API CO₂ + tests | Endpoint REST, pytest suite |
| 14–16 | Recommender | Scoring logic, tests |
| 17–19 | Anomaly detector | IF model, dashboard integration |
| 20–22 | Forecast trafic | Prophet model, predictions |
| 23–25 | Accessibilité + docs | WCAG audit, API docs |
| 26–27 | Production prep | Deployment config, monitoring setup |

---

## 7. Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|-----------|
| Données historiques insuffisantes | Moyenne | Élevé | Collecte données externes, augmentation synthétique |
| Modèles peu expliquables | Moyenne | Moyen | LIME/SHAP, documentation détaillée |
| Dérive de modèles en production | Élevée | Moyen | Monitoring drift, retraining mensuel |
| Performance API dégradée | Basse | Élevé | Caching, batch processing |
| Accessibilité incomplète | Moyenne | Moyen | Tests WCAG, audit externe |

---

## 8. Approbation et Traçabilité

| Rôle | Nom | Signature | Date |
|------|------|-----------|------|
| Product Owner | [À remplir] | ☐ | 2025-06-23 |
| Tech Lead | [À remplir] | ☐ | 2025-06-23 |
| Responsable IA | [À remplir] | ☐ | 2025-06-23 |
| CTO | [À remplir] | ☐ | 2025-06-23 |

---

**Document versioned en Git** : `docs/specs/SDF-IA-001.md`  
**Numéro Jira épopée** : [MSPR-IA-001]  
**Lien Confluence** : [MSPR Specs IA]
