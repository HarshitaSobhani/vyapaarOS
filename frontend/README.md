# VyapaarOS frontend

Next.js (App Router) + TypeScript + Tailwind + shadcn/ui. See the root README for setup and deployment.

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=<backend URL>
npm install && npm run dev
npm test && npm run lint && npm run typecheck && npm run build
```
All HTTP calls go through `lib/api/` and use `NEXT_PUBLIC_API_URL`.
