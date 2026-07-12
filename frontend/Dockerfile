FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_API_URL
ARG VITE_APP_URL
ARG VITE_TONCONNECT_MANIFEST_URL
ARG VITE_ENABLE_MOCK_AUTH=false

COPY package.json package-lock.json ./
RUN npm install -g npm@10.9.2
RUN npm ci --include=dev --no-audit --no-fund

COPY . .
RUN VITE_API_URL=$VITE_API_URL \
    VITE_APP_URL=$VITE_APP_URL \
    VITE_TONCONNECT_MANIFEST_URL=$VITE_TONCONNECT_MANIFEST_URL \
    VITE_ENABLE_MOCK_AUTH=$VITE_ENABLE_MOCK_AUTH \
    npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
