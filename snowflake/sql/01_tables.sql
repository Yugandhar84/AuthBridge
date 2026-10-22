-- =============================================================================
-- AuthBridge 01 — tables and sequences
-- Schema layout (refines PRD section 10): CORE holds the EHR chart, PAYER holds
-- everything the payer owns (rules, requests, decisions), AI holds retrieval
-- data and the append-only audit.
-- =============================================================================
USE ROLE AUTHBRIDGE_ADMIN;
USE DATABASE AUTHBRIDGE;
USE WAREHOUSE AUTHBRIDGE_APP_WH;

-- ---------------------------------------------------------------- RAW
CREATE TABLE IF NOT EXISTS RAW.FHIR_RAW_BUNDLES (
  payload_id         STRING DEFAULT UUID_STRING(),
  correlation_id     STRING,          -- hookInstance, Bundle.identifier, pa_id
  direction          STRING,          -- IN | OUT
  endpoint           STRING,          -- order-sign, $questionnaire-package, Claim/$submit, notification
  resource_type      STRING,
  payload            VARIANT,
  validation_status  STRING,
  validation_outcome VARIANT,
  received_at        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------- CORE (EHR chart)
CREATE TABLE IF NOT EXISTS CORE.PATIENT (
  patient_id STRING PRIMARY KEY, mrn STRING, given STRING, family STRING, birth_date DATE, gender STRING,
  city STRING, state STRING, problems ARRAY, demo_scenario STRING, suggested_order STRING, suggested_reason STRING,
  fhir VARIANT
);
CREATE TABLE IF NOT EXISTS CORE.COVERAGE (
  coverage_id STRING PRIMARY KEY, patient_id STRING, payer_id STRING, member_id STRING, plan_id STRING,
  status STRING, period_start DATE, period_end DATE, fhir VARIANT
);
CREATE TABLE IF NOT EXISTS CORE.PRACTITIONER (
  practitioner_role_id STRING PRIMARY KEY, practitioner_id STRING, npi STRING, name STRING, specialty STRING
);
CREATE TABLE IF NOT EXISTS CORE.CLINICAL_DOCUMENT (
  doc_id STRING PRIMARY KEY, patient_id STRING, note_type STRING, encounter_date DATE, author_npi STRING,
  title STRING, text STRING, attach_on_request BOOLEAN DEFAULT FALSE, stage_path STRING
);
ALTER TABLE CORE.CLINICAL_DOCUMENT SET CHANGE_TRACKING = TRUE;   -- Cortex Search source

-- ---------------------------------------------------------------- PROVIDER (EHR workflow)
CREATE TABLE IF NOT EXISTS PROVIDER.EHR_ORDER (
  order_id STRING PRIMARY KEY, patient_id STRING, status STRING, data VARIANT,
  updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------- PAYER
CREATE TABLE IF NOT EXISTS PAYER.PAYER_PLAN (
  plan_id STRING PRIMARY KEY, payer_id STRING, plan_name STRING,
  line_of_business STRING,             -- MA | MEDICAID | CHIP | QHP_FFE | COMMERCIAL
  cms_0057_applies BOOLEAN
);
CREATE TABLE IF NOT EXISTS PAYER.MEMBER_ELIGIBILITY (
  member_id STRING, plan_id STRING, patient_id STRING, eff_start DATE, eff_end DATE, status STRING,
  PRIMARY KEY (member_id, plan_id, eff_start)
);
CREATE TABLE IF NOT EXISTS PAYER.SERVICE_PA_RULES (
  rule_id STRING PRIMARY KEY, plan_id STRING,      -- NULL plan_id = applies to every plan
  service_code STRING, code_system STRING, description STRING, place_of_service STRING,
  pa_required BOOLEAN, doc_required BOOLEAN, questionnaire_id STRING, policy_doc_id STRING,
  gold_card_eligible BOOLEAN, expedited_allowed BOOLEAN, effective_from DATE, effective_to DATE, version STRING
);
CREATE TABLE IF NOT EXISTS PAYER.QUESTIONNAIRE (
  questionnaire_id STRING, version STRING, canonical_url STRING, title STRING, fhir VARIANT, libraries VARIANT,
  PRIMARY KEY (questionnaire_id, version)
);
CREATE TABLE IF NOT EXISTS PAYER.POLICY_CRITERIA (
  policy_doc_id STRING, version STRING, node_id STRING, parent_node_id STRING,
  node_type STRING,                    -- AND | OR | LEAF
  label STRING, fact_name STRING, operator STRING, threshold VARIANT,
  on_not_met STRING,                   -- PEND | RECOMMEND_DENY (what a NOT_MET leaf can lead to)
  policy_section_id STRING, sort_order NUMBER,
  PRIMARY KEY (policy_doc_id, version, node_id)
);
CREATE TABLE IF NOT EXISTS PAYER.GOLD_CARD_STATUS (
  ordering_npi STRING, service_code STRING, window_start DATE, window_end DATE, total_requests INT, approved INT,
  approval_rate FLOAT, threshold FLOAT, status STRING /* GOLD | NEAR | NONE */, satisfied_pa_prefix STRING,
  PRIMARY KEY (ordering_npi, service_code)
);
CREATE TABLE IF NOT EXISTS PAYER.CRD_RESPONSE (
  coverage_assertion_id STRING, hook STRING, member_id STRING, patient_id STRING, service_code STRING,
  ordering_npi STRING, result VARIANT, created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
CREATE TABLE IF NOT EXISTS PAYER.PA_REQUEST (
  pa_id STRING PRIMARY KEY, claim_id STRING, patient_id STRING, member_id STRING, plan_id STRING,
  line_of_business STRING, ordering_npi STRING, provider_org_npi STRING, service_code STRING, code_system STRING,
  service_display STRING, policy_doc_id STRING, questionnaire_id STRING, icd10_codes ARRAY,
  priority STRING /* standard | expedited */, coverage_assertion_id STRING,
  status STRING /* APPROVED | PENDED | CLINICIAN_REVIEW | DENIED */,
  recommendation STRING /* AUTO_APPROVE | PEND | RECOMMEND_DENY */, reason_text STRING,
  missing_info ARRAY, unmet ARRAY, criteria VARIANT, admin_ref STRING, version INT DEFAULT 1,
  submitted_at TIMESTAMP_NTZ, sla_due_at TIMESTAMP_NTZ, updated_at TIMESTAMP_NTZ,
  is_historical BOOLEAN DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS PAYER.QUESTIONNAIRE_RESPONSE (
  qr_id STRING DEFAULT UUID_STRING(), pa_id STRING, version INT, answers VARIANT, ai_prefill_pct FLOAT,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
CREATE TABLE IF NOT EXISTS PAYER.SUBMITTED_DOCUMENT (
  pa_id STRING, doc_id STRING, title STRING, encounter_date DATE, text STRING,
  received_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), PRIMARY KEY (pa_id, doc_id)
);
ALTER TABLE PAYER.SUBMITTED_DOCUMENT SET CHANGE_TRACKING = TRUE;   -- Cortex Search source
CREATE TABLE IF NOT EXISTS PAYER.DECISION (
  decision_id STRING DEFAULT UUID_STRING(), pa_id STRING, review_action_code STRING /* A1|A3|A4|A6 */,
  auth_number STRING, admin_ref_number STRING, auth_period_start DATE, auth_period_end DATE,
  reason_text STRING, request_text STRING, decided_by STRING /* SYSTEM or user */, decider_role STRING,
  ai_assisted BOOLEAN DEFAULT TRUE, decided_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
CREATE TABLE IF NOT EXISTS PAYER.APPEAL (
  appeal_id STRING DEFAULT UUID_STRING(), pa_id STRING, filed_at TIMESTAMP_NTZ, letter STRING,
  outcome STRING /* UPHELD | OVERTURNED | PENDING */, resolved_at TIMESTAMP_NTZ
);
CREATE TABLE IF NOT EXISTS PAYER.SUBSCRIPTION (
  subscription_id STRING PRIMARY KEY, org_identifier STRING, endpoint STRING, status STRING, fhir VARIANT,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------- AI
CREATE TABLE IF NOT EXISTS AI.APP_CONFIG (key STRING PRIMARY KEY, value STRING);
CREATE TABLE IF NOT EXISTS AI.POLICY_DOC_CHUNKS (
  chunk_id STRING PRIMARY KEY, policy_doc_id STRING, payer_id STRING, service_code STRING, section_id STRING,
  section_title STRING, effective_date DATE, chunk_text STRING
);
ALTER TABLE AI.POLICY_DOC_CHUNKS SET CHANGE_TRACKING = TRUE;
CREATE TABLE IF NOT EXISTS AI.CLINICAL_REVIEW (            -- one row per criterion per request version
  review_id STRING DEFAULT UUID_STRING(), pa_id STRING, version INT, node_id STRING, node_type STRING, label STRING,
  fact_name STRING, fact_value VARIANT, status STRING /* MET | NOT_MET | UNKNOWN */, evidence_quote STRING,
  evidence_doc_id STRING, policy_section_id STRING, citation_verified BOOLEAN, origin STRING,
  reviewer_override STRING, override_reason STRING, override_by STRING, override_at TIMESTAMP_NTZ
);
CREATE TABLE IF NOT EXISTS AI.AI_REVIEW_RESULT (            -- independent AI cross-check of provider answers
  pa_id STRING, version INT, fact_name STRING, provider_value VARIANT, ai_value VARIANT, quote STRING, doc_id STRING,
  citation_verified BOOLEAN, agrees BOOLEAN, model STRING, created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
CREATE TABLE IF NOT EXISTS AI.AI_RECOMMENDATION_AUDIT (     -- append-only; grant INSERT only to service roles
  audit_id STRING DEFAULT UUID_STRING(), pa_id STRING, agent_name STRING, model STRING, policy_version STRING,
  input_hash STRING, prompt_id STRING, output VARIANT, recommendation STRING, confidence STRING,
  ai_assisted BOOLEAN DEFAULT TRUE, human_actor STRING, created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------- sequences
CREATE SEQUENCE IF NOT EXISTS PAYER.SEQ_ASSERTION START = 1000;
CREATE SEQUENCE IF NOT EXISTS PAYER.SEQ_PA START = 1000;
CREATE SEQUENCE IF NOT EXISTS PAYER.SEQ_AUTH START = 50000;
CREATE SEQUENCE IF NOT EXISTS PAYER.SEQ_REF START = 70000;
