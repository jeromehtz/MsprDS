"""
Observabilité : métriques Prometheus partagées et middleware de mesure.

Centralisé ici pour être réutilisable à la fois par l'application (main.py) et par
le routeur de monitoring (santé / incidents), sans import circulaire.
"""

import time

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_COUNT = Counter("api_requests_total", "Total requêtes", ["endpoint", "status"])
REQUEST_LATENCY = Histogram("api_request_latency_seconds", "Latence", ["endpoint"])


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        REQUEST_LATENCY.labels(endpoint=request.url.path).observe(time.time() - start)
        REQUEST_COUNT.labels(endpoint=request.url.path, status=response.status_code).inc()
        return response


def request_summary() -> dict:
    """
    Agrège les compteurs de requêtes en direct (par statut HTTP) et détecte les
    « incidents » (réponses 4xx / 5xx) à partir du compteur Prometheus en mémoire.
    """
    by_status = {}
    by_endpoint_errors = {}
    total = 0
    errors = 0

    for metric in REQUEST_COUNT.collect():
        for sample in metric.samples:
            if not sample.name.endswith("_total"):
                continue
            value = int(sample.value)
            status = sample.labels.get("status", "?")
            endpoint = sample.labels.get("endpoint", "?")
            total += value
            by_status[status] = by_status.get(status, 0) + value
            if status and status[0] in ("4", "5"):
                errors += value
                key = f"{endpoint} [{status}]"
                by_endpoint_errors[key] = by_endpoint_errors.get(key, 0) + value

    incidents = [
        {"endpoint_status": k, "count": v}
        for k, v in sorted(by_endpoint_errors.items(), key=lambda x: x[1], reverse=True)
    ]
    error_rate = round(errors / total * 100, 2) if total else 0.0

    return {
        "total_requests": total,
        "error_count": errors,
        "error_rate_pct": error_rate,
        "by_status": dict(sorted(by_status.items())),
        "incidents": incidents,
    }
