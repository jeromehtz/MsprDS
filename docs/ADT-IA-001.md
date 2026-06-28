# Architecture Technique — Intégration IA MSPR v2.0
## Design et Implémentation

**Document** : ADT-IA-001  
**Version** : 1.0  
**Date** : 23 juin 2025  
**Auteurs** : Équipe Architecture Système  
**Statut** : Approuvé

---

## 1. Vue d'Ensemble Architecturale

### 1.1 Principes Architecturaux

1. **Séparation des préoccupations** : API applicative ≠ Services IA
2. **Scalabilité horizontale** : Services conteneurisés, load-balancés
3. **Résilience** : Circuit breakers, retry logic, fallbacks
4. **Observabilité** : Logging structuré, tracing distribué, metrics
5. **Accessibilité dès la conception** : API multiformat, UI inclusive

### 1.2 Patterns Architecturaux

- **Service-Oriented Architecture (SOA)** : Découplage API / ML services
- **Event-Driven** (optionnel Phase 3) : Webhook recommandations temps-réel
- **CQRS** (Command Query Responsibility Segregation) : Lectures/écritures optimisées
- **Model Registry Pattern** : MLflow comme source de vérité modèles

---

## 2. Architecture Logique par Couches

```
┌─────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Web UI (HTML/JS/CSS) + Swagger/ReDoc            │   │
│  │ Widgets accessibles (ARIA, labels)              │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────┐
│  API GATEWAY LAYER (FastAPI)                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Authentication (OAuth2/JWT)                     │   │
│  │ Request Validation (Pydantic)                   │   │
│  │ Rate Limiting, CORS                             │   │
│  │ Request/Response Transformation                 │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Route Handlers (Legacy + IA)                    │   │
│  │ /auth/*, /trajet/*, /data/*, /forecast/*        │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
            ┌──────────┼──────────┐
            │          │          │
    ┌───────▼────┐ ┌───▼──────┐ ┌▼────────────┐
    │ Business   │ │ ML       │ │  External   │
    │ Logic      │ │ Services │ │  Services   │
    │ (CRUD)     │ │ (IA)     │ │  (GTFS)     │
    └─────┬──────┘ └─────┬────┘ └─────┬──────┘
          │              │             │
└─────────▼──────────────▼─────────────▼────────────────────┐
│  SERVICE LAYER                                            │
│  ┌──────────────────┐   ┌─────────────────────────────┐  │
│  │ Data Repository  │   │ ML Service Layer            │  │
│  │ Pattern (DAO)    │   │ ┌─────────────────────────┐ │  │
│  │                  │   │ │ Model Orchestrator      │ │  │
│  │ ┌──────────────┐ │   │ │ (Load, predict, cache)  │ │  │
│  │ │ UserService  │ │   │ ├─────────────────────────┤ │  │
│  │ │ TrajetService│ │   │ │ CO₂ Predictor Service   │ │  │
│  │ └──────────────┘ │   │ │ Recommender Service     │ │  │
│  │                  │   │ │ Anomaly Detector        │ │  │
│  │                  │   │ │ Forecast Engine         │ │  │
│  │                  │   │ └─────────────────────────┘ │  │
│  └──────────────────┘   └─────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Cross-Cutting Concerns                              │ │
│  │ - Logging (structured, JSON)                        │ │
│  │ - Exception Handling                                │ │
│  │ - Performance Monitoring                            │ │
│  │ - Security Validation                               │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────┬─────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────┐
│  DATA & PERSISTENCE LAYER                                 │
│  ┌───────────────────────────────────────────────────┐   │
│  │ PostgreSQL 16                                     │   │
│  │ ┌─────────────────┐  ┌──────────────────────────┐│   │
│  │ │ Operational DB  │  │ Analytics / Time-Series ││   │
│  │ │ - users         │  │ - trafic_forecast       ││   │
│  │ │ - trajets       │  │ - predictions_log       ││   │
│  │ │ - services      │  │ - anomaly_reports       ││   │
│  │ └─────────────────┘  └──────────────────────────┘│   │
│  │ Extension: TimescaleDB (séries temporelles opt.)  │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│  ┌───────────────────────────────────────────────────┐   │
│  │ Cache Layer (Redis - optionnel)                   │   │
│  │ - Model predictions (TTL 1h)                      │   │
│  │ - Frequently accessed trajectories                │   │
│  │ - Session data                                    │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│  ┌───────────────────────────────────────────────────┐   │
│  │ ML Model Store                                    │   │
│  │ - MLflow Artifact Store (local/S3)                │   │
│  │ - Model binaries (.pkl, .joblib)                 │   │
│  │ - Feature stores (future)                         │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Modules IA — Architecture Détaillée

### 3.1 ML Service Architecture

```
ml_service/
├── __init__.py
├── config.py
│   ├── MLFLOW_TRACKING_URI
│   ├── MODEL_REGISTRY
│   └── Feature configs
├── models/
│   ├── co2_predictor.py
│   │   ├── class CO2PredictorModel
│   │   ├── load_model(version)
│   │   ├── predict(features)
│   │   └── get_confidence_interval()
│   ├── recommender.py
│   │   ├── class RecommenderEngine
│   │   ├── score_routes(routes, user_profile)
│   │   └── explain_recommendation()
│   ├── anomaly_detector.py
│   │   ├── class AnomalyDetector
│   │   ├── fit(data)
│   │   └── detect(records)
│   └── forecast_engine.py
│       ├── class TrafficForecastEngine
│       ├── train(historical_data)
│       └── predict(horizon_months)
│
├── features/
│   ├── feature_extractor.py
│   │   ├── extract_co2_features(trajet)
│   │   ├── extract_route_features(origin, dest, date)
│   │   └── normalize_features(raw_features)
│   └── feature_definitions.py
│       └── FEATURES = { 'distance_km': {...}, ... }
│
├── pipelines/
│   ├── training_pipeline.py
│   │   ├── load_training_data()
│   │   ├── preprocess()
│   │   ├── train_model()
│   │   ├── evaluate()
│   │   └── log_to_mlflow()
│   └── inference_pipeline.py
│       ├── load_model_from_registry()
│       ├── preprocess_input()
│       ├── predict()
│       └── postprocess_output()
│
├── serving/
│   ├── model_server.py
│   │   ├── FastAPI app serving models
│   │   ├── POST /predict/co2
│   │   ├── POST /predict/recommend
│   │   └── Health checks
│   └── model_cache.py
│       ├── LoadingCache (in-memory)
│       ├── get_model(name, version)
│       └── invalidate_cache()
│
├── monitoring/
│   ├── drift_detector.py
│   │   ├── detect_data_drift(new_data, baseline)
│   │   └── detect_prediction_drift(old_preds, new_preds)
│   ├── metrics_logger.py
│   │   ├── log_prediction_accuracy()
│   │   ├── log_latency()
│   │   └── track_feature_distributions()
│   └── alerting.py
│       ├── check_model_health()
│       └── trigger_alert_if_drift()
│
└── tests/
    ├── test_models.py
    ├── test_features.py
    ├── test_pipelines.py
    └── test_inference.py
```

### 3.2 Data Flow — Prédiction CO₂

```
User Request (trajet incomplet)
        │
        ▼
┌──────────────────────────────────────────┐
│ 1. API Route Handler (/predict-co2)      │
│    - Validate input (Pydantic)           │
│    - Check authorization (JWT)           │
│    - Sanitize features                   │
└──────────────────────┬───────────────────┘
                       │
        ┌──────────────▼────────────────┐
        │ 2. Feature Extraction         │
        │    - distance, train_type...  │
        │    - Load baseline stats      │
        │    - Normalize                │
        └──────────────┬────────────────┘
                       │
    ┌──────────────────▼─────────────────────────┐
    │ 3. ML Service Layer                        │
    │    - Get model from MLflow registry        │
    │    - Load to in-memory cache (if miss)     │
    │    - Predict: model.predict(features)     │
    │    - Confidence: ±2σ                      │
    └──────────────────┬──────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────┐
    │ 4. Persistence & Logging                   │
    │    - INSERT predictions table               │
    │    - Log event (request, prediction, time) │
    │    - Track for monitoring                  │
    └──────────────────┬───────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────┐
    │ 5. Response Formatting                     │
    │    - Pydantic model serialization           │
    │    - Multiformat (JSON, CSV header opt.)    │
    │    - Accessibility compliance               │
    └──────────────────┬───────────────────────────┘
                       │
                       ▼
                 User Response (JSON)
```

### 3.3 Model Registry & Serving (MLflow)

```
MLflow Tracking Server
├── Backend Store (PostgreSQL)
│   ├── Runs metadata
│   ├── Experiments
│   ├── Parameters
│   └── Metrics (RMSE, accuracy, etc.)
│
├── Artifact Store (S3 / Local)
│   ├── co2_predictor/
│   │   ├── 1.0.0/
│   │   │   ├── model.pkl (RandomForest)
│   │   │   ├── preprocessor.pkl
│   │   │   ├── metadata.json
│   │   │   └── metrics.json (RMSE=2.34)
│   │   ├── 1.1.0/
│   │   │   └── (gradient boosting variant)
│   │   └── 1.2.0/ (ACTIVE)
│   │
│   ├── recommender/
│   │   ├── 1.0.0/
│   │   │   └── scoring_config.json
│   │   └── 1.0.1/
│   │
│   ├── anomaly_detector/
│   │   ├── 1.0.0/
│   │   │   └── IF_model.pkl
│   │
│   └── traffic_forecast/
│       ├── 1.0.0/
│       │   └── prophet_model.pkl
│
└── Model Registry
    ├── Production Models
    │   ├── co2_predictor → v1.2.0 (routing 95%)
    │   ├── recommender → v1.0.1 (routing 100%)
    │   ├── anomaly_detector → v1.0.0
    │   └── traffic_forecast → v1.0.0
    │
    ├── Staging Models
    │   ├── co2_predictor_rf_v2.0.0 (test 5%)
    │   └── co2_predictor_gb_v2.0.0 (candidate)
    │
    └── Archived Models
        └── Legacy versions (history 12 months)
```

### 3.4 Feature Store & Engineering

```
Features Classification:

1. NUMERIC (ML input)
   - distance_km : float (0–1000+)
   - passenger_density : float (0–1)
   - year : int (2016–2025)
   - co2_base_historical : float (historical mean)

2. CATEGORICAL (encoded)
   - train_type : {TGV, TER, Intercités, ...} → one-hot
   - service_class : {Standard, Premium, Accessible}
   - country_origin : {FR, DE, CH, ...}

3. TEMPORAL
   - day_of_week : 0–6 (seasonality)
   - month : 1–12 (seasonality)
   - is_peak_season : bool

4. DERIVED
   - density_sq : passenger_density²
   - distance_log : log(distance_km)
   - train_co2_efficiency : co2_kg / (distance * passengers)

Feature Store (PostgreSQL)
├── feature_definitions (metadata)
├── feature_values (computed offline)
├── feature_requests (tracking usage)
└── feature_lineage (data provenance)
```

---

## 4. Déploiement et Infrastructure

### 4.1 Topology Déploiement (Dev/Staging/Prod)

```
┌─────────────────────────────────────────────────────┐
│ DEVELOPMENT (Local / Docker Compose)                │
│ ┌──────────────────────────────────────────────┐   │
│ │ - api:latest                                 │   │
│ │ - postgres:16-alpine                         │   │
│ │ - mlflow (tracking local)                    │   │
│ │ - prometheus, grafana                        │   │
│ └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                         │ Push to ghcr.io
                         ▼
┌─────────────────────────────────────────────────────┐
│ STAGING (Kubernetes / Cloud)                        │
│ ┌──────────────────────────────────────────────┐   │
│ │ Deployment: api-staging (2 replicas)         │   │
│ │ Deployment: ml-service-staging (1 replica)   │   │
│ │ Service: LoadBalancer (ingress)              │   │
│ │ PersistentVolumeClaim: PostgreSQL data       │   │
│ │ ConfigMap: Feature flags, thresholds         │   │
│ └──────────────────────────────────────────────┘   │
│ Testing: Integration, Performance, Accessibility   │
└─────────────────────────────────────────────────────┘
                         │ Approve release
                         ▼
┌─────────────────────────────────────────────────────┐
│ PRODUCTION (Kubernetes / Multi-AZ)                  │
│ ┌──────────────────────────────────────────────┐   │
│ │ Deployment: api (5+ replicas, HPA enabled)   │   │
│ │ Deployment: ml-service (3 replicas)          │   │
│ │ Ingress: nginx-controller + TLS              │   │
│ │ Service: ClusterIP (internal routing)        │   │
│ │ StatefulSet: PostgreSQL 16 (primary/replicas)│   │
│ │ S3: Model artifact store (versioned)         │   │
│ │ Redis: Distributed cache (replicated)        │   │
│ │ Logging: ELK Stack / Datadog                 │   │
│ │ Monitoring: Prometheus → Grafana             │   │
│ │ Tracing: Jaeger / OpenTelemetry              │   │
│ └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 4.2 Dockerfile — ML Service

```dockerfile
FROM python:3.13-slim as builder

WORKDIR /build
COPY ml_service/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy ML service code
COPY ml_service/ /app/ml_service/
COPY config/ /app/config/

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

EXPOSE 8001

CMD ["uvicorn", "ml_service.serving.model_server:app", \
     "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
```

### 4.3 Docker Compose — Stack Complète (v2)

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: mspr
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: msprds
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mspr"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://mspr:${DB_PASSWORD}@db:5432/msprds
      MLFLOW_TRACKING_URI: http://mlflow:5000
    ports:
      - "8000:8000"
    volumes:
      - ./API:/app

  ml-service:
    build:
      context: .
      dockerfile: Dockerfile.ml
    depends_on:
      - db
    environment:
      MLFLOW_TRACKING_URI: http://mlflow:5000
      DATABASE_URL: postgresql://mspr:${DB_PASSWORD}@db:5432/msprds
    ports:
      - "8001:8001"
    volumes:
      - ./ml_service:/app/ml_service
      - mlflow_artifacts:/mlflow_artifacts

  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    command: mlflow server --backend-store-uri postgresql://mspr:${DB_PASSWORD}@db/msprds --default-artifact-root /mlflow_artifacts --host 0.0.0.0
    ports:
      - "5000:5000"
    volumes:
      - mlflow_artifacts:/mlflow_artifacts
    depends_on:
      - db

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  prometheus_data:
  grafana_data:
  mlflow_artifacts:
```

---

## 5. Sécurité et Accessibilité

### 5.1 Sécurité Architecture

```
┌────────────────────────────────────────────┐
│ PERIMETER SECURITY                         │
├────────────────────────────────────────────┤
│ - Network: Private VPC, security groups   │
│ - Ingress: HTTPS only (TLS 1.3+)          │
│ - WAF: SQL injection, XSS filtering       │
└────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────┐
│ AUTHENTICATION                             │
├────────────────────────────────────────────┤
│ - OAuth2 + JWT (exp. 60min)                │
│ - Refresh tokens (7 days)                  │
│ - API keys for ML services (scoped)        │
└────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────┐
│ AUTHORIZATION (RBAC)                       │
├────────────────────────────────────────────┤
│ - admin: all operations                    │
│ - analyst: read+predict                    │
│ - read_only: read only                     │
└────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────┐
│ DATA PROTECTION                            │
├────────────────────────────────────────────┤
│ - Transit: HTTPS, TLS certs rotated        │
│ - At rest: PostgreSQL encryption (opt.)    │
│ - Backups: Encrypted, immutable (3+ days)  │
└────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────┐
│ AUDIT & MONITORING                         │
├────────────────────────────────────────────┤
│ - All predictions logged (audit table)     │
│ - Access logs (ELK)                        │
│ - Model changes tracked (MLflow)           │
└────────────────────────────────────────────┘
```

### 5.2 Accessibility-by-Design

| Layer | Standards | Implementation |
|-------|-----------|-----------------|
| **API** | OpenAPI 3.0 | Swagger docs accessible |
| **Response** | JSON + alt formats | CSV, XML negotiation |
| **Frontend** | WCAG 2.1 AA | ARIA, semantic HTML |
| **Data** | Plain language | Non-technical explanations |
| **Keyboards** | Full navigation | Tab order, focus visible |

---

## 6. Monitoring et Observabilité

### 6.1 Metrics Stack

```
Application Metrics (Prometheus)
├── API Metrics
│   ├── api_requests_total (counter)
│   ├── api_request_latency_seconds (histogram)
│   ├── api_errors_total (counter)
│   └── api_auth_failures_total
│
├── ML Metrics
│   ├── model_prediction_latency_seconds
│   ├── model_predictions_total
│   ├── model_cache_hits_total
│   ├── model_cache_misses_total
│   └── model_drift_score
│
├── Database Metrics
│   ├── db_connections_active
│   ├── db_queries_slow (> 1s)
│   └── db_replication_lag
│
└── System Metrics
    ├── container_cpu_usage_percent
    ├── container_memory_usage_bytes
    └── disk_io_operations_total
```

### 6.2 Alerting Rules

```yaml
groups:
  - name: ML_Service_Alerts
    rules:
      - alert: ModelLatencyHigh
        expr: api_request_latency_seconds{endpoint="/predict-co2",quantile="0.95"} > 0.2
        for: 5m
        annotations:
          summary: "CO₂ prediction latency > 200ms"

      - alert: ModelDriftDetected
        expr: model_drift_score > 0.15
        for: 1h
        annotations:
          summary: "Model drift detected, retraining recommended"

      - alert: PredictionAccuracyDegraded
        expr: model_prediction_accuracy < 0.85
        for: 6h
        annotations:
          summary: "Model accuracy < 85%, investigate"
```

---

## 7. Performance & Scalabilité

### 7.1 Optimization Strategies

| Bottleneck | Stratégie |
|------------|-----------|
| Model loading | In-memory cache (first load 50ms, subsequent <1ms) |
| Feature extraction | Vectorized operations (NumPy), parallel processing |
| API latency | Caching predictions (TTL 1h), batch inference |
| DB queries | Indexed columns (distance, country, year), connection pooling |
| Network | Compression (gzip), payload minification |

### 7.2 Capacity Planning

| Scénario | Concurrent Users | QPS | Replica Count |
|----------|------------------|-----|----------------|
| Dev | 10 | 1 | 1 |
| Staging | 100 | 10 | 2 |
| Production | 1000+ | 100+ | 5–10 (HPA) |

---

## 8. Testing Strategy

### 8.1 Test Pyramid

```
        ▲
        │       E2E Tests (10%)
        │    Selenium, Playwright
        │    - Full user journeys
        │    - Accessibility (axe, WAVE)
        │
        │    Integration Tests (30%)
        │    API + DB + ML Service
        │    - Endpoint contracts
        │    - Mock external services
        │
        │    Unit Tests (60%)
        │    - Service methods
        │    - Feature extractors
        │    - Model predictions
        │
        └─────────────────────────
```

### 8.2 Quality Metrics

```
def test_co2_prediction_accuracy():
    """Validate model RMSE < 5 kg/km on test set"""
    model = load_model("co2_predictor", version="1.2.0")
    X_test, y_test = load_test_data()
    predictions = model.predict(X_test)
    rmse = mean_squared_error(y_test, predictions, squared=False)
    assert rmse < 5, f"RMSE {rmse} exceeds threshold"

def test_recommendation_explanation():
    """Verify explanations contain justification"""
    recommendations = recommend(..., user_profile=...)
    for rec in recommendations:
        assert rec.justification != ""
        assert any(metric in rec.justification 
                   for metric in ["CO₂", "coût", "temps"])
```

---

## 9. Évolution Future (Phase 3+)

### 9.1 Roadmap Extension

- **Feature Store managée** : Feast, Tecton
- **Real-time recommendations** : Kafka stream processing
- **Deep Learning** : Embeddings trajets, graph neural networks
- **Federated Learning** : Données multi-sources sans centralisation
- **AutoML** : Automatic model selection, hyperparameter tuning

### 9.2 Technology Debt Management

- Quarterly model retraining (scheduler Airflow/Prefect)
- Dependency updates (Dependabot, security patches)
- Code refactoring (tech debt backlog)
- Documentation maintenance

---

## 10. Approbation Architecture

| Rôle | Nom | Signature | Date |
|------|------|-----------|------|
| Solutions Architect | [À remplir] | ☐ | 2025-06-23 |
| ML Architect | [À remplir] | ☐ | 2025-06-23 |
| DevOps Lead | [À remplir] | ☐ | 2025-06-23 |
| Security Officer | [À remplir] | ☐ | 2025-06-23 |

---

**Document versioned en Git** : `docs/architecture/ADT-IA-001.md`  
**Architecture Decision Records** : `docs/adr/`  
**Diagrams (PlantUML/Mermaid)** : `docs/diagrams/`
