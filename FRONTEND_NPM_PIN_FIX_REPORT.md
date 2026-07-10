# FRONTEND_NPM_PIN_FIX_REPORT

## Что исправлено

Обновлен `frontend/Dockerfile`.

В build stage перед установкой зависимостей добавлена фиксация npm:

```dockerfile
RUN npm install -g npm@10.9.2
RUN npm ci --include=dev --no-audit --no-fund
```

## Почему это нужно

На сервере сборка падала с ошибками:

```text
npm error Exit handler never called!
sh: 1: vite: not found
```

Это означало, что `npm ci` завершался некорректно и не создавал полноценный `node_modules`, поэтому во время `npm run build` отсутствовал `vite`.

## Почему npm@10.9.2

Образ остается на стабильном `node:20-bookworm-slim`, но npm больше не берется из образа неявно. Сборка явно использует `npm@10.9.2`, чтобы серверные сборки были воспроизводимее.

## Что не менялось

- `package-lock.json` сохранен.
- Установка остается через `npm ci`.
- Business logic приложения не менялась.
- Nginx runtime stage остается `nginx:1.27-alpine`.
- `VITE_*` остаются build args и не превращаются в runtime secrets.

## Как проверить на сервере

```bash
docker compose build frontend
docker compose up -d --force-recreate frontend
```
