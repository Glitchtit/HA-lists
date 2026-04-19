ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest

# ── Stage 1: Build the React frontend ──────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: Runtime image ─────────────────────────────────────────────────
FROM $BUILD_FROM

RUN apk add --no-cache \
    python3 py3-pip \
    nginx gettext jq curl

COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Copy built React app
COPY --from=frontend-builder /app/dist /var/www/html

# Copy nginx config template
COPY nginx.conf.template /etc/nginx/nginx.conf.template

# Copy add-on config
COPY config.json /config.json

# Copy FastAPI app
COPY app/ /app/

# Copy s6-overlay service definitions
COPY rootfs /

WORKDIR /app
