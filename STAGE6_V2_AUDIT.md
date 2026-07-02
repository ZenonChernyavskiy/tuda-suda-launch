# Stage 6 v2 audit

Checked after Codex fix.

## Result
- Frontend no longer imports `@ton/core`, `beginCell`, `window.Buffer`, or `nodePolyfills`.
- `@ton/core`, `buffer`, and `vite-plugin-node-polyfills` are removed from `frontend/package.json`.
- `frontend/src/tonPayload.js` provides browser-safe TON text comment payload encoding.
- Backend Python files compile successfully.
- Provider abstraction exists: `providers/base.py`, `providers/ton_native.py`, `providers/registry.py`.
- `JettonProvider` is still not implemented, which is expected for this stage.

## Cleanup applied
- Removed local debugging overlay from `frontend/index.html`.
- Removed generated/local folders from archive: `node_modules`, `dist`, `.npm-cache`.
- Removed duplicate `frontend/package-lock 2.json`.

## Recommended local launch
From frontend folder:
```bash
rm -rf node_modules package-lock.json
npm config set registry https://registry.npmjs.org/
npm install
npm run dev
```

From backend folder:
```bash
source .venv/bin/activate
uvicorn app.main:app --port 8000
```

Open:
`http://localhost:5173/`
