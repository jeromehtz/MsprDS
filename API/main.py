from fastapi import FastAPI
from database import Base, engine
from routers.auth_router import router as auth_router
from routers.trajet_router import router as trajet_router
from routers.prediction_router import router as prediction_router
from routers.stats_router import router as stats_router
from routers.monitoring_router import router as monitoring_router
from routers.businesscentral_router import router as businesscentral_router
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from observability import MetricsMiddleware

Base.metadata.create_all(bind=engine)


app = FastAPI(title="API MSPR", version="1.0.0")

app.add_middleware(MetricsMiddleware)

app.include_router(auth_router)
app.include_router(trajet_router)
app.include_router(prediction_router)
app.include_router(stats_router)
app.include_router(monitoring_router)
app.include_router(businesscentral_router)

@app.get("/")
def root():
    return {"message": "API MSPR RUNNING"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
