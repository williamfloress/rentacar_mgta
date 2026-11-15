# Imagen del panel web en dos etapas:
#   1) "build": Node compila la app (TypeScript + Vite) a archivos estáticos.
#   2) "serve": nginx sirve esos archivos. La imagen final no lleva Node ni
#      node_modules (unos 75 MB frente a más de 1 GB de la etapa de build).
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# La URL de la API se "hornea" en el JavaScript al compilar (así funciona Vite).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine AS serve
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
