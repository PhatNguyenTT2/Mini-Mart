# AI Service ↔ Chatbot integration

`ai-service/` holds the recommendation core `hybrid_recsys`: a decoupled Hybrid of a two-tower
Deep branch and association rules (see [`ai-service/README.md`](../ai-service/README.md)).

## Status (2026-11-15)

| Item | State |
|------|-------|
| Model and evaluation core | ✅ in `ai-service/`, 60 unit tests and lint in CI (job `ai-service`) |
| HTTP serving (`/recommend`, `/health`) | ❌ not built yet |
| Model bundle (trained on Mini-Mart data, export + verify) | ❌ not built yet |
| Docker image / deploy | ❌ `ai-service` is opt-in (`profiles: ["ai"]`) in both compose files and absent from `deploy-backend.yml` |
| Chatbot | ✅ runs on its built-in fallback (content, CF, Apriori, personalization) |

The chatbot no longer `depends_on` the AI service. `docker compose up` starts every other service
without `AI_MODEL_BUNDLE_PATH`.

## Contract to keep (already implemented on the chatbot side)

`backend/services/chatbot/src/services/ai.client.js` calls `POST {AI_SERVICE_URL}/recommend` and
`GET /health`. It applies a 300 ms SLA and a circuit breaker, and treats `null` as "use fallback".

- **Request:** `{store_id, user_id?, persona_cluster? (0-7), candidate_product_ids[1..256], context_product_id?}`
- **Response:** `{rankings[{product_id, ai_score, rank}], inference_ms, model_version, bundle_id}`. It must contain every candidate exactly once.

## Roadmap: making the AI service live
1. **Serving.** Add `serving/` (FastAPI) with `GET /health/live`, `/health/ready`, `/health`, `/metrics`
   and `POST /recommend`, using exactly the contract above. `ai.client.js` needs no change.
2. **Input mapping.**
   - `user_id` → the user tower; purchase history comes from the order DB.
   - `context_product_id` → the rule antecedent (`data/pair_rules.py`).
   - `persona_cluster` → cold-start for users with no history.
   - Score only `candidate_product_ids`.
3. **Bundle.**
   - Train the Hybrid model on Mini-Mart data. The data preparation and training pipeline lives on the `paper` branch.
   - Export the tower weights (or ONNX, so the serving image stays torch-free) and the rule table, with a SHA-256 `manifest.json` verified at load time.
4. **Deploy.**
   - CPU read-only Dockerfile.
   - Remove the `ai` profile from compose.
   - Add `ai-service` to `deploy-backend.yml`.
   - CI smoke test: `/health/ready` returns 503 without a bundle and 200 with one.
5. **Done when** staging chatbot logs no longer show `using Fallback`.
