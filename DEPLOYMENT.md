# Production Deployment Guide (Milestone 9)

This runbook covers deploying the Enterprise RAG Assistant to a production host using Docker Compose. Follow each step carefully.

## Prerequisites
- Linux server with Docker and Docker Compose installed
- Domain name pointing to server (e.g., `yourdomain.com`)
- TLS certificate (e.g., Let's Encrypt)
- Groq/OpenAI compatible API key with quota
- Sufficient disk for PostgreSQL, Qdrant, and document storage

## 1. Clone and prepare
```bash
git clone https://github.com/lYosril/enterprise-rag-qdrant.git
cd enterprise-rag-qdrant
cp .env.production.example .env
```

Edit `.env` with secure values:
- `POSTGRES_PASSWORD`: strong random password
- `JWT_SECRET_KEY`: long random secret
- `LLM_API_KEY`: your API key
- `VITE_API_BASE_URL`: `https://api.yourdomain.com` (or your API origin)
- `CORS_ORIGINS`: comma-separated allowed origins (frontend domains)
- `LLM_MODEL`, other config as needed

## 2. Configure frontend build-time API URL
The frontend embeds `VITE_API_BASE_URL` at build time. Set it in `.env` (used by `docker-compose.prod.yml`) before building.

## 3. (Optional) Set up Nginx reverse proxy and TLS
For HTTPS in front of the stack:
- Use `frontend/nginx.prod.conf` as a reference
- Mount TLS certs into nginx container
- Ensure ports 80/443 exposed only as intended
- Configure rate limiting zone in http context if needed

## 4. Start services (build + migrate + run)
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Notes:
- Backend runs `alembic -c /app/alembic.ini upgrade head` on startup via entrypoint; migrations are applied before starting the API/worker
- No public PostgreSQL (5432), Redis (6379), Qdrant (6333) ports are exposed
- Document storage is persisted in `document_storage` volume mounted to backend and worker
- PostgreSQL and Qdrant use persistent volumes

## 5. Verify deployment
- Health check: `curl -f https://api.yourdomain.com/health` (or via proxy) → returns `{"status":"ok",...,"database":"connected"}`
- API routes available under `/api/v1/*`
- Frontend loads and can register/login
- Upload a small PDF and run a grounded query
- Check logs: `docker compose -f docker-compose.prod.yml logs -f backend`

## 6. Security checklist
- Secrets only via `.env` (never committed)
- CORS restricted to your frontend origins
- HTTPS enforced (no plain HTTP in production)
- Admin interfaces (Postgres/Qdrant/Redis) not exposed to public internet
- Appropriate `client_max_body_size` and request rate limits
- Back up volumes regularly (Postgres, Qdrant, document_storage)

## 7. Maintenance
- Update: `git pull && docker compose -f docker-compose.prod.yml up -d --build`
- Migrations: Alembic runs automatically on backend startup; review before pulling major schema changes
- Scale: worker can be scaled (`--scale worker=2`) depending on load
- Logs/metrics: exposed at `/metrics` (internal access recommended via proxy)
