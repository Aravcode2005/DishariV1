# Stage 1: compile the React/TypeScript frontend using Debian-based Node.
# Avoid the Node Alpine environment implicated in some npm exit-handler crashes.
FROM node:22-bookworm-slim AS build
WORKDIR /app
ENV CI=true \
    NODE_ENV=development \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_FETCH_RETRIES=3 \
    NPM_CONFIG_FETCH_TIMEOUT=120000 \
    NPM_CONFIG_MAXSOCKETS=5
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund --loglevel=warn
COPY . .
# Nginx is the same-origin /api gateway in production.
ENV VITE_PROD_SERVER=1 VITE_API_BASE_PROD_URL=
RUN npm run build

# Stage 2: production static files served by Nginx.
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
