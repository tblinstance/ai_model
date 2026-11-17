# AI-Model Platform

Full-stack multimodal AI platform combining **PyTorch**, **TensorFlow** (optional/graceful fallback when unavailable), and **Keras** in `ai_engine`, served by **FastAPI**, governed by **Django + Djoser** (`billing`, `transactions`, `api`, `Agent`, `quota`), with both a **Vue 3 CDN** built-in control studio and a **React + TypeScript** (`frontend`) SPA.

## Directory Layout

- `src/ai-model/ai_engine/` — Multi-tier (`flash`, `pro`, `advance`) neural engine across `chat`, `images`, `video`, and `code` pipelines powered by PyTorch & Keras (with TensorFlow backend adapter).
- `src/ai-model/api/` — FastAPI service (`:8001`) exposing `/api/v1/chat`, `/api/v1/images/generate`, `/api/v1/video/generate`, `/api/v1/code/generate`, `/api/v1/agent/run`, and `/api/v1/models`.
- `src/ai-model/backend/` — Django + DRF + Djoser JWT control plane (`:8000`) backed by PostgreSQL (`ai_model`) featuring `billing`, `transactions`, `api`, `Agent`, and `quota` apps plus the Vue 3 CDN + Tailwind + Motion + Lucide + Google Fonts portal.
- `src/ai-model/base/postgraphql/` — PostGraphile (PostGraphQL) server (`:5000/graphql`, GraphiQL at `/graphiql`) exposing the PostgreSQL schema over GraphQL; `src/ai-model/base/` also houses local runtime `.run/`, `.logs/`, and `.pgdata/`.
- `src/ai-model/frontend/` — Vite + React + TypeScript + Tailwind CSS + Motion + Lucide + Axios + Google Fonts application (`:5173`).
- `Makefile` — Service lifecycle commands (`pg-start`, `start`, `stop`, `restart`, `reload`, `pkill`, `migrate`, `seed`, `test`).

## Quick Start

```bash
make install
make migrate
make seed
make start
```

- React TSX Studio: `http://127.0.0.1:5173`
- PostGraphQL (PostGraphile) GraphQL & GraphiQL: `http://127.0.0.1:5000/graphql` / `http://127.0.0.1:5000/graphiql`
- Django Control Plane & Vue 3 CDN Studio: `http://127.0.0.1:8000`
- FastAPI Engine Swagger Docs: `http://127.0.0.1:8001/docs`
- Demo Login: `demo` / `DemoPass123!`

