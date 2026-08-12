# --- Stage 1: build the static SPA ---
FROM node:20-alpine AS build

WORKDIR /app

# Install deps first for layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Build
COPY . .
RUN npm run build

# --- Stage 2: serve with nginx ---
FROM nginx:alpine

# SPA fallback + /api proxy config. Placed under /etc/nginx/templates so the
# nginx image's entrypoint runs envsubst on it at container start, injecting
# BACKEND_URL / NGINX_DNS_RESOLVER. Defaults below keep docker-compose /
# standalone `docker run` working; the Helm chart overrides them in K8s.
ENV BACKEND_URL=http://api:8000
ENV NGINX_DNS_RESOLVER=127.0.0.11
COPY default.conf.template /etc/nginx/templates/default.conf.template

# Static assets from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
