FROM python:3.12-slim

WORKDIR /app
# Install dependencies first (layer cached unless requirements change)
COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy API source
COPY api/ /app/

# Copy seed data so the startup script can access it
COPY seed/ /seed/

EXPOSE 8000

# Startup: migrate → seed → serve
# Using shell form so env vars expand correctly
CMD alembic upgrade head \
    && python /seed/seed_loader.py \
    && uvicorn app.main:app --host 0.0.0.0 --port 8000
