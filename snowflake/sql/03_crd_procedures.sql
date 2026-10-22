-- =============================================================================
-- AuthBridge 03 — CRD rules in Snowflake Scripting (no LLM on this path, FR-3.6)
-- Called by the local payer service on every order-select / order-sign hook.
-- Returns the values the service turns into the CRD coverage-information
-- extension.
-- =============================================================================
USE ROLE AUTHBRIDGE_ADMIN;
USE DATABASE AUTHBRIDGE;
USE WAREHOUSE AUTHBRIDGE_APP_WH;

CREATE OR REPLACE PROCEDURE PAYER.SP_CRD_EVALUATE(
    P_MEMBER_ID     STRING,
    P_PATIENT_ID    STRING,
    P_SERVICE_CODE  STRING,
    P_CODE_SYSTEM   STRING,
    P_ORDERING_NPI  STRING,
    P_HOOK          STRING)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
COMMENT = 'CRD: eligibility -> PA rule lookup -> gold card. Deterministic.'
AS
$$
DECLARE
  v_seq            NUMBER;
  v_assertion      STRING;
  v_member_found   NUMBER DEFAULT 0;
  v_plan_id        STRING;
  v_lob            STRING;
  v_rule_id        STRING;
  v_pa_required    BOOLEAN;
  v_doc_required   BOOLEAN;
  v_gold_eligible  BOOLEAN;
  v_qid            STRING;
  v_policy         STRING;
  v_q_url          STRING;
  v_gold_status    STRING;
  v_gold_prefix    STRING;
  v_result         VARIANT;
BEGIN
  SELECT PAYER.SEQ_ASSERTION.NEXTVAL INTO :v_seq;
  v_assertion := 'CA-' || TO_CHAR(CURRENT_DATE(), 'YYYYMMDD') || '-' || v_seq::STRING;

  -- 1. Eligibility
  SELECT COUNT(*) INTO :v_member_found FROM PAYER.MEMBER_ELIGIBILITY WHERE member_id = :P_MEMBER_ID;

  SELECT MAX(m.plan_id), MAX(p.line_of_business)
    INTO :v_plan_id, :v_lob
    FROM PAYER.MEMBER_ELIGIBILITY m
    JOIN PAYER.PAYER_PLAN p ON p.plan_id = m.plan_id
   WHERE m.member_id = :P_MEMBER_ID
     AND m.status = 'active'
     AND CURRENT_DATE() BETWEEN m.eff_start AND COALESCE(m.eff_end, '9999-12-31'::DATE);

  IF (v_member_found = 0) THEN
    SELECT OBJECT_CONSTRUCT('covered', 'not-covered', 'reason_text', 'No member found for this coverage',
                            'coverage_assertion_id', :v_assertion, 'date', TO_VARCHAR(CURRENT_DATE()))
      INTO :v_result;
  ELSEIF (v_plan_id IS NULL) THEN
    SELECT OBJECT_CONSTRUCT('covered', 'not-covered', 'reason_text', 'Coverage is not active on the date of service',
                            'coverage_assertion_id', :v_assertion, 'date', TO_VARCHAR(CURRENT_DATE()))
      INTO :v_result;
  ELSE
    -- 2. PA rule: a plan-specific rule wins over the all-plans rule
    SELECT MAX(rule_id) INTO :v_rule_id FROM (
      SELECT rule_id FROM PAYER.SERVICE_PA_RULES
       WHERE service_code = :P_SERVICE_CODE
         AND (plan_id = :v_plan_id OR plan_id IS NULL)
         AND CURRENT_DATE() >= effective_from
         AND (effective_to IS NULL OR CURRENT_DATE() <= effective_to)
       ORDER BY IFF(plan_id IS NULL, 1, 0)
       LIMIT 1);

    IF (v_rule_id IS NULL) THEN
      SELECT OBJECT_CONSTRUCT('covered', 'conditional', 'pa_needed', 'conditional',
                              'reason_text', 'Service not found in the plan''s prior authorization list; call the plan',
                              'plan_id', :v_plan_id, 'line_of_business', :v_lob,
                              'coverage_assertion_id', :v_assertion, 'date', TO_VARCHAR(CURRENT_DATE()))
        INTO :v_result;
    ELSE
      SELECT BOOLOR_AGG(pa_required), BOOLOR_AGG(doc_required), BOOLOR_AGG(gold_card_eligible),
             MAX(questionnaire_id), MAX(policy_doc_id)
        INTO :v_pa_required, :v_doc_required, :v_gold_eligible, :v_qid, :v_policy
        FROM PAYER.SERVICE_PA_RULES WHERE rule_id = :v_rule_id;

      IF (NOT v_pa_required) THEN
        SELECT OBJECT_CONSTRUCT('covered', 'covered', 'pa_needed', 'no-auth', 'rule_id', :v_rule_id,
                                'plan_id', :v_plan_id, 'line_of_business', :v_lob,
                                'coverage_assertion_id', :v_assertion, 'date', TO_VARCHAR(CURRENT_DATE()))
          INTO :v_result;
      ELSE
        -- 3. Gold card for the ordering practitioner
        SELECT MAX(status), MAX(satisfied_pa_prefix) INTO :v_gold_status, :v_gold_prefix
          FROM PAYER.GOLD_CARD_STATUS
         WHERE ordering_npi = :P_ORDERING_NPI AND service_code = :P_SERVICE_CODE;

        IF (v_gold_status = 'GOLD' AND v_gold_eligible) THEN
          SELECT OBJECT_CONSTRUCT('covered', 'covered', 'pa_needed', 'satisfied', 'reason_code', 'gold-card',
                                  'reason_text', 'Ordering practitioner holds a gold card for this service',
                                  'satisfied_pa_id', :v_gold_prefix || '-' || RIGHT(:v_assertion, 4),
                                  'rule_id', :v_rule_id, 'policy_doc_id', :v_policy,
                                  'plan_id', :v_plan_id, 'line_of_business', :v_lob,
                                  'coverage_assertion_id', :v_assertion, 'date', TO_VARCHAR(CURRENT_DATE()))
            INTO :v_result;
        ELSE
          SELECT MAX(canonical_url || '|' || version) INTO :v_q_url
            FROM PAYER.QUESTIONNAIRE WHERE questionnaire_id = :v_qid;
          SELECT OBJECT_CONSTRUCT('covered', 'covered', 'pa_needed', 'auth-needed',
                                  'doc_needed', IFF(:v_doc_required, 'clinical', NULL),
                                  'doc_purpose', IFF(:v_doc_required, 'withpa', NULL),
                                  'questionnaire_id', :v_qid, 'questionnaire_url', :v_q_url,
                                  'rule_id', :v_rule_id, 'policy_doc_id', :v_policy,
                                  'plan_id', :v_plan_id, 'line_of_business', :v_lob,
                                  'coverage_assertion_id', :v_assertion, 'date', TO_VARCHAR(CURRENT_DATE()))
            INTO :v_result;
        END IF;
      END IF;
    END IF;
  END IF;

  -- order-select SHALL NOT signal documentation needs (CRD 2.2)
  IF (P_HOOK = 'order-select') THEN
    SELECT OBJECT_DELETE(:v_result, 'doc_needed', 'doc_purpose', 'questionnaire_url') INTO :v_result;
  END IF;

  INSERT INTO PAYER.CRD_RESPONSE (coverage_assertion_id, hook, member_id, patient_id, service_code, ordering_npi, result)
    SELECT :v_assertion, :P_HOOK, :P_MEMBER_ID, :P_PATIENT_ID, :P_SERVICE_CODE, :P_ORDERING_NPI, :v_result;

  RETURN v_result;
END;
$$;

-- Smoke tests (expected: auth-needed, satisfied/gold-card, no-auth, not-covered)
-- CALL PAYER.SP_CRD_EVALUATE('M100002', 'pt-002', '72148', 'CPT', '1234567893', 'order-sign');
-- CALL PAYER.SP_CRD_EVALUATE('M100002', 'pt-002', '72148', 'CPT', '1477589632', 'order-sign');
-- CALL PAYER.SP_CRD_EVALUATE('M100002', 'pt-002', '72100', 'CPT', '1234567893', 'order-sign');
-- CALL PAYER.SP_CRD_EVALUATE('M100099', 'pt-099', '72148', 'CPT', '1234567893', 'order-sign');
