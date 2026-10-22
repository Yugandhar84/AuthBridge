-- =============================================================================
-- AuthBridge 08 — Cortex Agents (PRD section 8.4)
-- Agent spec fields follow the "Create and manage agents" docs as researched in
-- Oct 2026. Run these one at a time and check each against the current docs;
-- the spec format is the most likely thing to need small fixes.
-- The local payer service calls them through the REST API:
--   POST /api/v2/databases/AUTHBRIDGE/schemas/AI/agents/<NAME>:run
-- =============================================================================
USE ROLE AUTHBRIDGE_ADMIN;
USE DATABASE AUTHBRIDGE;
USE SCHEMA AI;
USE WAREHOUSE AUTHBRIDGE_AI_WH;

-- A3 Analytics Agent: natural-language questions over PA metrics.
CREATE OR REPLACE AGENT AI.ANALYTICS_AGENT
  COMMENT = 'AuthBridge analytics: PA volumes, SLA compliance, approval and denial rates, gold card'
  FROM SPECIFICATION
$$
models:
  orchestration: auto
instructions:
  response: >
    Answer questions about prior authorization operations for Demo Health Plan using only the
    pa_metrics tool. State the time window and filters you used. Show rates as percentages with
    one decimal. Data is synthetic. Do not speculate about individual patients.
  orchestration: >
    Use pa_metrics for every quantitative question. Use data_to_chart when a trend or comparison
    across more than three groups is requested.
  sample_questions:
    - question: "What share of expedited requests met the 72-hour limit last month, by service?"
    - question: "Which services have the highest auto-approval rate?"
    - question: "Which ordering practitioners are close to gold-card status for lumbar MRI?"
tools:
  - tool_spec:
      type: cortex_analyst_text_to_sql
      name: pa_metrics
      description: "Prior authorization requests, decisions, SLA compliance, approval/denial and appeal metrics."
  - tool_spec:
      type: data_to_chart
      name: data_to_chart
      description: "Draws a chart from query results."
tool_resources:
  pa_metrics:
    semantic_view: "AUTHBRIDGE.ANALYTICS.PA_METRICS_SV"
    execution_environment:
      type: warehouse
      warehouse: AUTHBRIDGE_AI_WH
$$;

-- A2 Clinical Review Agent: explains one case to a reviewer, with citations.
-- It never decides: the recommendation comes from the criteria engine.
CREATE OR REPLACE AGENT AI.CLINICAL_REVIEW_AGENT
  COMMENT = 'Explains a PA case criterion by criterion with policy and chart citations'
  FROM SPECIFICATION
$$
models:
  orchestration: auto
orchestration:
  budget:
    seconds: 60
    tokens: 16000
instructions:
  orchestration: >
    The user message names one prior authorization request (pa_id). Always call get_case first.
    Then search policy text with policy_search filtered to the case's policy_doc_id, and search the
    submitted records with submitted_docs filtered to the pa_id. Never search other patients' records.
  response: >
    Report the recommendation exactly as stored in the case. For each criterion give its status,
    the verbatim evidence quote with its document id, and the policy section id. If something is
    unknown, say exactly which document would resolve it. Never state that a request is denied;
    use "Recommend deny – requires clinician review" when that is the stored recommendation.
tools:
  - tool_spec:
      type: generic
      name: get_case
      description: "Returns the stored case: request, criteria results with evidence, and decisions."
      input_schema:
        type: object
        properties:
          pa_id: { type: string, description: "Prior authorization id, e.g. PA-1001" }
        required: [pa_id]
  - tool_spec:
      type: cortex_search
      name: policy_search
      description: "Demo Health Plan medical policy sections."
  - tool_spec:
      type: cortex_search
      name: submitted_docs
      description: "Clinical documents submitted with a PA request. Filter by pa_id."
tool_resources:
  get_case:
    type: procedure
    identifier: "AUTHBRIDGE.AI.SP_GET_CASE"
    execution_environment:
      type: warehouse
      warehouse: AUTHBRIDGE_AI_WH
  policy_search:
    search_service: "AUTHBRIDGE.AI.POLICY_SEARCH"
    id_column: "CHUNK_ID"
    title_column: "SECTION_TITLE"
    max_results: 5
  submitted_docs:
    search_service: "AUTHBRIDGE.AI.SUBMITTED_DOCS_SEARCH"
    id_column: "DOC_ID"
    title_column: "TITLE"
    max_results: 5
$$;

-- A4 Denial Explainer / Appeal Agent: drafts letters from stored facts only.
CREATE OR REPLACE AGENT AI.DENIAL_APPEAL_AGENT
  COMMENT = 'Drafts specific denial explanations (payer) and appeal letters (provider)'
  FROM SPECIFICATION
$$
models:
  orchestration: auto
instructions:
  orchestration: >
    Call get_case for the pa_id in the message. Use policy_search for the exact policy wording.
  response: >
    Write a plain-language letter. Every code, date, member id and criterion must come from get_case;
    never invent them. Name each unmet criterion, the documented value, the policy section, and what
    documentation would satisfy it. State that a licensed clinician made any denial and that AI only
    organised the evidence. Include appeal rights. End with "Draft – review before sending".
tools:
  - tool_spec:
      type: generic
      name: get_case
      description: "Returns the stored case: request, criteria results with evidence, and decisions."
      input_schema:
        type: object
        properties:
          pa_id: { type: string }
        required: [pa_id]
  - tool_spec:
      type: cortex_search
      name: policy_search
      description: "Demo Health Plan medical policy sections."
tool_resources:
  get_case:
    type: procedure
    identifier: "AUTHBRIDGE.AI.SP_GET_CASE"
    execution_environment:
      type: warehouse
      warehouse: AUTHBRIDGE_AI_WH
  policy_search:
    search_service: "AUTHBRIDGE.AI.POLICY_SEARCH"
    id_column: "CHUNK_ID"
    title_column: "SECTION_TITLE"
    max_results: 5
$$;

-- A1 DTR Auto-fill Agent (chat form). The app's auto-fill uses
-- AI.SP_DTR_AUTOFILL directly for predictable latency; this agent supports
-- "ask the chart" questions in Snowflake CoWork or a future UI panel.
CREATE OR REPLACE AGENT AI.DTR_AUTOFILL_AGENT
  COMMENT = 'Answers documentation questions from one patient''s chart with verbatim quotes'
  FROM SPECIFICATION
$$
models:
  orchestration: auto
instructions:
  orchestration: >
    Always filter clinical_notes by the patient_id named in the message. Never return information
    about any other patient.
  response: >
    Answer only from retrieved notes and quote them verbatim with the document id. If the chart does
    not answer the question, say so and suggest which record would.
tools:
  - tool_spec:
      type: cortex_search
      name: clinical_notes
      description: "The patient's clinical notes. Filter by patient_id."
tool_resources:
  clinical_notes:
    search_service: "AUTHBRIDGE.AI.CLINICAL_NOTES_SEARCH"
    id_column: "DOC_ID"
    title_column: "TITLE"
    max_results: 6
$$;

-- Optional stretch (PRD 8.7): expose the review agent and policy search over the
-- Snowflake-managed MCP server for agent-to-agent experiments.
-- CREATE OR REPLACE MCP SERVER AI.AUTHBRIDGE_MCP FROM SPECIFICATION $$ ... $$;
