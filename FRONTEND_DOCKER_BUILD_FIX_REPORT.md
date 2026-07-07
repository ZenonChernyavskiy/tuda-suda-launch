# FRONTEND_DOCKER_BUILD_FIX_REPORT

## Что исправлено

Обновлен `frontend/Dockerfile`.

Build stage заменен:

- было: `node:22-alpine`;
- стало: `node:20-bookworm-slim`.

Nginx stage оставлен без изменений:

- `nginx:1.27-alpine`.

## Почему заменен node:22-alpine

На сервере npm падал во время установки зависимостей с ошибкой:

`npm error Exit handler never called!`

Это внутренняя ошибка npm/runtime, которая чаще проявляется на свежих Node/npm сочетаниях и Alpine/musl окружении.

## Почему node:20-bookworm-slim

`node:20-bookworm-slim` использует стабильный Node.js LTS и Debian/glibc окружение. Это более предсказуемая база для npm и сборки Vite-приложения на production server.

## npm install strategy

Так как `frontend/package-lock.json` есть, используется:

```bash
npm ci --include=dev --no-audit --no-fund
```

`npm install` не используется, чтобы не менять lockfile и не получать разные деревья зависимостей между локальной и серверной сборкой.

## Vite build args

`VITE_*` оставлены как Docker build args и передаются только в команду сборки.

Реальные секреты через `ENV` не добавлены.

## Как проверить на сервере

```bash
docker compose build frontend
docker compose up -d --force-recreate frontend
```
