-- =============================================================================
-- AuthBridge 07 — analytics: fact view, CMS-style metrics, semantic view for
-- Cortex Analyst. Verify metric definitions against CMS-0057-F (42 CFR) before
-- labelling anything "CMS-compliant".
-- =============================================================================
USE ROLE AUTHBRIDGE_ADMIN;
USE DATABASE AUTHBRIDGE;
USE WAREHOUSE AUTHBRIDGE_AI_WH;

-- One row per PA request with its final (or latest) decision.
CREATE OR REPLACE VIEW ANALYTICS.V_PA_FACT AS
WITH latest AS (
  SELECT d.*, ROW_NUMBER() OVER (PARTITION BY d.pa_id ORDER BY d.decided_at DESC) AS rn
    FROM PAYER.DECISION d
), first_final AS (
  SELECT d.pa_id, MIN(d.decided_at) AS final_at
    FROM PAYER.DECISION d WHERE d.review_action_code IN ('A1', 'A3', 'A6') GROUP BY d.pa_id
), appeal AS (
  SELECT pa_id, MAX(outcome) AS appeal_outcome FROM PAYER.APPEAL GROUP BY pa_id
)
SELECT r.pa_id, r.member_id, r.plan_id, r.line_of_business, r.ordering_npi, r.service_code, r.service_display,
       r.policy_doc_id, r.priority, r.status, r.recommendation, r.submitted_at, r.sla_due_at, r.is_historical,
       l.review_action_code AS latest_action, l.decided_by AS latest_decided_by, l.decider_role AS latest_decider_role,
       f.final_at,
       IFF(f.final_at IS NULL, NULL, DATEDIFF(minute, r.submitted_at, f.final_at) / 60.0) AS hours_to_decision,
       IFF(f.final_at IS NULL, NULL, f.final_at <= r.sla_due_at)                          AS met_sla,
       l.review_action_code IN ('A1', 'A6') AND f.final_at IS NOT NULL                    AS is_approved,
       l.review_action_code = 'A3'                                                        AS is_denied,
       r.recommendation = 'AUTO_APPROVE' AND l.decided_by = 'SYSTEM'                      AS is_auto_approved,
       a.appeal_outcome IS NOT NULL                                                       AS was_appealed,
       a.appeal_outcome = 'OVERTURNED'                                                    AS overturned_on_appeal,
       DATE_TRUNC(month, r.submitted_at)                                                  AS submitted_month
  FROM PAYER.PA_REQUEST r
  LEFT JOIN latest l ON l.pa_id = r.pa_id AND l.rn = 1
  LEFT JOIN first_final f ON f.pa_id = r.pa_id
  LEFT JOIN appeal a ON a.pa_id = r.pa_id;

-- Headline metrics, the same numbers the payer dashboard shows.
CREATE OR REPLACE VIEW ANALYTICS.V_PA_METRICS AS
SELECT COUNT(*)                                                         AS total_requests,
       COUNT_IF(final_at IS NOT NULL)                                   AS decided,
       ROUND(COUNT_IF(is_approved) / NULLIF(COUNT_IF(final_at IS NOT NULL), 0), 3)       AS approval_rate,
       ROUND(COUNT_IF(is_denied) / NULLIF(COUNT_IF(final_at IS NOT NULL), 0), 3)         AS denial_rate,
       ROUND(COUNT_IF(is_auto_approved) / NULLIF(COUNT_IF(final_at IS NOT NULL), 0), 3)  AS auto_approval_rate,
       ROUND(MEDIAN(hours_to_decision), 2)                              AS median_hours_to_decision,
       ROUND(MEDIAN(IFF(priority = 'standard', hours_to_decision, NULL)), 2)  AS median_hours_standard,
       ROUND(MEDIAN(IFF(priority = 'expedited', hours_to_decision, NULL)), 2) AS median_hours_expedited,
       ROUND(COUNT_IF(met_sla) / NULLIF(COUNT_IF(final_at IS NOT NULL), 0), 3)            AS sla_compliance,
       COUNT_IF(status = 'CLINICIAN_REVIEW')                            AS open_clinician_reviews,
       COUNT_IF(status = 'PENDED')                                      AS open_pends,
       ROUND(COUNT_IF(overturned_on_appeal) / NULLIF(COUNT_IF(was_appealed), 0), 3)       AS appeal_overturn_rate
  FROM ANALYTICS.V_PA_FACT;

CREATE OR REPLACE VIEW ANALYTICS.V_PA_BY_SERVICE AS
SELECT service_code, ANY_VALUE(service_display) AS service_display, COUNT(*) AS requests,
       COUNT_IF(is_approved) AS approved, COUNT_IF(is_denied) AS denied, COUNT_IF(is_auto_approved) AS auto_approved
  FROM ANALYTICS.V_PA_FACT GROUP BY service_code ORDER BY requests DESC;

-- ---------------------------------------------------------------------------
-- Semantic view for the Analytics Agent (Cortex Analyst). Check the clause
-- syntax against the current CREATE SEMANTIC VIEW docs on day 1.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE SEMANTIC VIEW ANALYTICS.PA_METRICS_SV
  TABLES (
    pa AS ANALYTICS.V_PA_FACT PRIMARY KEY (pa_id)
      WITH SYNONYMS = ('prior authorization', 'PA request', 'authorization request')
      COMMENT = 'One row per prior authorization request with its decision outcome'
  )
  FACTS (
    pa.hours_to_decision AS pa.hours_to_decision COMMENT = 'Hours from submission to the first final decision (A1/A3/A6)',
    pa.decided_flag      AS IFF(pa.final_at IS NOT NULL, 1, 0),
    pa.approved_flag     AS IFF(pa.is_approved, 1, 0),
    pa.denied_flag       AS IFF(pa.is_denied, 1, 0),
    pa.auto_flag         AS IFF(pa.is_auto_approved, 1, 0),
    pa.met_sla_flag      AS IFF(pa.met_sla, 1, 0),
    pa.appealed_flag     AS IFF(pa.was_appealed, 1, 0),
    pa.overturned_flag   AS IFF(pa.overturned_on_appeal, 1, 0)
  )
  DIMENSIONS (
    pa.service_code     AS pa.service_code WITH SYNONYMS = ('CPT', 'HCPCS', 'service') COMMENT = 'Requested service code',
    pa.service_display  AS pa.service_display COMMENT = 'Service description',
    pa.priority         AS pa.priority WITH SYNONYMS = ('urgency') COMMENT = 'standard (7-day) or expedited (72-hour)',
    pa.line_of_business AS pa.line_of_business COMMENT = 'MA, MEDICAID, CHIP, QHP_FFE or COMMERCIAL',
    pa.ordering_npi     AS pa.ordering_npi WITH SYNONYMS = ('provider', 'physician', 'NPI') COMMENT = 'Ordering practitioner NPI',
    pa.status           AS pa.status COMMENT = 'APPROVED, PENDED, CLINICIAN_REVIEW or DENIED',
    pa.recommendation   AS pa.recommendation COMMENT = 'Engine recommendation: AUTO_APPROVE, PEND or RECOMMEND_DENY',
    pa.submitted_month  AS pa.submitted_month COMMENT = 'Month the request was submitted',
    pa.submitted_at     AS pa.submitted_at COMMENT = 'Submission timestamp'
  )
  METRICS (
    pa.request_count            AS COUNT(pa.pa_id) COMMENT = 'Number of PA requests',
    pa.approval_rate            AS SUM(pa.approved_flag) / NULLIF(SUM(pa.decided_flag), 0) COMMENT = 'Share of decided requests approved',
    pa.denial_rate              AS SUM(pa.denied_flag) / NULLIF(SUM(pa.decided_flag), 0) COMMENT = 'Share of decided requests denied',
    pa.auto_approval_rate       AS SUM(pa.auto_flag) / NULLIF(SUM(pa.decided_flag), 0) COMMENT = 'Share approved in real time with no human',
    pa.sla_compliance           AS SUM(pa.met_sla_flag) / NULLIF(SUM(pa.decided_flag), 0) COMMENT = 'Share decided within 72h (expedited) or 7 days (standard)',
    pa.median_hours_to_decision AS MEDIAN(pa.hours_to_decision) COMMENT = 'Median hours to a final decision',
    pa.appeal_overturn_rate     AS SUM(pa.overturned_flag) / NULLIF(SUM(pa.appealed_flag), 0) COMMENT = 'Share of appealed denials overturned'
  )
  COMMENT = 'AuthBridge prior authorization metrics (synthetic data)';
