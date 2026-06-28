# ─── Build stage ───────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

COPY API/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Runtime stage ─────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Copie des dépendances installées
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copie du code source
COPY API/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
