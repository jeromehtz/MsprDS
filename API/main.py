from fastapi import FastAPI
from database import Base, engine
from routers.auth_router import router as auth_router
from routers.trajet_router import router as trajet_router
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

Base.metadata.create_all(bind=engine)


REQUEST_COUNT = Counter("api_requests_total", "Total requêtes", ["endpoint", "status"])
REQUEST_LATENCY = Histogram("api_request_latency_seconds", "Latence", ["endpoint"])

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        REQUEST_LATENCY.labels(endpoint=request.url.path).observe(time.time() - start)
        REQUEST_COUNT.labels(endpoint=request.url.path, status=response.status_code).inc()
        return response


app = FastAPI(title="API MSPR", version="1.0.0")

app.add_middleware(MetricsMiddleware)

app.include_router(auth_router)
app.include_router(trajet_router)

@app.get("/")
def root():
    return {"message": "API MSPR RUNNING"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)