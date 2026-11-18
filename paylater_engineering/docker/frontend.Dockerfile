# ── Stage 1: Build ────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Note: --frozen-lockfile is a Yarn flag; npm ci is already exact.
ENV NODE_ENV=development

# Install ALL dependencies (incl. devDependencies) using the lockfile
COPY app/frontend/package*.json ./
RUN npm ci

# Copy source code
COPY app/frontend/ .

# nginx will reverse-proxy
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Compile TypeScript + bundle with Vite
RUN npm run build

# ── Stage 2: Serve ────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Remove the default nginx welcome page
RUN rm -rf /usr/share/nginx/html/*

# Copy Vite production build
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config: SPA routing + API reverse-proxy to fastapi
COPY docker/nginx.frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost/health.txt || exit 1

CMD ["nginx", "-g", "daemon off;"]
