# client_side

The web app (Next.js PWA) of the Behördenbrief Assistant.
All project documents are in [`../docs/`](../docs/); the frontend structure is in
[ARCHITECTURE §6](../docs/ARCHITECTURE.md) and the code rules in [RULES §5](../docs/RULES.md).

## Start locally

```powershell
npm install
npm run dev
```

The app runs at http://localhost:3000.

## Checks

```powershell
npm run lint
npx tsc --noEmit
npm run test -- --coverage
```
