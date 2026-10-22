-- =============================================================================
-- AuthBridge 06 — event-driven work that must NOT sit on the order-sign path:
-- AI cross-check of new/updated requests, and gold-card candidate refresh.
-- =============================================================================
USE ROLE AUTHBRIDGE_ADMIN;
USE DATABASE AUTHBRIDGE;
USE WAREHOUSE AUTHBRIDGE_AI_WH;

CREATE OR REPLACE STREAM PAYER.PA_REQUEST_STREAM ON TABLE PAYER.PA_REQUEST APPEND_ONLY = FALSE;

CREATE TABLE IF NOT EXISTS AI.AI_REVIEW_QUEUE (pa_id STRING, queued_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), done_at TIMESTAMP_NTZ);

-- Drains the stream (advancing its offset) and runs the AI cross-check for
-- requests that a human will look at (pended or clinician review).
CREATE OR REPLACE PROCEDURE AI.SP_PROCESS_REVIEW_QUEUE()
RETURNS STRING
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  n INTEGER DEFAULT 0;
  c1 CURSOR FOR SELECT DISTINCT pa_id FROM AI.AI_REVIEW_QUEUE WHERE done_at IS NULL;
BEGIN
  INSERT INTO AI.AI_REVIEW_QUEUE (pa_id)
    SELECT DISTINCT pa_id FROM PAYER.PA_REQUEST_STREAM
     WHERE METADATA$ACTION = 'INSERT' AND status IN ('PENDED', 'CLINICIAN_REVIEW') AND NOT is_historical;
  FOR rec IN c1 DO
    LET id STRING := rec.pa_id;
    CALL AI.SP_AI_REVIEW(:id);
    UPDATE AI.AI_REVIEW_QUEUE SET done_at = CURRENT_TIMESTAMP() WHERE pa_id = :id AND done_at IS NULL;
    n := n + 1;
  END FOR;
  RETURN 'reviewed ' || n;
END;
$$;

-- Triggered task: runs when the stream has data (no fixed schedule).
CREATE OR REPLACE TASK AI.T_AI_REVIEW
  WAREHOUSE = AUTHBRIDGE_AI_WH
  WHEN SYSTEM$STREAM_HAS_DATA('PAYER.PA_REQUEST_STREAM')
AS
  CALL AI.SP_PROCESS_REVIEW_QUEUE();

ALTER TASK AI.T_AI_REVIEW RESUME;

-- Rolling 12-month gold-card candidates from real decisions (FR-9.4).
-- Thresholds: 90% approval with at least 5 requests (TX-style); NEAR within 5 points.
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DT_GOLD_CARD_CANDIDATES
  TARGET_LAG = '1 hour'
  WAREHOUSE = AUTHBRIDGE_AI_WH
AS
WITH final AS (
  SELECT d.pa_id, d.review_action_code,
         ROW_NUMBER() OVER (PARTITION BY d.pa_id ORDER BY d.decided_at DESC) AS rn
    FROM PAYER.DECISION d
   WHERE d.review_action_code IN ('A1', 'A3', 'A6')
)
SELECT r.ordering_npi, r.service_code,
       COUNT(*)                                                         AS total_requests,
       COUNT_IF(f.review_action_code IN ('A1', 'A6'))                   AS approved,
       ROUND(COUNT_IF(f.review_action_code IN ('A1', 'A6')) / COUNT(*), 3) AS approval_rate,
       CASE WHEN COUNT(*) >= 5 AND COUNT_IF(f.review_action_code IN ('A1', 'A6')) / COUNT(*) >= 0.90 THEN 'GOLD'
            WHEN COUNT(*) >= 5 AND COUNT_IF(f.review_action_code IN ('A1', 'A6')) / COUNT(*) >= 0.85 THEN 'NEAR'
            ELSE 'NONE' END                                               AS candidate_status
  FROM PAYER.PA_REQUEST r
  JOIN final f ON f.pa_id = r.pa_id AND f.rn = 1
 WHERE r.submitted_at >= DATEADD(month, -12, CURRENT_TIMESTAMP())
 GROUP BY r.ordering_npi, r.service_code;

-- Optional: alert when an open request is within 12 hours of its CMS-0057-F deadline.
-- CREATE OR REPLACE ALERT ANALYTICS.A_SLA_AT_RISK
--   WAREHOUSE = AUTHBRIDGE_AI_WH SCHEDULE = '15 MINUTE'
--   IF (EXISTS (SELECT 1 FROM PAYER.PA_REQUEST WHERE status IN ('PENDED','CLINICIAN_REVIEW')
--               AND sla_due_at < DATEADD(hour, 12, CURRENT_TIMESTAMP())))
--   THEN CALL SYSTEM$SEND_EMAIL('<integration>', '<email>', 'AuthBridge: PA requests near deadline', 'Check the work queue.');
