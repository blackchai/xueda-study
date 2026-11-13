FROM node:22-alpine AS frontend-builder

WORKDIR /workspace/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_BUSINESS_DATA_MODE=api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_BUSINESS_DATA_MODE=${VITE_BUSINESS_DATA_MODE}
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STUDYMATE_FRONTEND_DIST_DIR=/srv/studymate/frontend

WORKDIR /srv/studymate/backend
RUN apt-get update && apt-get install --no-install-recommends -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY backend/pyproject.toml ./
COPY backend/app/ ./app/
RUN pip install --no-cache-dir .
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic/ ./alembic/
COPY --from=frontend-builder /workspace/frontend/dist /srv/studymate/frontend

RUN addgroup --system studymate \
    && adduser --system --ingroup studymate studymate \
    && chown -R studymate:studymate /srv/studymate
USER studymate

EXPOSE 8000
CMD ["python", "-m", "app.startup"]
