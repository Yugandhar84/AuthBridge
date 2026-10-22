# AI/LLM Agents in Prior Authorization: Evidence, Rules, Public Medical Policy, Demo Scenarios and Responsible-AI Design

Scope: US context, current as of October 2026. Vendor claims are marked as such; they are unaudited marketing figures.

## 1. Documented uses and results of AI in PA (provider and payer side)

### Takeaway
Payer-side AI in production is overwhelmingly positioned as "approve fast, route everything else to a human": vendors report 75-96% real-time approval or recommendation rates, but none publish audited methodology. Academic LLM work shows strong results on criteria-vs-chart matching and letter drafting, with consistent weaknesses in citations, coding precision and administrative completeness, which argues for grounded, checklist-structured agents with human sign-off.

### Cited Findings
**Payer-side vendors**
- Cohere Health claims "85% of prior authorizations approved in real time with AI-powered intelligence" (varies by specialty; elsewhere on the page "50-90%" automation). Decisions are made against NCDs, LCDs, Cohere proprietary guidelines, plan policies and some third-party guidelines; uses "350+ AI/ML models"; cases that cannot be auto-approved go to clinical staff with AI-pre-structured clinical information. Page does not state whether AI ever denies. — [Cohere Health Decision](https://coherehealth.com/decision)
- Cohere processes ~5.5 million PA requests/yr (~15M members, 420,000 providers); integrated into Epic Payer Platform (April 2024) so clinicians start PA requests inside the EHR. — [Becker's](https://beckershospitalreview.com/ehrs/epic-cohere-expedite-prior-authorizations.html)
- Availity AuthAI: "Analytical AI, not generative AI"; encodes payer medical policy in Clinical Quality Language (CQL) for traceability/audit; "does not auto-deny, deny or approve prior authorizations" — "a recommendation engine, not a decisioning engine"; claims 75% of requests receive a near-real-time approval recommendation in <90 seconds on average; clinicians can override any recommendation; complex cases routed to humans with organized evidence. — [Availity AuthAI](https://www.availity.com/authai/)
- Optum (Feb 2026): provider-side Digital Auth Complete (Humata Health, EHR-embedded; gathers materials, applies payer rules, auto-submits) plus payer-side InterQual Auth Accelerator; Allina Health an early adopter. Vendor-touted results: 56% reduction in review time, 80% greater documentation bundling efficiency, 96% first-pass approval rate, "45% manual touches" (as reported, unclear framing). — [Healthcare Finance News](https://www.healthcarefinancenews.com/news/optum-introduces-ai-powered-digital-prior-authorization)
- Infinitus markets voice AI agents that make payer phone calls for PA follow-ups/status checks and appeals. — [Infinitus blog](https://www.infinitus.ai/blog/ai-agents-for-follow-up-calls-prior-authorizations-appeals-more/); [Infinitus PA solution](https://www.infinitus.ai/solutions/prior-authorization/)

**Provider/EHR side**
- Epic (Aug 2026) rolled out real-time Coverage Requirements Discovery (CRD) API checks in the EHR at Ochsner, Froedtert ThedaCare, Denver Health, Summit Health, with UnitedHealthcare, Network Health, Aetna and others; 16 more payers testing. No outcome data reported; article does not say CRD uses AI. — [Healthcare Finance News](https://www.healthcarefinancenews.com/news/epic-launches-real-time-prior-authorization-four-health-systems)
- Same article cites KFF: 2025 standard PA denial rates of 12% (Medicare Advantage), 14% (Medicaid managed care), 18% (ACA plans), many overturned on appeal. — [Healthcare Finance News](https://www.healthcarefinancenews.com/news/epic-launches-real-time-prior-authorization-four-health-systems)

**Government use**
- CMS WISeR model (Jan 1, 2026 - Dec 31, 2031) in AZ, NJ, OK, OH, TX, WA (~6.4M beneficiaries): contractors use technologies "such as artificial intelligence" to review PA requests for Traditional Medicare services (nerve stimulation, nerve tissue destruction, pain steroid injections, vertebral bone cement, cervical fusion, knee arthroscopy for OA, incontinence devices, impotence treatments, spinal decompression, skin substitutes). A human clinician must review every denial. Contractors are paid a percentage of the dollar value of denied requests, with penalties for denials overturned on appeal. Legislation introduced in the 119th Congress to block it. — [CRS In Focus IF13133 (May 2026)](https://www.everycrsreport.com/files/2026-05-12_IF13133_1b7af5c4cb1305bfa031b37cfcf21ca5739edb1a.html); concerns: [Georgetown CHIR](https://medicare.chir.georgetown.edu/new-cms-wiser-model-revives-concerns-of-prior-authorization-and-artificial-intelligence/)

**Academic studies**
- Multi-agent medical-necessity system (BioNLP 2024): retrieves top-k EHR sentences per checklist item, an Evidence Classification Agent labels sentences supporting/contradicting/irrelevant, a Jury Agent votes 10x for judgment + confidence, and a Propagator Agent rolls leaf judgments up a criteria tree. On ~300 synthetic sub-checklists for propagation: GPT-4 95.6% response accuracy, Claude 3 Opus 95.2%, GPT-3.5 91.2%, Mixtral 87.2%. Leaf-node evaluation was limited/ongoing. — [arXiv 2404.17977](https://arxiv.org/abs/2404.17977)
- GPT-4o, Claude Sonnet 4.5, Gemini 2.5 Pro on 45 physician-validated synthetic scenarios: strong clinical content in PA letters, but consistent administrative gaps (missing billing codes, no requested authorization duration, inadequate follow-up plans) not caught by clinical scoring. — [arXiv 2603.29366 (Mar 2026)](https://arxiv.org/abs/2603.29366)
- ChatGPT-5 nephrology PA letters (29 scenarios): 1/29 false statement (3.5%), 79.3% correct ICD-10 (CKD 3a vs 3b errors), 93.1% valid references, 89.7% strong reasoning; authors say clinician oversight "remains necessary." — [Frontiers in Digital Health 2026 via HMP](https://www.hmpgloballearningnetwork.com/site/frmc/news/large-language-model-shows-promise-nephrology-prior-authorization-letter-drafting)
- Radiotherapy appeal letters (WashU, medRxiv 2024): GPT-4 letters rated by blinded radiation oncologists as likely to expedite appeals in 100% of cases; GPT-4 > GPT-3.5 in reasoning; fine-tuned GPT-3.5 on only 53 letters was worse on every domain; all models were poor at citing accurate primary literature, and web search did not fix it. — [medRxiv 2024.04.30.24306634](https://medrxiv.org/content/10.1101/2024.04.30.24306634.full.pdf)

**Context on burden**
- AMA 2024 survey (Feb 2025): 61% of physicians worry payer AI is increasing PA denials; 39 PAs/physician/week; 13 hours/week; 29% report a serious adverse event; 93% report care delays. — [AMA press release](https://www.ama-assn.org/press-center/ama-press-releases/physicians-concerned-ai-increases-prior-authorization-denials)

### Inferences
- The dominant, regulator-tolerated industry pattern is asymmetric automation: auto-approve or recommend approval; never auto-deny. Availity explicitly brands itself as non-decisioning; the demo should copy this framing.
- Deterministic policy encoding (CQL/rules) plus LLM evidence extraction is the emerging architecture; the LLM finds and cites evidence, while rule logic decides whether criteria are met. This maps well to Snowflake: Cortex Search over notes/policies + Cortex LLM functions for extraction + SQL/Python rule evaluation.
- Letter-drafting studies show the biggest LLM failure modes are citations and administrative fields (codes, units, duration). Appeal/denial drafting should pull codes and citations from structured data and policy text, not from model memory.

### Gaps
- No independent, peer-reviewed measurement of auto-approval rates or accuracy for any commercial vendor was found; all rates above are vendor-reported.
- No peer-reviewed study found that measures LLM accuracy on real PA decisions vs. nurse/physician reviewers at scale.
- Epic's specific generative-AI PA questionnaire auto-fill features could not be verified from a primary source in this research pass.

## 2. Controversies and rules governing AI in PA

### Takeaway
Litigation (UnitedHealth/naviHealth nH Predict, Humana, Cigna PXDX) and the 2024 Senate PSI report created the regulatory consensus now codified in CMS MA rules and a fast-growing set of state laws: AI may assist and may support approvals, but any adverse medical-necessity determination must be individualized and made by a licensed clinician, with specific reasons and the criteria used. CMS-0057-F adds 72h/7-day deadlines and specific denial reasons from Jan 2026.

### Cited Findings
**Lawsuits and investigations**
- UnitedHealth/nH Predict (D. Minn., filed Nov 2023): alleges the naviHealth tool overrode physicians on post-acute care, with a ~90% reversal rate on appeal and ~0.2% of members appealing. Feb 2025: Judge Tunheim let breach of contract and implied covenant claims proceed and waived administrative exhaustion as "futile"; Mar 9, 2026: court compelled discovery on nH Predict design records and AI review board materials back to 2017. UnitedHealth says nH Predict "does not make coverage determinations." — [DistilInfo, Mar 2026](https://distilinfo.com/2026/03/12/court-orders-unitedhealth-to-disclose-ai-denial-algorithm/); [Skilled Nursing News, Feb 2025](https://skillednursingnews.com/2025/02/lawsuit-against-unitedhealth-over-ai-based-denials-of-post-acute-care-moves-ahead/)
- Humana class action (Dec 2023) alleges use of nH Predict to cut MA rehab care early, with "highly inaccurate" predictions used in place of doctors' recommendations; ~2% of members appeal. — [Healthcare Finance News](https://www.healthcarefinancenews.com/news/humana-sued-allegedly-using-ai-medicare-advantage-denials)
- Cigna PXDX (ProPublica, 2023): >300,000 claims denied over two months in 2022 at ~1.2 seconds per claim; Cigna disputes the characterization (post-service claims, not PA). Lawsuits followed. — [Becker's Payer](https://www.beckerspayer.com/payer/home-page/cigna-physicians-deny-claims-en-masse-without-reading-them-propublica-report.html); [Becker's: suits](https://www.beckerspayer.com/payer/lawsuits-pile-up-against-cigna-over-alleged-mass-claim-denials.html)
- Senate PSI majority staff report (Oct 2024): 2022 post-acute denial rates were ~3x overall at UnitedHealthcare and CVS and >16x at Humana; UnitedHealthcare denials rose alongside automated review systems. — [PSI report PDF](https://www.hsgac.senate.gov/wp-content/uploads/2024.10.17-PSI-Majority-Staff-Report-on-Medicare-Advantage.pdf); [Skilled Nursing News summary](https://skillednursingnews.com/2024/10/u-s-senate-subcommittee-cites-serious-concerns-on-medicare-advantages-denial-of-post-acute-care/)

**CMS Medicare Advantage rule (CMS-4201-F) and Feb 6, 2024 FAQ**
- MA plans may use algorithms/AI to assist coverage decisions (e.g., checking compliance with coverage criteria, facilitating approvals, predicting LOS) but cannot base decisions on large datasets without the individual's circumstances (42 CFR 422.101(c)(1)(i)); algorithms cannot change or deviate from publicly posted coverage criteria; plans must apply NCDs/LCDs, and internal criteria only where Medicare criteria are not fully established, must be evidence-based and publicly accessible (422.101(b)(6)); adverse medical-necessity decisions must be reviewed by a physician or appropriate professional with relevant expertise (422.566(d)); ACA Section 1557 nondiscrimination applies. — [Manatt summary](https://www.manatt.com/insights/newsletters/health-highlights/cms-weighs-in-on-the-use-of-algorithms-and-artific); [Reed Smith](https://www.reedsmith.com/en/perspectives/2024/02/cms-confirms-medicare-advantage-organizations-may-use-ai-in-making-coverage)

**CMS-0057-F (Interoperability and Prior Authorization)**
- From Jan 1, 2026 impacted payers (MA, Medicaid/CHIP FFS and managed care, FFE QHPs) must decide standard requests in 7 calendar days and expedited in 72 hours, and give a specific denial reason regardless of channel; annual public PA metrics due March 31 (first report Mar 31, 2026 for CY2025). By Jan 1, 2027: Prior Authorization API (requirements, documentation, submission/decision), expanded Patient Access API with PA status (updated within one business day), Provider Access and Payer-to-Payer APIs. Drugs are excluded. — [Health Samurai CMS-0057 docs](https://www.health-samurai.io/docs/payerbox/compliance/cms-0057); [LeadingAge](https://leadingage.org/cms-finalizes-interoperability-prior-authorization-rule/)
- CRD/DTR/PAS workflow: CRD answers "is PA required" via CDS Hooks at order time; DTR returns a FHIR Questionnaire with CQL that pre-fills from the chart; PAS submits a Claim bundle and receives a ClaimResponse. — [HL7 News, Jan 2026](https://hl7news.hl7.org/?p=1277)

**Industry pledge**
- AHIP pledge (June 23, 2025): standardized FHIR e-PA by Jan 1, 2027; demonstrated reductions in medical PA by Jan 1, 2026; 90-day continuity-of-care honoring of existing PAs from Jan 1, 2026; clear explanations of determinations with appeal guidance; at least 80% of electronic PA approvals answered in real time by 2027; clinical denials continue to be reviewed by medical professionals. — [TechTarget](https://www.techtarget.com/healthcarepayers/news/366626091/Major-health-plans-pledge-to-simplify-prior-authorizations)

**State laws requiring clinician review**
- California SB 1120 "Physicians Make Decisions Act" (effective Jan 1, 2025; H&S Code 1367.01, Ins. Code 10123.135): AI "shall not deny, delay, or modify health care services based, in whole or in part, on medical necessity"; determination by a licensed physician/competent professional; must use individual clinical history, not solely group datasets; no discrimination; open to audit; periodic performance review. — [CASRAI guide](https://www.casrai.org/guides/ai-claim-denials-state-utilization-review-laws); [Sen. Becker press release](https://sd13.senate.ca.gov/news/press-release/december-9-2024/landmark-law-prohibits-health-insurance-companies-using-ai-to)
- Texas SB 815 (2025; Ins. Code 4201.156): utilization review agents may not use an automated decision system to make, wholly or partly, an adverse determination; plans issued/renewed on or after Jan 1, 2026; commissioner may audit. — [CASRAI guide](https://www.casrai.org/guides/ai-claim-denials-state-utilization-review-laws)
- 2026 enactments: Alabama SB 63 (Oct 1, 2026; disclosure of AI use, individualized determinations, annual certification); Colorado HB 1139 (Jan 1, 2027; qualified professional reviews denials, periodic accuracy audits); Georgia SB 444 (Jan 1, 2027; adverse determinations require licensed-provider approval); Iowa HF 2635 (July 1, 2026; AI allowed for initial PA review but not sole basis to deny/delay/downgrade; written denials naming criteria used); Utah SB 319 (Jan 1, 2027; disclose AI use to state, providers, enrollees; publish PA requirements and stats); Washington SB 5395 (June 11, 2026; only licensed clinicians deny on medical necessity; annual reporting on AI-aided denials); plus Illinois SB 3114 and Indiana HB 1271 on AI downcoding, Maryland HB 1563 adverse-decision reporting. — [Rise Health, 2026](https://www.risehealth.org/insights-articles/ai-health-insurance-state-laws-2026/); see also [Holland & Knight, May 2026](https://www.hklaw.com/en/insights/publications/2026/05/states-continue-efforts-to-regulate-ai-in-healthcare)

### Inferences
- Product rule for the demo: the payer agent may (a) auto-approve when all criteria are met with cited evidence, (b) pend with a specific document request, or (c) recommend deny, but a recommend-deny must route to a licensed clinician queue; the denial letter is issued only after the clinician signs. This satisfies CMS 422.566(d), CA SB 1120, TX SB 815, WA/GA/IA laws and the AHIP pledge.
- Every determination needs a criterion-level reason ("Criterion 2b: 6 weeks of conservative therapy not documented") to meet CMS-0057-F specific-reason and Iowa "criteria used" requirements; the agent's evidence table is the natural source.
- State-level disclosure laws (AL, UT) suggest a "this recommendation was AI-assisted" flag stored in the audit record and surfaced in member/provider notices.
- WISeR's pay-for-denials design is a cautionary contrast for analytics: avoid optimizing the agent or dashboards on denial savings; track overturn rates instead.

### Gaps
- Exact current status (settlement/trial) of the Humana and Cigna suits as of Oct 2026 was not verified.
- Whether the CY2027 MA final rule adds AI-specific requirements: one source says it has no parallel federal requirement ([CASRAI](https://www.casrai.org/guides/ai-claim-denials-state-utilization-review-laws)); not independently verified.

## 3. Public medical-necessity criteria usable in a demo

### Takeaway
CMS NCDs/LCDs (and the MAC documentation checklists) are public US-government content and the safest demo corpus; many payer policies (Aetna, Evolent/NIA guidelines posted by Louisiana Medicaid, Molina, etc.) are publicly viewable but copyrighted, so quote/link rather than redistribute. ACR Appropriateness Criteria are viewable but their terms bar copying, storing in retrieval systems, or derivative works without written permission, so they should not be ingested into a RAG index without a license. InterQual and MCG are proprietary.

### Cited Findings
- NCD 240.2 Home Use of Oxygen (CMS Medicare Coverage Database) is public with full criteria text. — [CMS MCD NCD 240.2](https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=169)
- LCD L33718 Positive Airway Pressure Devices for OSA (Policy Article A52467) and a Noridian documentation checklist are public. — [Noridian PAP checklist](https://med.noridianmedicare.com/documents/2230715/26734435/Documentation+Checklist+-+Positive+Airway+Pressure+%28PAP%29.pdf)
- Noridian publishes Power Mobility Device clinician checklists and top non-affirmation reasons from the Medicare PMD prior authorization program. — [Noridian PMD checklist](https://med.noridianmedicare.com/documents/2230703/16619307/Clinician+Checklist+Power+Mobility+Devices.pdf); [Noridian PMD non-affirmations](https://med.noridianmedicare.com/web/jddme/cert-reviews/mr/pre-claim/required-programs/reasons-for-non-affirmation)
- Lumbar MRI LCD L34220 exists (Noridian JE), but the article page was unavailable during research. — [Noridian JE article](https://med.noridianmedicare.com/web/jeb/article-detail/-/view/10525/lumbar-mri-l34220-r9-effective-august-18-2022)
- Evolent/NIA Lumbar Spine MRI guideline (NIA_CG_044) is publicly posted by Louisiana Medicaid with detailed criteria and ACR references. — [LDH posting (July 2024)](https://ldh.la.gov/assets/medicaid/MCPP/6.14.24/741_LHCC_Lumbar_Spine_MRI_July_2024_redlines.pdf)
- Aetna pharmacy PA criteria for Wegovy/Zepbound are publicly posted HTML. — [Aetna 5098-C](https://www.aetna.com/products/rxnonmedicare/data/2025%20commercial/Antiobesity_Agents_Aetna_ONLY_for_Specific_States_PA_with_Limit_5098-C_P08-2024_R.html)
- ACR Appropriateness Criteria terms: personal use only for research/scientific/informational purposes; may not copy, download, store in a retrieval system, redistribute, or create derivative works without ACR's written permission. — [ACR Terms and Conditions](https://ACR.org/Clinical-Resources/ACR-Appropriateness-Criteria/Terms-and-Conditions)
- CMS rules require MA internal criteria to be publicly accessible, so MA plan policies must be posted. — [Manatt](https://www.manatt.com/insights/newsletters/health-highlights/cms-weighs-in-on-the-use-of-algorithms-and-artific)
- Cohere's own product decisions against NCDs/LCDs plus plan policies, confirming NCD/LCD are a real-world criteria source. — [Cohere](https://coherehealth.com/decision)

### Inferences
- Recommended demo corpus: NCD 240.2, LCD L33718/A52467, the PMD LCD and checklists, LCD L34220 (lumbar MRI) and a self-authored "Demo Health Plan" policy paraphrasing public criteria. Label everything "for demonstration; not a real payer policy."
- For the lumbar MRI and GLP-1 cases, write original fictional policy text inspired by public criteria rather than copying Evolent/Aetna text into Snowflake tables, to avoid copyright issues.
- Do not ingest ACR, InterQual or MCG content.

### Gaps
- The text of LCD L34220 could not be retrieved in this pass; verify criteria directly at cms.gov MCD before building the lumbar scenario from it.
- Licensing terms for Aetna CPBs, UHC and Cigna policy sites were not reviewed; assume copyrighted.
- InterQual/MCG proprietary status is well-known but was not sourced in this pass.

## 4. Demo PA scenarios (3-5) with codes, criteria and questionnaire items

### Takeaway
Five scenarios built on public criteria give a full spread: CPAP initial (auto-approve), lumbar MRI with insufficient conservative therapy (pend/needs info), lumbar MRI with red flag (auto-approve variant), home oxygen with non-qualifying saturation (recommend deny -> clinician review), and GLP-1 continuation with <5% weight loss (recommend deny -> clinician review), plus PMD as a stretch.

### Cited Findings
**Scenario A: CPAP for OSA (auto-approve)** — HCPCS E0601 (CPAP device), LCD L33718. Initial criteria: face-to-face evaluation before sleep test; Medicare-covered sleep test with AHI/RDI >=15 (min 30 events), or 5-14 (min 10 events) plus excessive daytime sleepiness, impaired cognition, mood disorder, insomnia, hypertension, ischemic heart disease or stroke; supplier instruction documented. Continuation: F2F re-evaluation day 31-91 showing improvement and adherence >=4 h/night on 70% of nights in any consecutive 30 days within the first 3 months. — [Noridian PAP checklist](https://med.noridianmedicare.com/documents/2230715/26734435/Documentation+Checklist+-+Positive+Airway+Pressure+%28PAP%29.pdf)
- Questionnaire items: Was a face-to-face evaluation for OSA documented before the sleep test (date)? Sleep test type and date? AHI/RDI value and total events? If AHI 5-14, which qualifying symptom/comorbidity? Bonus continuation question: adherence % nights >=4h in best 30-day window?

**Scenario B: Lumbar spine MRI without contrast (pend / needs more info; red-flag variant auto-approves)** — CPT 72148 (also 72149, 72158). Evolent/NIA criteria: failure of >=6 weeks of conservative treatment within the past 6 months, multimodal with one active (PT, physician-supervised home exercise, chiropractic) and one inactive (meds, injections, devices) component; conservative care not required with red flags such as cauda equina syndrome (saddle anesthesia, new bladder/bowel dysfunction) or new neurologic deficit (new weakness, foot drop, dermatomal sensory changes). — [NIA_CG_044 via LDH](https://ldh.la.gov/assets/medicaid/MCPP/6.14.24/741_LHCC_Lumbar_Spine_MRI_July_2024_redlines.pdf)
- Questionnaire items: Duration of symptoms? Conservative therapy type(s), start/end dates, and response? Any red flags (saddle anesthesia, bowel/bladder change, progressive weakness/foot drop, history of cancer, fever/IV drug use, significant trauma)? Is surgery or injection being planned?
- Pend case: note documents 3 weeks NSAIDs only and no PT -> agent pends and requests PT notes or documentation of 6 weeks of multimodal care.

**Scenario C: Home oxygen (deny-likely -> clinician review)** — HCPCS E1390 (concentrator), NCD 240.2. Group I: PaO2 <=55 mm Hg or SpO2 <=88% at rest on room air, or during sleep/exercise with specified conditions; Group II: PaO2 56-59 or SpO2 89% plus dependent edema suggesting CHF, pulmonary hypertension/cor pulmonale, or hematocrit >56%; test must be at "time of need" (inpatients within 2 days of discharge); non-covered: angina without hypoxemia, breathlessness without cor pulmonale or hypoxemia; MACs should account for skin pigmentation, altitude and age when reviewing values. — [CMS NCD 240.2](https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=169)
- Deny-likely case: resting SpO2 92% on room air, no exercise/sleep test, dyspnea only -> recommend deny with criterion-level reason; human reviewer may instead pend for an exercise oximetry test.
- Questionnaire items: Test type (ABG/oximetry), date, condition (rest/exercise/sleep), result on room air? Was the test performed by a qualified provider (not the DME supplier)? Group II findings (edema, PH, hematocrit)?

**Scenario D: GLP-1 for obesity, continuation (deny-likely or pend)** — Wegovy/Zepbound (pharmacy benefit; NDC-based, outside CMS-0057-F scope). Aetna 5098-C: initial adult approval requires age >=18, BMI >=40 or >=35 with comorbidity (per this specific-state policy), active lifestyle program; continuation requires >=5% loss of baseline weight after 12 weeks at stable maintenance dose; initial approval 7 months (Wegovy)/8 months (Zepbound), continuation 12 months. — [Aetna 5098-C](https://www.aetna.com/products/rxnonmedicare/data/2025%20commercial/Antiobesity_Agents_Aetna_ONLY_for_Specific_States_PA_with_Limit_5098-C_P08-2024_R.html)
- Note: FDA labeling uses BMI >=30 or >=27 with comorbidity; this specific Aetna state policy is stricter, which is a good demo of "policy is plan-specific."

**Scenario E (stretch): Power mobility device (pend)** — HCPCS K0823 (Group 2 standard power wheelchair). Top Medicare PA non-affirmation reasons (Oct-Dec 2023): F2F exam doesn't show the patient can safely operate a POV (40%), doesn't show upper-body limits prevent self-propelling a manual wheelchair (28%), doesn't show cane/walker insufficient (21%), POV not ruled out (11%). — [Noridian](https://med.noridianmedicare.com/web/jddme/cert-reviews/mr/pre-claim/required-programs/reasons-for-non-affirmation)

### Inferences
- Suggested ICD-10 codes (standard code set, not sourced here; verify against each LCD's covered code list): G47.33 OSA (Scenario A); M54.16/M54.17 lumbar radiculopathy, M54.50 low back pain, G83.4 cauda equina (Scenario B); J44.9 COPD, R06.02 shortness of breath (Scenario C); E66.01 morbid obesity + Z68.41 BMI 40-44.9 (Scenario D); G35/M62.81 or similar mobility diagnosis (Scenario E).
- Represent each policy as a criteria tree (AND/OR nodes with leaf evidence requirements), mirroring both CQL/DTR questionnaires and the multi-agent paper's checklist tree; the provider-side auto-fill and payer-side review then share one criteria model.
- Synthetic chart notes should include distractors (e.g., "patient declined PT" vs. "PT not tolerated due to X") to test the "documented medical reason" nuance.

### Gaps
- Exact covered ICD-10 lists for each LCD were not extracted.
- PMD LCD criteria text (L33789) was not fully retrieved; only checklist/non-affirmation reasons.

## 5. Responsible AI design patterns

### Takeaway
The patterns that regulators, litigants and the evidence converge on: asymmetric automation (no auto-deny), criterion-level evidence citations, deterministic policy logic, calibrated confidence with routing thresholds, clinician sign-off with override capture, immutable audit trails, monitoring of overturn rates and subgroup disparities, PHI controls, and gold-standard eval sets.

### Cited Findings
- Recommendation-only engines with CQL-encoded policy for traceability and clinician override are an established vendor pattern. — [Availity AuthAI](https://www.availity.com/authai/)
- Evidence classification per criterion (supporting/contradicting/irrelevant) plus jury voting for confidence and bottom-up propagation over a criteria tree achieved ~95% accuracy in the research setting. — [arXiv 2404.17977](https://arxiv.org/abs/2404.17977)
- LLMs are poor at citing primary literature and make coding errors; clinician oversight required. — [medRxiv](https://medrxiv.org/content/10.1101/2024.04.30.24306634.full.pdf); [HMP / Frontiers](https://www.hmpgloballearningnetwork.com/site/frmc/news/large-language-model-shows-promise-nephrology-prior-authorization-letter-drafting); [arXiv 2603.29366](https://arxiv.org/abs/2603.29366)
- Legal requirements to embed: individualized review, no group-dataset-only decisions, publicly posted criteria, physician review of adverse decisions, nondiscrimination (Section 1557). — [Manatt](https://www.manatt.com/insights/newsletters/health-highlights/cms-weighs-in-on-the-use-of-algorithms-and-artific); auditability and periodic performance review — [CASRAI on SB 1120](https://www.casrai.org/guides/ai-claim-denials-state-utilization-review-laws); periodic accuracy audits (CO), AI-use disclosure (AL, UT), annual reporting on AI-aided denials (WA) — [Rise Health](https://www.risehealth.org/insights-articles/ai-health-insurance-state-laws-2026/)
- NCD 240.2 tells reviewers to account for skin pigmentation when interpreting oximetry, a concrete bias consideration (pulse oximeters can overestimate saturation in darker skin). — [CMS NCD 240.2](https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=169)
- nH Predict litigation centers on reversal rates (~90% alleged) and low appeal rates, making overturn rate a key fairness/quality KPI. — [DistilInfo](https://distilinfo.com/2026/03/12/court-orders-unitedhealth-to-disclose-ai-denial-algorithm/)

### Inferences (concrete patterns for the product)
1. **Decision policy:** `AUTO_APPROVE` only if every required leaf criterion is MET with >=1 cited evidence span and confidence >= threshold; `PEND` if any criterion is UNKNOWN (generate specific document request); `RECOMMEND_DENY` only routes to a licensed-clinician queue; nothing denies without a named human signer.
2. **Grounding:** every criterion verdict stores note ID, character offsets/quote, and policy section ID; UI highlights the quote. Reject any model output whose quote is not an exact substring of the source (cheap hallucination check).
3. **Split LLM vs. logic:** LLM (Cortex COMPLETE / AI_EXTRACT) extracts facts (dates, values, therapies); SQL/Python evaluates thresholds (AHI >=15, 6 weeks, SpO2 <=88). Numbers never "decided" by the LLM.
4. **Confidence:** self-consistency (n samples/jury vote) or agreement between two models per criterion; show as High/Med/Low; low confidence forces human review.
5. **Human-in-the-loop UX:** reviewer sees criteria checklist with evidence, can override per criterion with reason code; overrides feed evaluation set.
6. **Audit trail:** immutable table per decision: input hashes, policy version, model name/version, prompts, outputs, confidence, human actor, timestamps, AI-assisted flag (for state disclosure laws and CMS-0057-F reporting). Snowflake Time Travel/streams help.
7. **Monitoring:** auto-approval rate, pend rate, recommend-deny rate, clinician override rate, appeal overturn rate, turnaround vs 72h/7d SLAs, broken down by service, provider, and member demographics (age, sex, race/ethnicity where available, language, geography) for disparity detection.
8. **PHI:** keep data and model inference inside Snowflake governance boundary (Cortex runs in-account); masking policies and row access policies; synthetic data only for the hackathon; minimum-necessary context per prompt.
9. **Evaluation:** gold set of synthetic cases with clinician-labeled criterion verdicts, including adversarial/distractor notes; metrics: per-criterion precision/recall, decision accuracy, false-approve and false-deny rates, citation validity rate, letter administrative completeness (codes, duration, units) per arXiv 2603.29366.
10. **Letters:** denial explanations and appeal letters generated from the structured evidence table and policy citations (never free-recalled literature); include specific unmet criterion, what documentation would satisfy it, and appeal rights.

### Gaps
- No published standard threshold for confidence-based routing in PA was found.
- No source found quantifying demographic bias in PA AI models specifically.

## 6. Innovative enhancement ideas (2025-2026)

### Takeaway
The market is moving toward real-time FHIR-based e-PA (CRD/DTR/PAS), gold carding, transparency to members and agentic automation; a hackathon demo can differentiate with "PA not required" short-circuit, likelihood-of-approval before submission, automated gold-card analytics, natural-language policy-to-rules authoring, and an agent-to-agent negotiation loop.

### Cited Findings
- Real-time "is PA required?" at order entry via CRD is now live in Epic with several payers (Aug 2026). — [Healthcare Finance News](https://www.healthcarefinancenews.com/news/epic-launches-real-time-prior-authorization-four-health-systems)
- DTR questionnaires pre-fill from the chart using CQL; agentic AI can request missing info and apply nuanced guidelines. — [HL7 News](https://hl7news.hl7.org/?p=1277)
- AHIP target: 80% of electronic approvals in real time by 2027. — [TechTarget](https://www.techtarget.com/healthcarepayers/news/366626091/Major-health-plans-pledge-to-simplify-prior-authorizations)
- Texas gold card law: exemption if >=90% approval; fewer than 4% of physicians qualified; HB 3812 (eff. Sept 1, 2025) extended evaluation to 12 months, minimum 5 services, and annual reporting. — [Texas Medical Association](https://www.texmed.org/LegeWrapInsurance)
- CMS-0057-F requires PA status in the Patient Access API within one business day (Jan 2027), enabling member-facing status. — [Health Samurai](https://www.health-samurai.io/docs/payerbox/compliance/cms-0057)
- Top Medicare PMD non-affirmation reasons are documentation gaps, supporting proactive provider-side completeness checks. — [Noridian](https://med.noridianmedicare.com/web/jddme/cert-reviews/mr/pre-claim/required-programs/reasons-for-non-affirmation)
- Voice agents for payer calls (Infinitus) indicate agentic automation of provider-payer communication. — [Infinitus](https://www.infinitus.ai/blog/ai-agents-for-follow-up-calls-prior-authorizations-appeals-more/)

### Inferences (idea list for the product)
- **"PA not required" short-circuit:** rules table keyed on CPT/HCPCS + plan + site of service + provider gold-card status; return instantly before any LLM call.
- **Gold-card automation:** analytics computing each provider's approval rate per service over a rolling 12 months (Texas-style 90%, min 5 requests) and auto-exempting; dashboard shows "near gold card" providers.
- **Provider-side likelihood-of-approval / completeness score:** before submission, the provider agent runs the payer's published criteria tree on the chart and shows unmet criteria ("add PT notes for 6 weeks") to reduce pends; PMD data shows documentation gaps dominate non-affirmations.
- **Pend -> targeted document request:** agent generates a specific request mapped to the unmet criterion, and the provider agent auto-searches the chart for it.
- **NL policy authoring:** payer clinical policy staff paste policy text; LLM drafts a criteria tree/CQL-like JSON with citations to policy paragraphs; human approves and versions it (supports CMS "do not deviate from posted criteria").
- **Member-facing status + plain-language explanation** of pends/denials in the member's language.
- **Agent-to-agent loop:** provider agent submits -> payer agent returns a structured "missing criterion" -> provider agent retrieves evidence and resubmits, all within FHIR DTR/PAS semantics; humans approve any final denial. MCP servers could expose chart search (provider side) and policy/criteria lookup (payer side) as tools; this is conceptual, with no production examples found.
- **Analytics:** overturn rates by service/policy to flag policies that cause unnecessary denials; turnaround vs 72h/7d SLAs; CMS-0057-F public metric report auto-generation.

### Gaps
- No verified production deployments of provider-agent <-> payer-agent negotiation or MCP-based PA were found; treat as concept.
- No data found on member-facing PA status adoption or outcomes.
