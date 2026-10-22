# Snowflake Platform Capabilities for an Electronic Prior Authorization (ePA) Hackathon Product (as of Oct 2026)

Product context: Next.js/React front end acting as an EHR (provider) simulator and a payer portal; FHIR JSON bundles in Snowflake; payer rules tables; four Cortex Agents: (a) DTR questionnaire auto-fill, (b) payer clinical review (approve/deny/pend with citations), (c) PA metrics analytics, (d) denial explainer and appeal drafter.

Research date: 2026-10-18. Snowflake renamed several products at Summit 2026 (June). **Snowflake Intelligence is now "Snowflake CoWork"** and **Cortex Code is now "Snowflake CoCo."** Current docs use the new names.

---

## 1. Cortex Agents: architecture, API, tools, auth from SPCS, streaming, observability, MCP

### Takeaway
Cortex Agents is a fully managed agent platform built around schema-level `AGENT` objects (`CREATE AGENT ... FROM SPECIFICATION $$yaml$$`). Agents are invoked over REST (`.../agents/{name}:run`) with SSE streaming, server-side threads, and tools: Cortex Analyst (semantic views), Cortex Search, custom stored procedures/UDFs ("generic"), web search, data_to_chart, code execution, and MCP connectors. Monitoring, feedback, and evaluations (GA March 2026) are built in, and the Snowflake-managed MCP server (GA Nov 2025) can expose agents and tools to external MCP clients. All four product agents map directly onto this.

### Cited Findings
**Architecture and objects**
- Cortex Agents is a "fully managed agentic platform." The loop is plan, use tools, reflect, respond. Key concepts are Agent (a schema-level object bundling model, tools, orchestration settings, instructions), Tools, Orchestration, Thread (persisted context), and Run (one `agent:run` request). Variants are permanent, temporary (session-only), and secure agents (specification hidden from non-owners). — [Cortex Agents overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)
- Tools: Cortex Analyst (SQL over semantic views), Cortex Search (unstructured), Analytical search (**Public Preview**; counts/aggregates/trends over large document collections), Code execution (Python in an isolated sandbox), Data to Chart, Custom tools (stored procedures and UDFs), agent skills, MCP connectors, agent toolsets, and Web search (must be enabled at account level). — [Cortex Agents overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)
- Cortex Agents APIs are **not supported from Streamlit in Snowflake on a warehouse runtime**. Use a container runtime. — [Cortex Agents overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)

**CREATE AGENT syntax and spec fields**
- `CREATE OR REPLACE AGENT myagent COMMENT = '...' PROFILE = '{"display_name": "...", "avatar": "...", "color": "blue"}' FROM SPECIFICATION $$ ... $$;` — [Create and manage agents](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-manage)
- Spec YAML keys:
  - `models: orchestration: auto` (or a named model such as `claude-sonnet-5`).
  - `orchestration:` with `tool_not_accessible: accept`, `budget: {seconds: 30, tokens: 16000}`, and `capabilities: {analytical_search: true}` (off by default).
  - `instructions:` with `response`, `orchestration`, and `sample_questions`.
  - `tools:` as a list of `tool_spec: {type, name, description, input_schema}`. Type values are `cortex_analyst_text_to_sql`, `cortex_search`, `data_to_chart`, `generic`, and `web_search`.
  - `tool_resources:` keyed by tool name. Analyst uses `semantic_view: "db.schema.sv"`. Search uses `search_service`, `max_results`, `filter`, `title_column`, `id_column`, `stage_path`, and `relative_path_column`.
  - Source: [Create and manage agents](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-manage)
- Generic (custom) tool resources take `type` (function/procedure), `execution_environment` (warehouse), and `identifier`. Web search takes `max_results`. — [Agents Run API](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-run)

**Models**
- Snowflake recommends `auto` (highest-quality model available to the account). Agent orchestration models listed:
  - Anthropic Claude: Opus 4.5 through 5, Sonnet 4.5 through 5, Haiku 4.5, legacy Sonnet 4.
  - OpenAI: GPT-5 through 5.4, 5-mini, legacy 4.1.
  - Google: Gemini 3.5 Flash (GA) and 3.1 Pro (public preview).
  - Models run via cross-region inference, and availability depends on the `CORTEX_ENABLED_CROSS_REGION` routing scope. Check with `SHOW CORTEX BASE MODELS`.
  - Source: [Cortex Agents overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)

**REST API**
- Endpoints:
  - Run an agent object: `POST /api/v2/databases/{db}/schemas/{schema}/agents/{name}:run`
  - Run without an object: `POST /api/v2/cortex/agent:run` (supply `models`, `instructions`, `orchestration`, `tools`, `tool_resources` inline)
  - Stream or replay an existing run: `GET /api/v2/cortex/agent/runs/{run_id}`
  - Cancel: `POST /api/v2/cortex/agent/runs/{run_id}/cancel`
  - Source: [Agents Run API](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-run)
- Object-run body: `thread_id`, `parent_message_id`, `messages`, `background`, `stream`, `tool_choice` (`type` auto/required/tool, plus `name[]`). — [Agents Run API](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-run)
- SSE events: `response.status`, `response.thinking(.delta)`, `response.text(.delta)`, `response.text.annotation` (citations), `response.tool_use`, `response.tool_result(.status)`, `response.tool_result.analyst.delta`, `response.table`, `response.chart`, `response.warning`, `error`, `metadata`, and the final `response`. `stream` defaults to true. Use `stream:false` with `Accept: application/json` for a single JSON response. — [Agents Run API](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-run)
- Limits:
  - Synchronous runs time out at 15 minutes.
  - `background: true` runs time out at 6 hours, require threads, and are GA on AWS and Azure.
  - Run events can be replayed for 5 minutes after completion, after which the API returns 409.
  - `orchestration.budget` (seconds/tokens) caps a run.
  - Source: [Agents Run API](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-run)
- Threads: create with `POST /api/v2/cortex/threads` (body includes `origin_application`), then pass `thread_id` and `parent_message_id` (starts at 0). Feedback: `POST .../agents/{name}:feedback` with `request_id`, `positive`, `feedback_message`, `categories`, and `thread_id`. — [Create and manage agents](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-manage)

**Auth and privileges**
- REST APIs support PATs, key-pair JWT, and OAuth. The `X-Snowflake-Role` header selects the role. Required: `SNOWFLAKE.CORTEX_USER` or `SNOWFLAKE.CORTEX_AGENT_USER` (agents only), `CREATE AGENT` on the schema, `USAGE` on the agent, db, and schema, plus USAGE on tool warehouses, search services, semantic views, and procedures. — [Access control and authentication](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-setup)

**Calling the agent from SPCS**
- Inside SPCS, Snowflake provides an OAuth token in `/snowflake/session/token` (refreshed every few minutes, valid up to 1 hour). It must be used with `SNOWFLAKE_HOST`, and it "can't be used outside Snowpark Container Services." — [SPCS SQL execution](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/spcs-execute-sql)
- Caller's rights: with spec `capabilities: securityContext: executeAsCaller: true`, Snowflake injects the `Sf-Context-Current-User-Token` header on ingress requests. The app connects with `authenticator: "oauth"` and token `<service-token>.<Sf-Context-Current-User-Token>`. This requires `CALLER USAGE` / `INHERITED CALLER SELECT` grants to the service owner role. — [SPCS Tutorial 7: caller's rights](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/tutorials/advanced/tutorial-7-callers-rights)
- Public endpoints add an `Sf-Context-Current-User: <user_name>` header. `...-Email` is available via Support. — [SPCS additional considerations](https://docs.snowflake.com/developer-guide/snowpark-container-services/additional-considerations-services-jobs.html)

**Snowflake Intelligence / CoWork**
- Snowflake Intelligence went GA on Nov 4, 2025. — [Release note](https://docs.snowflake.com/release-notes/2025/other/2025-11-04-snowflake-intelligence)
- It was renamed **Snowflake CoWork** at Summit 2026 (June 3, 2026) and now includes personalized work agents, scheduled automations, and MCP connectors. — [IT Brief](https://itbrief.com.au/story/snowflake-renames-ai-tools-amid-broader-platform-push); also [select.dev Summit recap](https://select.dev/posts/snowflake-summit-2026-what-actually-shipped-and-what-it-means) (auto-routing orchestrator, user memory, Slack/Teams connectors)
- Summit 2026 security announcements: Trust Center AI Security Package, data movement policies restricting agent actions, multi-party approvals, and agent identity (agents inherit creator permissions, which can be restricted). — [IT Brief](https://itbrief.com.au/story/snowflake-renames-ai-tools-amid-broader-platform-push)

**Monitoring and evaluations**
- Traces go to the `SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS` event table in OpenTelemetry style. Each turn is a trace, and spans cover planning, tool calls, SQL, charts, and response.
- Read traces with the `GET_AI_OBSERVABILITY_EVENTS(db, schema, agent, 'CORTEX AGENT')` table function, or in Snowsight under AI & ML → Agents → Observability.
- Privileges: OWNERSHIP or MONITOR on the agent. Viewing full prompt and response content also requires the account privilege `READ UNREDACTED AI OBSERVABILITY EVENTS TABLE`. This matters for PHI.
- Source: [Monitor agents](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-monitor)
- **Cortex Agent evaluations went GA on Mar 13, 2026.** Metrics: answer correctness (against an expected answer), logical consistency (reference-free), and custom LLM-judge metrics (for example, policy-compliance checks). — [Release note](https://docs.snowflake.com/release-notes/2026/other/2026-03-13-cortex-agent-evaluations); [guide](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-evaluations)
- Cost controls: resource budgets for agents and per-user quotas. — [Cortex Agents overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)

**Cortex Guard**
- `AI_COMPLETE(... model_parameters => {'guardrails': true})` filters unsafe output (violence, hate, sexual content, self-harm) using Llama Guard 3. It is billed on input tokens. — [AI_COMPLETE](https://docs.snowflake.com/en/sql-reference/functions/ai_complete-single-string)

**Managed MCP server**
- **GA on Nov 4, 2025.** — [Release note](https://docs.snowflake.com/release-notes/2025/other/2025-11-04-cortex-agents-mcp)
- Syntax: `CREATE [OR REPLACE] MCP SERVER [IF NOT EXISTS] <name> FROM SPECIFICATION $$ <yaml> $$;`
- Tool types: `CORTEX_SEARCH_SERVICE_QUERY`, `CORTEX_ANALYST_MESSAGE`, `SYSTEM_EXECUTE_SQL`, `CORTEX_AGENT_RUN`, and `GENERIC` (UDF/procedure).
- Endpoint: `https://<account_url>/api/v2/databases/{db}/schemas/{schema}/mcp-servers/{name}`.
- Auth: Snowflake OAuth by default, or External OAuth (Okta/Entra). Dynamic client registration isn't supported.
- Limits: 50 tools per server, 250 KB response truncation for generic and SQL tools, MCP revision 2025-11-25, tools capability only, agent-to-agent recursion depth of 10, and no failover replication of MCP server objects.
- Source: [Snowflake-managed MCP server](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-mcp)
- **Native Apps can include Cortex Agents, managed MCP servers, and SPCS-hosted MCP servers (GA Aug 7, 2026).** Agents from different apps can call each other only through tools the providers expose and consumers approve. — [Release note](https://docs.snowflake.com/release-notes/2026/other/2026-08-07-native-apps-agents-mcp-ga)

### Inferences
- **Agent design for the product:**
  - **DTR auto-fill agent:**
    - Cortex Search over chunked clinical notes, filtered by `patient_id`.
    - A generic tool (Python stored procedure) that loads the Questionnaire JSON and patient FHIR resources and returns a draft QuestionnaireResponse. Internally it can call `AI_COMPLETE` with a `response_format` JSON schema.
  - **Payer clinical review agent:**
    - Cortex Search over medical policy PDFs, with `title_column`/`id_column` so `response.text.annotation` events carry citations.
    - A Search service over submitted clinical documents.
    - A generic tool `EVALUATE_CRITERIA(pa_id)` that returns structured approve/deny/pend.
    - A `tool_choice: required` setting to force retrieval.
  - **Analytics agent:** Cortex Analyst over a PA-metrics semantic view, plus `data_to_chart`.
  - **Appeal agent:** Search over policy, a generic tool to fetch the decision record, and response instructions for letter format.
- **Auth from the React app:** have the Next.js server-side route (or a FastAPI sidecar) call the agent REST API, not the browser.
  - The SPCS service token with `executeAsCaller` is designed for SQL connections. The docs don't explicitly confirm using it as a bearer token for `/api/v2/.../agents:run`.
  - Safer hackathon fallbacks: (1) call the agent via SQL if a SQL entry point exists (not confirmed here), (2) use a PAT or key-pair JWT stored as a Snowflake SECRET mounted into the container, or (3) use App Runtime (see section 6), which handles per-user identity.
  - Test the SPCS OAuth token against the REST endpoint early. Calling Snowflake's public hostname from a container may require an External Access Integration (EAI).
- Use CoWork (the former Snowflake Intelligence UI) as a zero-code demo surface for the analytics agent, alongside the custom React UI.
- Exposing the payer review agent through the managed MCP server (`CORTEX_AGENT_RUN`) would let the team demo interoperability, for example from Claude Desktop or another MCP client. This could be a differentiator.

### Gaps
- There's no explicit doc confirming that the SPCS `/snowflake/session/token` works as a bearer token for the Cortex Agents REST API, or what `X-Snowflake-Authorization-Token-Type` value it needs. Verify hands-on.
- I didn't confirm whether a SQL function for running an agent exists (for example, `SNOWFLAKE.CORTEX.AGENT_RUN` or `DATA_AGENT_RUN`).
- I found no TruLens-specific doc for current agent evals. The eval docs describe built-in metrics only.
- The agent page's model list (Claude Opus/Sonnet 5, GPT-5.4, Gemini 3.5 Flash) is newer than the AI_COMPLETE regional table (which lists claude-opus-4-8 as its newest Claude, in preview). The two pages may be updated on different cadences. Run `SHOW CORTEX BASE MODELS` in the target account.

---

## 2. Cortex Search (policy PDFs, clinical notes)

### Takeaway
Cortex Search is a managed hybrid (vector + keyword + semantic rerank) search service defined over a SQL query. It supports attribute filters, incremental refresh via PRIMARY KEY, and multi-index search. It is the right retrieval layer for both medical-policy PDFs (after AI_PARSE_DOCUMENT and chunking) and clinical notes (filtered by patient/member).

### Cited Findings
- Syntax: `CREATE OR REPLACE CORTEX SEARCH SERVICE svc ON text_col ATTRIBUTES region WAREHOUSE = wh TARGET_LAG = '1 day' EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0' AS (SELECT ...);`
  - The default embedding model is `snowflake-arctic-embed-m-v1.5`.
  - Optional `PRIMARY KEY (cols)` enables incremental refresh. Key columns must be TEXT.
  - `AUTO_SUSPEND` has a minimum of 1800 seconds.
  - Source: [Cortex Search overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview.html)
- Hybrid search combines vector, keyword, and semantic reranking. Scoring can be customized with numeric boosts, time decay, and component weights. — [Cortex Search overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview.html)
- Query options:
  - SQL: `SNOWFLAKE.CORTEX.SEARCH_PREVIEW('db.schema.svc', '{"query":..., "columns":[...], "filter":{"@eq":{"region":"..."}}, "limit":1}')`
  - Python: `service.search(...)`
  - REST
  - Source: [Cortex Search overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview.html)
- Limits:
  - The source query must return fewer than 400M rows.
  - Defaults are 20 QPS per service and 140 QPS per account, with HTTP 429 beyond that.
  - Recommended chunks are ≤512 tokens (about 385 words). Longer text is truncated for embedding, but keyword search uses the full text.
  - No cloning, and base tables can't be dropped while the service exists.
  - Source: [Cortex Search overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview.html)
- Multi-index search: text indexes for exact or fuzzy matching (for example, codes or names) and vector indexes for semantic matching. User-provided embeddings are also supported. — [Cortex Search overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview.html)
- Snowflake has an official tutorial for a PDF chatbot with Cortex Search (parse, chunk, index). — [Tutorial 3](https://docs.snowflake.cn/user-guide/snowflake-cortex/cortex-search/tutorials/cortex-search-tutorial-3-chat-advanced)

### Inferences
- **Policy service:** `ON chunk ATTRIBUTES policy_id, payer_id, cpt_code, section, effective_date`. Then filter by the requested CPT/HCPCS code so the reviewer agent sees only the relevant policy.
- **Clinical notes service:** `ATTRIBUTES patient_id, encounter_date, note_type`. The agent tool_resources `filter` (or a dynamic filter) should scope retrieval to the patient. This is a correctness and privacy requirement.
- A multi-index text index on CPT/ICD codes would improve exact-code recall.

### Gaps
- I didn't capture the full filter operator list (`@and`, `@or`, `@contains`, `@gte`). It is on the Cortex Search query page.
- I didn't confirm the status of a native multimodal (PDF-image) Cortex Search option.

---

## 3. Cortex Analyst: semantic views vs YAML, verified queries

### Takeaway
Semantic views (`CREATE SEMANTIC VIEW`) are the recommended approach. YAML semantic model files on stages remain supported for backward compatibility. Verified queries can be embedded directly with `AI_VERIFIED_QUERIES`.

### Cited Findings
- "Semantic Views are the recommended approach for new implementations." Legacy YAML files on stages "are still supported for backward compatibility." — [Cortex Analyst](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst)
- Syntax: `CREATE [OR REPLACE] SEMANTIC VIEW <name> TABLES (...) [RELATIONSHIPS (...)] [FACTS (...)] [DIMENSIONS (...)] [METRICS (...)] [AI_SQL_GENERATION '<instructions>'] [AI_VERIFIED_QUERIES (q AS (QUESTION '...' SQL '...'), ...)]`. FACTS must come before DIMENSIONS, and at least one dimension or metric is required. — [CREATE SEMANTIC VIEW](https://docs.snowflake.com/en/sql-reference/sql/create-semantic-view)
- Semantic View Autopilot can generate a view or ingest a YAML spec. Horizon Context (Summit 2026) extends Horizon Catalog with semantic views. — [Semantic views overview](https://docs.snowflake.com/en/user-guide/views-semantic/overview); [IT Brief](https://itbrief.com.au/story/snowflake-renames-ai-tools-amid-broader-platform-push)
- In agents, the tool resource is `cortex_analyst_text_to_sql` with exactly one of `semantic_view` or `semantic_model_file`. — [Agents Run API](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-run)

### Inferences
- Build a `PA_METRICS_SV` semantic view over PA_REQUEST, PA_DECISION, MEMBER, SERVICE_CODE, and PROVIDER.
  - Metrics: approval rate, median turnaround hours, pend rate, auto-approval rate, and the denial reasons distribution.
  - Add verified queries for CMS-0057-F-style metrics (for example, decisions within 72h for expedited and 7 days for standard).

### Gaps
- Cortex Analyst GA status and quotas aren't stated on the overview page. It is widely used in production, but I didn't capture an explicit statement.

---

## 4. Cortex AI Functions (AISQL) and Document AI

### Takeaway
The full AI Function family is available. AI_COMPLETE supports structured outputs, Cortex Guard, and Claude models via cross-region inference. AI_PARSE_DOCUMENT (OCR/LAYOUT) and AI_EXTRACT handle document ingestion. **Document AI was decommissioned on March 16, 2026, and AI_EXTRACT replaces it.** AI_REDACT is PII-focused, not full HIPAA PHI de-identification.

### Cited Findings
- Functions: AI_COMPLETE, AI_CLASSIFY, AI_FILTER, AI_AGG, AI_EMBED, AI_MULTI_EMBED, AI_EXTRACT, AI_SENTIMENT, AI_SUMMARIZE, AI_SUMMARIZE_AGG, AI_SIMILARITY, AI_TRANSCRIBE, AI_PARSE_DOCUMENT, AI_REDACT, AI_TRANSLATE, plus the helpers TO_FILE, AI_COUNT_TOKENS, and PROMPT.
  - Access requires the `USE AI FUNCTIONS` account privilege and the CORTEX_USER or AI_FUNCTIONS_USER role.
  - The functions are optimized for throughput and batch work. For interactive latency, Snowflake points to the REST Complete, Embed, and Agents APIs.
  - Source: [Cortex AI Functions](https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql)
- AI_AGG and AI_SUMMARIZE_AGG are "not subject to context window limits." — [Cortex AI Functions](https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql)
- AI_COMPLETE syntax: `AI_COMPLETE(model, prompt [, model_parameters, response_format, show_details])`.
  - `model_parameters` takes temperature, top_p, max_tokens (default 4096), and guardrails.
  - `response_format` takes a JSON schema object `{'type':'json','schema':{...}}` or `TYPE OBJECT(...)`.
  - `show_details` returns `structured_output` plus usage.
  - Source: [AI_COMPLETE](https://docs.snowflake.com/en/sql-reference/functions/ai_complete-single-string)
- AI_COMPLETE models:
  - Claude: claude-opus-4-8 (preview), opus-4-7, opus-4-6, sonnet-4-6, sonnet-4-5, opus-4-5, haiku-4-5, claude-4-sonnet (legacy).
  - OpenAI: openai-gpt-5.x family.
  - Google: gemini-3.1-pro (preview).
  - Also Llama 3.x/4, mistral-large2/3, and deepseek-r1.
  - **Claude models are not native in any region table. They are available only via cross-region inference.**
  - Source: [Regional availability](https://docs.snowflake.com/user-guide/snowflake-cortex/aisql-regional-availability)
- Cross-region inference: `ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION' | 'AWS_US' | ... | 'DISABLED'` (ACCOUNTADMIN only).
  - Organizations created after Mar 9, 2026 default to ANY_REGION.
  - Prompts and responses are not persisted in the processing region, and traffic is encrypted (mTLS across clouds).
  - There are no egress charges.
  - Source: [Cross-region inference](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cross-region-inference)
- AI_PARSE_DOCUMENT: `AI_PARSE_DOCUMENT(file_object [, options] [, return_error_details])` on a staged FILE.
  - Modes: OCR (default) or LAYOUT (Markdown with tables).
  - `page_split` works for PDF, pptx, and docx.
  - `page_filter` selects page ranges.
  - `extract_images` works in LAYOUT mode only.
  - It is native in select regions and available everywhere via cross-region inference.
  - Source: [AI_PARSE_DOCUMENT](https://docs.snowflake.com/en/sql-reference/functions/ai_parse_document)
- AI_REDACT: `AI_REDACT(input [, categories] [, return_error_details] [, mode])`. Mode is `redact` or `detect` (detect returns spans).
  - Categories: NAME, EMAIL, PHONE_NUMBER, DATE_OF_BIRTH, GENDER, AGE, ADDRESS, NATIONAL_ID, PASSPORT, TAX_IDENTIFIER, PAYMENT_CARD_DATA, DRIVERS_LICENSE, and IP_ADDRESS.
  - **Medical record numbers and general dates are not covered.**
  - Input plus output is limited to 4,096 tokens (output 1,024), so chunk longer text.
  - Detection is best-effort.
  - Source: [AI_REDACT](https://docs.snowflake.com/en/sql-reference/functions/ai_redact)
- **Document AI:** the UI and `!PREDICT` were decommissioned on March 16, 2026. Snowflake recommends AI_EXTRACT (powered by `arctic-extract`, single-step, token billing). — [BCR-2156](https://docs.snowflake.com/en/release-notes/bcr-bundles/un-bundled/bcr-2156)
- At Summit 2026, AI Complete gained audio and video input, and Cortex AI Function Studio entered public preview. — [select.dev recap](https://select.dev/posts/snowflake-summit-2026-what-actually-shipped-and-what-it-means)

### Inferences
- **Pipeline:**
  - Load policy PDFs and scanned clinical attachments to a stage.
  - Run `AI_PARSE_DOCUMENT(... {'mode':'LAYOUT','page_split':true})`.
  - Chunk with `SPLIT_TEXT_RECURSIVE_CHARACTER` (or a markdown splitter).
  - Index with Cortex Search.
- Use `AI_EXTRACT` to pull structured criteria (for example, "conservative therapy ≥6 weeks") from policies into a criteria table.
- Use `AI_COMPLETE` with a JSON schema for deterministic decision objects: `{decision, criteria_met[], missing_info[], citations[]}`.
- Use `AI_CLASSIFY` to triage requests (urgent vs standard, service category).
- Use `AI_FILTER` in SQL joins (for example, match notes that mention a failed conservative therapy).
- Use `AI_AGG` for denial-trend narratives.
- Use `AI_TRANSCRIBE` for an optional peer-to-peer call transcript.
- Use AI_REDACT only as a supplementary safeguard. Use synthetic data (Synthea) for the hackathon.

### Gaps
- I didn't capture per-function GA vs preview status. The overview page doesn't state it, and only models are flagged.
- I didn't fetch the AI_EXTRACT reference for limits (pages, file size) or AI_CLASSIFY/AI_FILTER syntax details.

---

## 5. Semi-structured data (FHIR JSON), validation, UDFs, EAI

### Takeaway
FHIR bundles fit naturally in a `VARIANT` column, queried with path notation and `LATERAL FLATTEN`. Snowflake's own FHIR quickstart uses only native SQL. Validation would need a custom Snowpark UDF.

### Cited Findings
- The Snowflake FHIR quickstart:
  - Stages Synthea FHIR JSON and loads it with `COPY INTO` into a `VARIANT` column (`ON_ERROR='SKIP_FILE'`).
  - Builds views using paths (`JSON_STRING:entry[0].fullUrl`) and `LATERAL FLATTEN` over `entry`, `identifier`, `extension`, and `code.coding`.
  - Applies masking policies on the view columns.
  - Uses no Java UDFs or HAPI.
  - Source: [Processing HL7 FHIR messages with Snowflake](https://www.snowflake.com/en/developers/guides/processing-hl7-fhir-messages-with-snowflake/); [repo](https://github.com/Snowflake-Labs/sfquickstarts/tree/master/site/sfguides/src/processing-hl7-fhir-messages-with-snowflake)
- An HL7 data-product guide also exists. — [Unpacking complex HL7 data](https://www.snowflake.com/en/developers/guides/powering-ai-ready-data-products-by-unpacking-complex-hl7-data-using-snowflake/)

### Inferences
- **Table pattern:** `FHIR_BUNDLE_RAW(bundle_id, patient_id, received_at, bundle VARIANT)`, plus flattened views per resource type (Patient, Condition, Observation, MedicationRequest, Coverage, ServiceRequest, Questionnaire, QuestionnaireResponse, Claim, ClaimResponse).
- **Validation:** a Python UDF using the `jsonschema` package against the official FHIR JSON schema (offline, no EAI needed if the schema file is in a stage), or a Java UDF bundling the HAPI FHIR validator JAR from a stage. For profile validation against Da Vinci PAS/DTR IGs, HAPI is the stronger option, though it is heavy.
- An EAI is only needed for outbound calls (for example, to a public terminology server or the HL7 IG registry).

### Gaps
- I didn't verify current Snowpark Anaconda/Artifact Repository availability of `jsonschema`/`fhir.resources`, Java UDF JAR size limits, or the EAI syntax in this session. These are well established, but they weren't freshly cited here.

---

## 6. Transactional state: Hybrid Tables vs Snowflake Postgres

### Takeaway
Both are GA. Hybrid tables are GA on AWS/Azure commercial regions but **not available on trial accounts** and support **no streams or dynamic tables**. Snowflake Postgres went **GA on Feb 24, 2026** (PG 16/17/18, PgBouncer, Private Link, CDC mirroring into Snowflake). For an operational PA state store backing a Next.js app, Postgres is the better fit for low-latency OLTP and ORM compatibility. Hybrid tables keep everything in one SQL engine and governance plane. For a hackathon, standard tables plus streams may be simplest if the account is a trial.

### Cited Findings
- Hybrid tables are GA in AWS and Azure commercial regions only. PRIMARY KEY is required and enforced, there is row-level locking, and secondary indexes update synchronously. Use cases include lightweight transactional apps and high-concurrency point reads and writes. — [Hybrid tables](https://docs.snowflake.com/en/user-guide/tables-hybrid)
- Hybrid table limitations:
  - Not supported in trial accounts.
  - **Streams and dynamic tables are not supported.**
  - No replication.
  - A 2 TB quota per database.
  - About 16,000 ops/sec per database (80/20 read/write).
  - Tri-Secret Secure only with Dedicated Storage Mode.
  - Source: [Hybrid table limitations](https://docs.snowflake.com/en/user-guide/tables-hybrid-limitations)
- Triggered tasks are not supported on hybrid tables. — [Triggered tasks](https://docs.snowflake.com/en/user-guide/tasks-triggered)
- Snowflake Postgres went GA on Feb 24, 2026. It runs on dedicated Snowflake-managed VMs and works with any Postgres client. — [Release note](https://docs.snowflake.com/release-notes/2026/other/2026-02-24-snowflake-postgres-ga)
- Postgres details:
  - Versions 16/17/18.
  - AWS (19 regions) and Azure (16 regions); no GCP.
  - Isolated private network with firewall rules or Private Link.
  - Built-in PgBouncer.
  - Recommended for high-throughput operational workloads.
  - Source: [Snowflake Postgres about](https://docs.snowflake.com/en/user-guide/snowflake-postgres/about)
- At Summit 2026, Postgres was presented as GA with private link, customer-managed keys, and pg_lake. Postgres data mirroring (CDC sync into Snowflake) was also announced. — [select.dev recap](https://select.dev/posts/snowflake-summit-2026-what-actually-shipped-and-what-it-means)
- A Postgres compute usage history view was added on Aug 12, 2026. — [Release note](https://docs.snowflake.com/release-notes/2026/other/2026-08-12-postgres-compute-usage-history-view)

### Inferences
- **Recommended hackathon architecture:**
  - PA workflow state (request status transitions, task queue, UI sessions) in Snowflake Postgres if the account is paid. Mirror it into Snowflake for analytics and agents.
  - Otherwise, use standard Snowflake tables with streams and triggered tasks (simplest, fully event-driven).
  - Use hybrid tables only if you don't need streams on them (for example, a member eligibility lookup table with point reads).
- Because streams aren't supported on hybrid tables, an event-driven "new PA → payer evaluation" flow is easier on standard tables.

### Gaps
- I couldn't confirm Snowflake Postgres's HIPAA/BAA coverage, edition requirement, or trial availability. The docs page doesn't state them.
- I didn't confirm whether Postgres mirroring is GA or preview.

---

## 7. Event-driven processing: Streams, Tasks, Dynamic Tables, Snowpipe Streaming, Alerts

### Takeaway
Triggered tasks (`WHEN SYSTEM$STREAM_HAS_DATA`, serverless, down to a 10s interval) are the natural mechanism for "new PA request → run payer evaluation agent/procedure."

### Cited Findings
- Syntax: `CREATE TASK t TARGET_COMPLETION_INTERVAL='15 MINUTES' WHEN SYSTEM$STREAM_HAS_DATA('s') AS ...`, with no SCHEDULE.
  - Omitting WAREHOUSE makes the task serverless.
  - Tasks start suspended, so run `ALTER TASK ... RESUME`.
  - The default minimum interval is 30s, adjustable to 10s via `USER_TASK_MINIMUM_TRIGGER_INTERVAL_IN_SECONDS`.
  - Supported stream sources: tables, views, dynamic tables, Iceberg tables, shares, and directory tables. Hybrid tables and external tables are not supported.
  - Source: [Triggered tasks](https://docs.snowflake.com/en/user-guide/tasks-triggered)
- Directory-table streams (for new uploaded PDFs) need stage refresh (auto or manual) before triggering. — [Triggered tasks](https://docs.snowflake.com/en/user-guide/tasks-triggered)
- At Summit 2026, Snowflake announced Datastream, a Kafka wire-compatible native streaming ingestion service. — [IT Brief](https://itbrief.com.au/story/snowflake-renames-ai-tools-amid-broader-platform-push); [select.dev](https://select.dev/posts/snowflake-summit-2026-what-actually-shipped-and-what-it-means)

### Inferences
- **Event flow:**
  1. The provider submits PAS Bundle → INSERT into `PA_REQUEST`.
  2. A stream on `PA_REQUEST` fires a triggered task, which calls a Python stored procedure. The procedure runs rules (eligibility plus PA-required lookup), then invokes the reviewer logic (AI_COMPLETE with a structured schema, or the agent REST endpoint).
  3. The procedure writes `PA_DECISION`, and the UI polls or streams the result.
- A directory table on the attachments stage with a stream and triggered task can run AI_PARSE_DOCUMENT on new uploads.
- Dynamic tables can maintain flattened FHIR views and PA metrics incrementally.

### Gaps
- I didn't fetch docs for Snowpipe Streaming (high-performance architecture), Alerts (`CREATE ALERT`), or notification integrations (email/webhook). These are known GA features, but they weren't cited in this session.
- I didn't confirm whether a stored procedure can call the Cortex Agent REST API from inside Snowflake without an EAI.

---

## 8. App hosting: SPCS, App Runtime, Native Apps, Streamlit

### Takeaway
There are three viable hosting paths.
- **SPCS** (full control: Next.js plus FastAPI containers, public endpoint with Snowflake OAuth login, caller's rights).
- **Snowflake App Runtime** (**GA Sept 1, 2026**; purpose-built for Node.js/Next.js with `snow app deploy`, SSO, and run-as-user queries; not on trial accounts).
- **Streamlit in Snowflake** on container runtime (GA per Summit 2026). Agents API isn't supported on warehouse-runtime Streamlit.

### Cited Findings
- SPCS:
  - `CREATE SERVICE ... IN COMPUTE POOL ... FROM SPECIFICATION $$...$$` (or from a stage spec file).
  - Endpoints marked `public: true` allow HTTP ingress.
  - Browser users are redirected to Snowflake login (OAuth). Programmatic callers use a PAT, key-pair auth, or a session token.
  - Users need a service role granting endpoint access.
  - Service functions use `CREATE FUNCTION ... SERVICE=... ENDPOINT=... AS '/path'` and work with HTTP endpoints only.
  - Source: [Working with services](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/working-with-services)
- Caller's rights (`executeAsCaller`) and the `Sf-Context-Current-User(-Token)` headers: see section 1. — [Tutorial 7](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/tutorials/advanced/tutorial-7-callers-rights)
- Snowflake App Runtime:
  - **GA Sept 1, 2026.**
  - Builds Node.js/Next.js apps (Python planned), configured with an `app.yml` manifest and deployed with `snow app setup` / `snow app deploy`, which returns a live SSO URL.
  - Queries run as the service or as the signed-in user.
  - Available on AWS, Azure, and GCP commercial regions. **Not available in gov regions or on trial accounts.**
  - Source: [GA release note](https://docs.snowflake.com/en/release-notes/2026/other/2026-09-01-snowflake-app-runtime-ga); [About App Runtime](https://docs.snowflake.com/en/developer-guide/snowflake-app-runtime); [Quickstart](https://www.snowflake.com/en/developers/guides/getting-started-snowflake-app-runtime/)
- Streamlit in Snowflake on container runtime was reported GA at Summit 2026. — [select.dev](https://select.dev/posts/snowflake-summit-2026-what-actually-shipped-and-what-it-means)
- Native Apps can bundle agents, managed MCP servers, and SPCS-hosted MCP servers.
  - App agents run under restricted caller's rights, and owner's-rights agents aren't supported.
  - Consumers need Cortex Agents and CoWork enabled.
  - External MCP clients can reach an SPCS ingress URL directly, but not via OAuth yet.
  - Source: [Use Cortex Agents and MCP servers in an app](https://docs.snowflake.com/developer-guide/native-apps/agents-mcp-servers)

### Inferences
- **For a React/Next.js product:** App Runtime is now the lowest-friction path, with SSO and run-as-user built in. Use SPCS if you need multi-container services (Next.js plus FastAPI), custom images, or service functions.
- Run the "EHR simulator" and "payer portal" as two routes or two apps, with different Snowflake roles (PROVIDER_ROLE and PAYER_REVIEWER_ROLE). Row access policies then enforce separation.
- A Native App packaging (with containers plus agents) is a strong "productization / Marketplace-ready" story for judges.

### Gaps
- I didn't fetch App Runtime limits or confirm how it authenticates calls to the Cortex Agents REST API.
- I didn't check SPCS compute pool instance families or GPU availability (not needed for this product).
- SPCS availability on trial accounts wasn't confirmed from fetched content.

---

## 9. Governance and compliance for PHI

### Takeaway
PHI under HIPAA/HITRUST requires **Business Critical edition** (or VPS). Enterprise provides masking, row access policies, and classification. Horizon/Trust Center add classification profiles with auto tag-based masking, and Summit 2026 added AI-specific security controls. Snowflake docs reviewed don't explicitly state HIPAA coverage of Cortex AI features or cross-region inference. Use synthetic data for the hackathon.

### Cited Findings
- Business Critical and VPS include: "Support for PHI data (in accordance with HIPAA and HITRUST CSF regulations)," Tri-Secret Secure, and PrivateLink / Private Service Connect. — [Snowflake editions](https://docs.snowflake.com/en/user-guide/intro-editions)
- Enterprise includes column-level security (masking policies), row access policies, classification, aggregation and projection policies, and differential privacy. — [Snowflake editions](https://docs.snowflake.com/en/user-guide/intro-editions)
- Sensitive data classification (Enterprise+):
  - Classification profiles (created in Trust Center or SQL) auto-classify databases.
  - Columns get the `SNOWFLAKE.CORE.SEMANTIC_CATEGORY` and `PRIVACY_CATEGORY` tags (IDENTIFIER, QUASI_IDENTIFIER, SENSITIVE).
  - User tags can be mapped so tag-based masking applies automatically.
  - Custom categories are supported. There is no dedicated healthcare category; medical data falls under SENSITIVE.
  - AI mode (preview) uses openai-gpt-5-mini.
  - Source: [Classification intro](https://docs.snowflake.com/en/user-guide/classify-intro)
- Agent observability content requires `READ UNREDACTED AI OBSERVABILITY EVENTS TABLE` to see prompts and responses. — [Monitor agents](https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-agents-monitor)
- Cross-region inference doesn't persist prompts in the processing region. `DISABLED` keeps processing in the home region, which limits models. — [Cross-region inference](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cross-region-inference)
- Summit 2026 added the Trust Center AI Security Package, data-movement policies limiting agent actions, multi-party approvals, and agent identity. — [IT Brief](https://itbrief.com.au/story/snowflake-renames-ai-tools-amid-broader-platform-push)

### Inferences
- **Demo governance story:**
  - Tag FHIR-derived columns (name, DOB, MRN, address) via a classification profile, with tag-based masking for analytics roles.
  - Add a row access policy so a provider org sees only its patients and a payer sees only its members (via a `member.payer_id` mapping table).
  - Use ACCESS_HISTORY to audit who viewed which PA. Set `CORTEX_ENABLED_CROSS_REGION='AWS_US'` to keep inference in the US.
  - Use a custom classification category for MRN and member ID.
  - Note that agent tools run under caller rights, so policies apply to agent queries.

### Gaps
- There is no Snowflake doc confirming that Cortex AI (LLM) features or cross-region inference are in scope of Snowflake's HIPAA BAA. Verify with the Snowflake compliance or Trust portal.
- I didn't fetch ACCESS_HISTORY or Trust Center scanner docs, or `SYSTEM$CLASSIFY` legacy syntax.

---

## 10. Healthcare resources, quickstarts, hackathon criteria

### Takeaway
Relevant Snowflake material exists:
- A payer contact-center Cortex Agent quickstart.
- A FHIR JSON processing quickstart.
- An HL7 data-product guide.

I found no Snowflake prior-authorization quickstart. Public hackathon judging criteria are generic or old.

### Cited Findings
- The "AI Agent for Health Payers Contact Center" guide covers Cortex Agents, Search, Analyst, Complete, ML classification, Notebooks (container runtime), and Streamlit. It uses Whisper rather than AI_TRANSCRIBE. — [Guide](https://www.snowflake.com/en/developers/guides/ai-agent-health-payers-cc/); [repo](https://github.com/Snowflake-Labs/sfguide-ai-agent-hcls-payers-cc-cortex-notebooks-mlclassification/tree/main)
- There is also a "Building an AI agent for healthcare in Snowflake" solutions-center entry. — [Solutions Center](https://www.snowflake.com/en/developers/solutions-center/building-an-ai-agent-for-healthcare-in-snowflake/)
- FHIR quickstart: see section 5. — [Guide](https://www.snowflake.com/en/developers/guides/processing-hl7-fhir-messages-with-snowflake/)
- The Snowflake AI Hackathon (London, Feb 24, 2026) focused on data agents and Snowflake Intelligence, AI SQL plus Document AI, and Streamlit. No judging criteria or winners were published. — [Event page](https://www.snowflake.com/event/ai-hackathon-2026-02-24)
- The only official rules page found is the 2023 Streamlit hackathon. Judging centered on building a Streamlit app that uses Snowflake, with special consideration for Snowpark use. — [Official rules](https://www.snowflake.com/legal/snowflake-hackathon-official-rules/)
- Partner hackathons exist (Snowflake x Accenture, x Capgemini). I didn't extract their criteria. — [Accenture](https://www.snowflake.com/snowflake-x-accenture-hackathon); [Capgemini](https://www.snowflake.com/snowflake-x-capgemini-hackathon/)
- Regulatory context: the CMS-0057-F prior authorization API workflow and the Da Vinci PAS IG. — [CMS PDF](https://www.cms.gov/files/document/prior-authorization-api-workflow-cms-0057-f.pdf); [Da Vinci PAS](https://hl7.org/fhir/us/davinci-pas/specification.html)

### Inferences
- Judges at Snowflake hackathons typically reward deep, native use of current flagship features: Cortex Agents, Search, Analyst, CoWork, AI SQL, and app hosting on Snowflake. Prioritize visible use of agents with citations, semantic views, evaluations or observability, and governance.

### Gaps
- I found no published judging rubric for the user's specific hackathon, and no prior winning healthcare projects.
- I found no Marketplace FHIR listings or prior-authorization-specific Snowflake quickstart, though the search was limited.
