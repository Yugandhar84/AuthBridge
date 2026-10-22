export type Practitioner = {
  practitioner_role_id: string;
  npi: string;
  name: string;
  specialty: string;
};

export type CatalogItem = {
  code: string;
  code_system: string;
  display: string;
  resource_type: "ServiceRequest" | "MedicationRequest";
  category: string;
};

export type Coverage = { coverage_id: string; member_id: string; plan_id: string; period_start: string; period_end: string };

export type OrderSummary = {
  order_id: string;
  patient_id: string;
  code: string;
  display: string;
  status: string;
  created_at: string;
  updated_at: string;
  review_action?: string | null;
  auth_number?: string | null;
};

export type Patient = {
  patient_id: string;
  mrn: string;
  given: string;
  family: string;
  birth_date: string;
  gender: string;
  city?: string;
  state?: string;
  problems: string[];
  scenario: string;
  suggested_order: string;
  suggested_reason: string;
  coverage: Coverage;
  latest_order?: OrderSummary | null;
};

export type Note = {
  doc_id: string;
  note_type: string;
  encounter_date: string;
  title: string;
  text: string;
};

export type PatientDetail = Patient & {
  notes: Note[];
  pending_documents: { doc_id: string; title: string; note_type: string; encounter_date: string }[];
  orders: OrderSummary[];
};

export type CoverageInfo = {
  covered?: string;
  pa_needed?: string;
  doc_needed?: string;
  questionnaire_url?: string;
  coverage_assertion_id?: string;
  satisfied_pa_id?: string;
  reason_code?: string;
  reason_text?: string;
};

export type Answer = {
  value: string | number | boolean;
  quote?: string;
  doc_id?: string;
  doc_title?: string;
  confidence?: string;
  origin: "auto" | "override" | "manual";
  replaced_ai_value?: unknown;
};

export type QItem = {
  linkId: string;
  text?: string;
  type: string;
  readOnly?: boolean;
  item?: QItem[];
};

export type Criterion = {
  node_id: string;
  parent_node_id: string | null;
  node_type: "AND" | "OR" | "LEAF";
  label: string;
  fact_name?: string | null;
  operator?: string | null;
  threshold?: unknown;
  on_not_met?: string | null;
  policy_section_id: string;
  depth: number;
  status: "MET" | "NOT_MET" | "UNKNOWN";
  value?: unknown;
  quote?: string | null;
  doc_id?: string | null;
  citation_verified?: boolean;
  origin?: string | null;
  reviewer_override?: string | null;
  override_reason?: string | null;
};

export type Completeness = {
  recommendation: "AUTO_APPROVE" | "PEND" | "RECOMMEND_DENY";
  reason_text: string;
  missing_info: string[];
  unmet: string[];
  criteria: Criterion[];
};

export type Exchange = {
  at: string;
  endpoint: string;
  status: number;
  ms?: number;
  request: unknown;
  response: unknown;
};

export type Order = OrderSummary & {
  practitioner_role_id: string;
  resource_type: string;
  form: Record<string, unknown>;
  resource: Record<string, unknown>;
  crd?: { coverage_information: CoverageInfo | null; cards: { summary: string; detail?: string; indicator: string; links?: { label: string; url: string }[] }[] };
  dtr?: {
    questionnaire: { id: string; title: string; item: QItem[] };
    prefilled: Record<string, unknown>;
    answers: Record<string, Answer>;
    completeness?: Completeness | null;
    attached_doc_ids: string[];
    rejected_ai_answers?: string[];
  };
  pas?: {
    claim_id: string;
    pa_id: string;
    review_action: string;
    review_action_display?: string;
    auth_number?: string;
    admin_ref?: string;
    period?: { start?: string; end?: string };
    reason_text?: string;
    request_text?: string;
  };
  timeline?: { at: string; label: string; detail?: string }[];
  exchanges?: Exchange[];
  appeal_draft?: string;
};

export type QueueRow = {
  pa_id: string;
  member_id: string;
  patient_id: string;
  service_code: string;
  service_display: string;
  priority: string;
  status: string;
  recommendation: string;
  submitted_at: string;
  sla_due_at: string;
  ordering_npi: string;
  line_of_business: string;
};

export type Case = {
  request: QueueRow & {
    reason_text?: string;
    missing_info?: string[];
    unmet?: string[];
    policy_doc_id?: string;
    version?: number;
    icd10_codes?: string[];
    admin_ref?: string;
  };
  criteria: Criterion[];
  answers: Record<string, Answer>;
  documents: { doc_id: string; title?: string; encounter_date?: string; text: string }[];
  decisions: { review_action_code: string; decided_by: string; decider_role: string; reason_text?: string; request_text?: string; decided_at: string; auth_number?: string }[];
  audit: { agent_name: string; model?: string; recommendation?: string; human_actor?: string; created_at: string }[];
  policy_sections: { section_id: string; section_title: string; text: string }[];
  ai_cross_check?: { fact_name: string; provider_value: unknown; ai_value: unknown; agrees: boolean | null; quote?: string }[];
};

export type Metrics = {
  total_requests: number;
  decided: number;
  approval_rate: number | null;
  denial_rate: number | null;
  auto_approval_rate: number | null;
  median_hours_to_decision: number | null;
  median_hours_standard: number | null;
  median_hours_expedited: number | null;
  sla_compliance: number | null;
  open_clinician_reviews: number;
  open_pends: number;
  appeal_overturn_rate: number | null;
  by_service: { service_code: string; service_display: string; requests: number; approved: number; denied: number; auto_approved: number }[];
  gold_card: { ordering_npi: string; service_code: string; approval_rate: number; status: string; total_requests: number }[];
};
