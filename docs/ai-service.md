# AI Service ↔ Chatbot integration

`ai-service/` is the Python (FastAPI) ranking service that re-ranks product candidates
for the Node.js chatbot service. The training and packaging details are in
[`ai-service/README.md`](../ai-service/README.md).

## Contract

| Side | File | Detail |
|------|------|--------|
| Client | `backend/services/chatbot/src/services/ai.client.js` | `POST {AI_SERVICE_URL}/recommend`, `GET /health`; 300 ms SLA, circuit breaker, manual disable toggle |
| Server | `ai-service/src/ai_service/serving/app.py` | `POST /recommend`, `GET /health`, `/health/live`, `/health/ready`, `/metrics` |
| Schema | `ai-service/src/ai_service/serving/schemas.py` | Request `{store_id, user_id?, persona_cluster? (0-7), candidate_product_ids[1..256], context_product_id?}`; response `{rankings[{product_id, ai_score, rank}], inference_ms, model_version, bundle_id}` |
| Wiring | `backend/docker-compose.yml`, `backend/docker-compose.prod.yml` | Service `ai-service:8000`, chatbot gets `AI_SERVICE_URL=http://ai-service:8000` |
| CI | `.github/workflows/ci.yml` (job `ai-service`) | `uv run pytest` with coverage ≥ 85 %, Docker build and read-only smoke run |

If the AI service is unreachable or not ready, the client returns `null`, and the chatbot
falls back to its built-in hybrid ensemble (content, CF, Apriori and personalization).
The chatbot keeps working without the AI service.

## Status (2026-11-15)

- **Code-level integration: done.** The client payload and response validation match the
  Pydantic schemas field by field.
- **End-to-end ranking: not live yet.** Serving needs a verified model bundle at
  `AI_MODEL_BUNDLE_PATH`, otherwise `/recommend` returns 503. The repo does not ship a
  bundle, and none has been exported locally yet, so production runs on the fallback path.
- **Compose blocker:** `backend/docker-compose.yml` mounts `${AI_MODEL_BUNDLE_PATH}:/models/current:ro`
  with no default. If the variable is missing from `backend/.env`, `docker compose config` and
  `docker compose up` fail for **all** services with `invalid spec: :/models/current:ro`. Until a bundle
  exists, set `AI_MODEL_BUNDLE_PATH` to an existing (empty) directory. The AI service then stays
  not-ready and the chatbot uses its fallback.
- **Deployment gap:** `.github/workflows/deploy-backend.yml` does not build or publish
  `ghcr.io/.../ai-service`, although `docker-compose.prod.yml` pulls that image.

### To make it live
1. Train and export a v5 bundle (`ai-service/README.md`, section "Rebuild and training"),
   then mount it at `AI_MODEL_BUNDLE_PATH` on the server.
2. Add `ai-service` to the build matrix in `deploy-backend.yml`, or publish the image manually.
3. Check that `GET /health/ready` returns `ready: true`, and that chatbot logs no longer show
   `using Fallback`.
