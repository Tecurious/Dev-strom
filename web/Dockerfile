# Dev-Strom web image (Vite SPA served by nginx).
# Build context must be the web/ directory.
FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# tests may require extra tooling; build only needs vite
RUN npx vite build

FROM nginx:1.27-alpine
COPY dev-strom-web.nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
