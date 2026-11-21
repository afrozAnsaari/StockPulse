# StockPulse Architecture Decision Records (ADRs)

---

## ADR 1: Commerce Strategy Layer & Domain Placement

**Status**: Accepted  
**Date**: August 24, 2026  
**Relevant Code**: [`backend/app/services/strategy/base.py`](backend/app/services/strategy/base.py), [`backend/app/services/strategy/rule_strategy.py`](backend/app/services/strategy/rule_strategy.py), [`backend/app/services/strategy/ai_strategy.py`](backend/app/services/strategy/ai_strategy.py)

### Context
Merchandising decision logic (pricing optimization and restocking calculations) is required in both synchronous on-demand HTTP endpoints (e.g. `POST /products/{id}/suggest-pricing`) and asynchronous background event triggers (e.g. order sales and stock updates). Duplicating pricing or reorder formulas inside API routers or background handlers leads to divergence, hard-to-test code, and tight coupling with specific LLM providers.

### Options
1. **Router-embedded logic**: Embed price calculations and LLM prompts directly inside FastAPI route handlers.
2. **Fat SQLModel entities**: Place pricing and reorder logic inside SQLModel product methods.
3. **Pluggable Strategy Pattern (Chosen)**: Encapsulate all pricing and replenishment logic behind unified abstract interfaces (`PricingStrategy`, `ReorderStrategy`, and `CommerceAdvisor`).

### Decision
We adopted the Strategy Pattern. All commerce intelligence is decoupled into abstract interfaces in `services/strategy/base.py`. Both deterministic rule-based calculation (`RuleCommerceAdvisor`) and AI-powered intelligence (`AICommerceAdvisor`) adhere to the exact same contract. Routers and background workers only depend on the interface, never on concrete LLM details.

### Tradeoffs
- **Pros**: Clean testability with mocks, zero duplication between HTTP and background tasks, seamless runtime strategy switching, and clear extension seams for future strategies (e.g., `CompetitorAwareStrategy`).
- **Cons**: Minor initial abstraction overhead with interface definitions.

---

## ADR 2: Specialized Trigger Prompts with Unified Output Contracts

**Status**: Accepted  
**Date**: August 24, 2026  
**Relevant Code**: [`backend/app/services/ai/prompts.py`](backend/app/services/ai/prompts.py), [`backend/app/services/ai/parser.py`](backend/app/services/ai/parser.py)

### Context
Inventory-low conditions and demand-spike conditions require fundamentally different domain reasoning. A generic LLM prompt that merely changes a trigger tag fails to capture nuanced economic trade-offs (such as margin preservation and stock rationing during scarcity vs. surge capture without customer friction during demand spikes). However, the downstream application and frontend merchandising console require predictable, strongly typed JSON payloads.

### Options
1. **Single Generic Prompt**: One prompt for all recommendation requests.
2. **Split Trigger-Specific Prompts with Unified Schema Output (Chosen)**: Distinct prompt builders for `INVENTORY_LOW` and `DEMAND_SPIKE` that both produce strictly validated `PricingRecommendation` and `ReorderRecommendation` models.

### Decision
We implemented specialized prompt builders:
- `build_inventory_low_pricing_prompt` & `build_inventory_low_reorder_prompt`: Instruct the model to reason about inventory scarcity, remaining stock runway, price protection vs holding, and replenishment urgency.
- `build_demand_spike_pricing_prompt` & `build_demand_spike_reorder_prompt`: Instruct the model to reason about surge velocity multiples, monetizing consumer surplus without price gouging, and accelerated inventory drain.
- Category benchmark averages (e.g. category average 24h demand velocity) are calculated by the backend and injected directly into prompts rather than asking the LLM to invent them.
- All outputs are parsed, sanitized, and validated using Pydantic models with strict guardrails (`0.3x <= price <= 3.0x`, quantity >= 1).

### Tradeoffs
- **Pros**: High-quality, context-aware reasoning tailored to specific business conditions; predictable validation and error handling.
- **Cons**: Requires maintaining two distinct prompt templates.

---

## ADR 3: Runtime Strategy Switching Without Restarts

**Status**: Accepted  
**Date**: August 24, 2026  
**Relevant Code**: [`backend/app/services/strategy/manager.py`](backend/app/services/strategy/manager.py), [`backend/app/api/routes.py`](backend/app/api/routes.py)

### Context
During operations or live demonstrations, merchandisers need the ability to toggle between AI-assisted pricing (via an OpenAI-compatible LLM API) and deterministic rule-based algorithms (e.g., in offline environments, during rate-limit events, or for regulatory compliance) without downtime or restarting the application.

### Options
1. **Environment-variable restart only**: Changing strategy requires editing `.env` and restarting the server.
2. **Dynamic Strategy Manager (Chosen)**: A centralized `StrategyManager` singleton that resolves the active advisor at runtime and exposes `GET /config/strategy` and `PATCH /config/strategy`.

### Decision
We implemented `StrategyManager`. The active strategy defaults to `settings.ACTIVE_STRATEGY` but can be switched on-the-fly via the API or frontend UI header toggle. Both asynchronous event workers and synchronous endpoints retrieve the advisor via `strategy_manager.get_advisor()`.

### Tradeoffs
- **Pros**: Zero-downtime reconfiguration; instant toggling during live demos; extensible registry for future algorithms.
- **Cons**: State is held in the running process memory (synchronized across workers if deployed multi-process).

---

## ADR 4: Autonomous Resilience & Automatic Rule-Based Fallback

**Status**: Accepted  
**Date**: August 24, 2026  
**Relevant Code**: [`backend/app/services/strategy/ai_strategy.py`](backend/app/services/strategy/ai_strategy.py), [`backend/app/services/ai/client.py`](backend/app/services/ai/client.py)

### Context
External LLM gateways are subject to network timeouts, API quota exhaustion, connection drops, malformed JSON formatting, or hallucinations that generate absurd prices (e.g. $99,999 on a $25 t-shirt). An agentic commerce engine must NEVER drop background recommendation events or leave products in an unhandled state when AI calls fail.

### Options
1. **Fail-loud with HTTP error**: Raise 500 error and drop the recommendation.
2. **Automatic Rule Fallback with Guardrails (Chosen)**: Catch any LLM failure (timeout, network error, schema violation, out-of-bounds price) and automatically delegate to `RulePricingStrategy` / `RuleReorderStrategy`.

### Decision
`AIPricingStrategy` and `AIReorderStrategy` catch `LLMClientError`, `AIValidationError`, and `Exception`. Upon any failure, they log a warning, execute the deterministic rule strategy, append an `[AI Fallback Applied]` audit note to the reasoning, and persist a valid suggestion. Absurd prices outside `[PRICE_MIN_MULTIPLIER * current_price, PRICE_MAX_MULTIPLIER * current_price]` immediately trigger the fallback path.

### Tradeoffs
- **Pros**: 100% availability guarantee; suggestions are always produced and never dropped; protects business from extreme pricing errors.
- **Cons**: Fallback suggestions use deterministic heuristics instead of deep semantic reasoning.

---

## ADR 5: Asynchronous Agentic Loop & Event Decoupling

**Status**: Accepted  
**Date**: August 24, 2026  
**Relevant Code**: [`backend/app/services/recommendation_engine.py`](backend/app/services/recommendation_engine.py), [`backend/app/api/routes.py`](backend/app/api/routes.py)

### Context
Operations such as `POST /products/{id}/orders` (sale simulation) and `PATCH /products/{id}/stock` (inventory adjustment) must execute with sub-50ms latency. Because LLM generation can take 2 to 10 seconds, recommendation reasoning must not block the transactional response.

### Options
1. **Synchronous in-request LLM calls**: Block the order HTTP response until LLM completes.
2. **Heavy distributed queue (Celery/Kafka/RabbitMQ)**: Overkill for a lightweight service.
3. **FastAPI BackgroundTasks Event Loop (Chosen)**: Non-blocking asynchronous task execution using native FastAPI background tasks and async worker functions.

### Decision
`create_order_transaction` and `update_product_stock` execute the inventory transaction atomically and return immediately. If an `INVENTORY_LOW` or `DEMAND_SPIKE` threshold is crossed, a background task `process_async_recommendations` is dispatched. The frontend Merchandising Console polls `GET /suggestions/pending` every 2.5 seconds to seamlessly detect and render newly generated recommendations.

### Tradeoffs
- **Pros**: Blazing fast order response times; resilient architecture without external broker dependencies; simple local and demo execution.
- **Cons**: Background tasks run within the FastAPI event loop; for massive enterprise scale, a Redis/Celery queue can be plugged in without changing domain logic.

---

## ADR 6: Idempotency & Recommendation Deduplication Guard

**Status**: Accepted  
**Date**: August 24, 2026  
**Relevant Code**: [`backend/app/services/recommendation_engine.py`](backend/app/services/recommendation_engine.py)

### Context
If multiple simulated orders occur in rapid succession while a product is below threshold, multiple identical `INVENTORY_LOW` recommendation tasks would be dispatched. Creating duplicate pending suggestions for the same product, trigger reason, and suggestion type confuses merchandisers and creates review queue clutter.

### Options
1. **Allow duplicate suggestions**: Clutters database and review queue.
2. **Idempotency Guard on Pending Records (Chosen)**: Verify whether a `PENDING` suggestion already exists for `(product_id, trigger_reason, type)` before generating and persisting a new record.

### Decision
Before generating a pricing or reorder suggestion, `recommendation_engine.py` checks `has_pending_pricing_suggestion` and `has_pending_reorder_suggestion`. If an active `PENDING` recommendation exists, generation is skipped idempotently. Once a merchandiser accepts or rejects the pending recommendation, subsequent trigger events can generate new recommendations.

### Tradeoffs
- **Pros**: Clean review queue; eliminates redundant LLM calls and duplicate proposals.
- **Cons**: Minor database lookup overhead before recommendation generation.

---

## ADR 7: Human Checkpoint & State Machine Transitions

**Status**: Accepted  
**Date**: August 24, 2026  
**Relevant Code**: [`backend/app/services/state_service.py`](backend/app/services/state_service.py), [`backend/app/core/crud.py`](backend/app/core/crud.py)

### Context
In automated commerce, autonomous price updates can lead to unintended margin loss, brand damage, or race conditions. The system requires an explicit human-in-the-loop checkpoint (`OBSERVE → REASON → PROPOSE → HUMAN CHECKPOINT → ACT`).

### Options
1. **Autonomous auto-publishing**: AI modifies price immediately.
2. **Explicit Human Review Checkpoint with State Machine (Chosen)**: Suggestions remain in `PENDING` status. Only explicit merchandiser approval via `PATCH /pricing-suggestions/{id}` or `PATCH /reorder-suggestions/{id}` mutates product state.

### Decision
We implemented formal lifecycle states:
- `OUT_OF_STOCK`: Stock == 0.
- `PRICE_REVIEW_PENDING`: Stock > 0 and one or more `PENDING` suggestions exist.
- `ACTIVE`: Stock > 0 and all suggestions resolved (accepted/rejected).
- Accepting a pricing suggestion updates `Product.current_price` atomically and transitions state.
- Accepting a reorder suggestion atomically increments `Product.stock_level` by `recommended_quantity` (simulating an inbound replenishment shipment) and restores stock.
- Double acceptance/rejection is prevented with validation checks (`400 Bad Request`).

### Tradeoffs
- **Pros**: Complete human control; auditability; zero unintended price changes; robust state consistency.
- **Cons**: Requires merchandiser action to apply recommendations.

---

## ADR 8: Technology Selection (FastAPI + React + SQLite/PostgreSQL)

**Status**: Accepted  
**Date**: August 24, 2026  

### Decision & Rationale
- **FastAPI (Python 3.11+) over Spring Boot**: Native async/await, integrated Pydantic v2 validation, automatic OpenAPI/Swagger documentation, fast startup, and native Python LLM ecosystem integration.
- **SQLModel / SQLAlchemy**: Unified ORM and schema layer providing zero-config local SQLite execution while maintaining 100% portability to PostgreSQL in production.
- **React + Vite + TypeScript**: Fast hot module replacement (HMR), component-driven UI architecture, and strict type safety for merchandising workflows.
- **Strict Folder Isolation**: Backend (`backend/`) and frontend (`frontend/`) maintain independent package manifests, dependencies, virtual environments, and build pipelines.

---

## ADR 9: Future Extension Seams (Sprint 2 Roadmap)

**Status**: Proposed / Planned  

The architecture is deliberately structured with pluggable seams for Sprint 2 enhancements:
1. **Competitor Pricing & Catalog Sync**: `cost_price` and `supplier_id` are already present in `Product`. A new `CompetitorAwareStrategy` can implement `PricingStrategy` and register with `StrategyManager.register_strategy("competitor", CompetitorAwareStrategy())`.
2. **Margin Floor Safeguards**: Enforce `recommended_price >= cost_price * (1 + margin_floor)`.
3. **Automated Purchase Orders**: Accepting a `ReorderSuggestion` can emit an outbound PO payload to `supplier_id`.
4. **Price Change Cooldowns**: Restrict frequency of price changes per SKU within a rolling 7-day window.