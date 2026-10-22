# Prior Authorization (PA) in US Healthcare: Problem, Regulatory Drivers, Market (as of Oct 18, 2026)

Labels used: **[FINAL]** = finalized regulation/law; **[PROPOSED]** = proposed, not binding; **[VOLUNTARY]** = industry pledge; **[OLDER]** = data predating 2025.

## Q1. What is the scale and cost of PA burden?

### Takeaway
PA is high-volume, slow, and harmful. In the latest AMA survey (2025 survey, published May 2026), physicians handle about 40 PAs a week, which takes about 13 hours of physician and staff time, and 95% say PA delays care. Medicare Advantage alone made about 53M PA determinations in 2024, and more than 80% of appealed denials were overturned. Electronic adoption of medical PA is only 40% (2025 CAQH Index). Manual PA costs providers about twice as much per transaction as electronic PA [OLDER cost data].

### Cited Findings
**AMA 2025 Prior Authorization Physician Survey** (1,000 practicing physicians; AMA article dated May 18, 2026). Source for all bullets in this group: [AMA](https://www.ama-assn.org/practice-management/prior-authorization/only-1-3-doctors-trusts-insurers-prior-authorization).
- Physicians average **40 PA requests per physician per week**, taking **13 hours** of physician and staff time.
- **40%** employ staff who work only on PA.
- **94%** say PA contributes to burnout.
- **95%** say PA delays access to necessary care, and **79%** report that patients abandon treatment because of PA.
- **26%** report a serious adverse event (hospitalization, permanent impairment or death) for a patient because of PA.
- **92%** say PA hurts clinical outcomes, and **88%** say it interferes with continuity of care.
- **61%** say PA at least sometimes destabilizes patients whose condition was stable.
- Downstream effects reported: ineffective initial treatments (75%), additional office visits (73%), urgent or emergency care (47%), hospitalizations (32%).
- **88%** say PA increases overall healthcare utilization.
- **32%** say requests are often or always denied, and **74%** say denials increased over the past 5 years.
- **About 60%** worry that AI will further increase denials.
- Required PAs rose over 5 years for prescription drugs (84%) and medical services (82%).
- Many find it hard to tell whether PA is required: 63% for drugs and 62% for services.
- Only **24%** say their EHR offers ePA for prescriptions, and 27% say drug-PA requirement information in their EHR or e-prescribing system is rarely or never accurate.
- Only **5%** take part in gold-card or exemption programs.
- Only **24%** agree that medical-necessity denials are reviewed by a qualified physician. Only **16%** say peer-to-peer reviewers often or always have appropriate qualifications.
- Only about **1 in 3** (33%) expect the insurer pledge to make a meaningful difference. The 33% figure comes from [AJMC, Aug 26 2026](https://www.ajmc.com/view/faq-prior-authorization-reform-will-changes-go-far-enough-by-2027-).
- Separately, a KFF poll (July 2025) found only 39% of patients believe insurers will follow through on the pledge — [AMA](https://www.ama-assn.org/practice-management/prior-authorization/only-1-3-doctors-trusts-insurers-prior-authorization).

**KFF Medicare Advantage PA data (2024 data, published Jan 28, 2026)**. Source for all bullets in this group: [KFF](https://www.kff.org/medicare/medicare-advantage-insurers-made-nearly-53-million-prior-authorization-determinations-in-2024/).
- MA insurers made **52.8M PA determinations** in 2024, up from 49.8M in 2023. That is 1.7 requests per enrollee.
- **7.7%** were fully or partly denied, or **4.1M requests**. The denial rate was 6.4% in 2023 and 7.4% in 2022.
- Only **11.5%** of denials were appealed, but **80.7%** of appeals were overturned. The overturn rate has been above 80% every year from 2019 to 2024.
- These figures exclude withdrawn or dismissed requests.

**CAQH Index**
- The 2025 CAQH Index (2024 data) puts fully electronic medical PA adoption at **40%**. It was 31% in the 2023 Index and 35% in the 2024 Index. The report does not give partially electronic or manual shares — [CAQH 2025 Index Executive Report](https://index.caqh.org/hubfs/Index/CAQH_IndexReport_2025_Executive%20Report_v6.pdf); [AJMC, May 1 2026](https://www.ajmc.com/view/caqh-index-finds-20-billion-in-cost-savings-opportunities).
- The 2025 Index also reports these readiness figures — [CAQH 2025 Index](https://index.caqh.org/hubfs/Index/CAQH_IndexReport_2025_Executive%20Report_v6.pdf):
  - **63%** of medical plans were still developing ePA FHIR APIs.
  - Only **20%** of providers had begun implementation.
- The industry-wide savings opportunity is more than **$20B a year** if the remaining manual administrative transactions go fully electronic. Of that, $18.7B is medical. This covers all transaction types, not PA alone — [AJMC](https://www.ajmc.com/view/caqh-index-finds-20-billion-in-cost-savings-opportunities).
- The Index surveyed about 600 provider organizations and health plans, covering 63% of insured lives. Results may be distorted by the Feb 2024 Change Healthcare cyberattack — [AJMC](https://www.ajmc.com/view/caqh-index-finds-20-billion-in-cost-savings-opportunities).
- **Cost per PA transaction [OLDER, 2023 CAQH Index; secondary source, not checked against the original]** — [Nirmitee summary of the 2023 CAQH Index](https://nirmitee.io/blog/true-cost-prior-authorization-data-driven-analysis-cms-ama-caqh/):
  - Providers pay **$10.97 for a manual PA vs $5.79 electronic**. Plans pay $3.52 manual vs $0.05 electronic.
  - A manual PA takes about 24 minutes for specialists and about 8 minutes for generalists.
  - Going fully electronic would save about $494M a year in PA spending.

### Inferences
- About 40 PAs a week across roughly 1M US physicians implies hundreds of millions of PA touches a year. This is order-of-magnitude reasoning, not a sourced figure.
- More than 80% of appealed MA denials are overturned. That suggests many initial denials stem from missing or poorly presented documentation, which a documentation-assembly or AI-summarization product can address.
- 60% of physicians fear AI will increase denials. Position the product as "AI assembles evidence and recommends approval; humans decide adverse outcomes."

### Gaps
- The 2025 CAQH Index executive report does not give PA cost per transaction or minutes per transaction. The latest verified cost figures are from 2023 (secondary source).
- I found no 2026 CAQH Index; it may not be published yet.
- I found no 2025 KFF MA data yet.

## Q2. Regulatory drivers: CMS-0057-F, HTI-4, CMS-0062-P, X12 278, AHIP pledge

### Takeaway
CMS-0057-F [FINAL, Jan 17 2024] already requires government-program payers to meet these Jan 1, 2026 requirements:
- Decision times of 72 hours (expedited) and 7 days (standard)
- Specific denial reasons
- Public PA metrics

FHIR Prior Authorization, Provider Access, Payer-to-Payer and expanded Patient Access APIs follow on Jan 1, 2027. The provider ePA measure starts in performance year 2027. HTI-4 [FINAL, Jul 2025] certifies EHRs for the CRD, DTR and PAS ePA APIs. CMS-0062-P [PROPOSED, Apr 2026] would extend this to drugs, starting Oct 1, 2027. The voluntary AHIP/BCBSA pledge (June 2025, plans covering about 270M people) targets standardized ePA in 2027, with 80% of complete electronic requests decided in real time.

### Cited Findings
**CMS-0057-F Interoperability & Prior Authorization Final Rule [FINAL]** (fact sheet, Jan 17, 2024). Source for all bullets in this group: [CMS fact sheet](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f).
- **Impacted payers:** Medicare Advantage organizations, state Medicaid and CHIP fee-for-service programs, Medicaid managed care plans, CHIP managed care entities, and QHP issuers on the federally facilitated exchanges.
  - The rule does **not** cover employer or commercial plans outside these programs.
  - It does **not** cover drugs.
- **Jan 1, 2026 (operational):**
  - Decisions within **72 hours for expedited** and **7 calendar days for standard** requests. The timeframes do not apply to FFE QHPs.
  - A **specific denial reason** for every denial, however the request was submitted.
  - **Annual public posting of PA metrics**, with the first set due by **Mar 31, 2026**.
  - Annual reporting to CMS on Patient Access API usage.
- **Jan 1, 2027 (APIs, HL7 FHIR):**
  - **Prior Authorization API:** discovers whether PA is required and what documentation is needed, supports submission, and returns approve, deny-with-reason or request-more-info.
  - **Provider Access API:** in-network providers with a treatment relationship can access patient data, with patient opt-out.
  - **Payer-to-Payer API:** data moves when a patient changes payers, with patient opt-in.
  - **Patient Access API:** adds PA information (not drugs).
- **Provider side:**
  - A new **"Electronic Prior Authorization" attestation measure** under Promoting Interoperability.
  - For MIPS clinicians it starts with the **CY 2027 performance period** (CY 2029 payment year).
  - For eligible hospitals and CAHs it starts with the CY 2027 EHR reporting period.
- **X12 278 enforcement discretion:** HHS will not enforce the HIPAA X12 278 standard against covered entities that run an all-FHIR or FHIR-plus-X12 PA API.

**HTI-4 (ASTP/ONC) [FINAL; finalized Jul 31, 2025]**. Source for all bullets in this group: [HealthIT.gov HTI-4](https://healthit.gov/resources/hti-4-final-rule-electronic-prescribing-real-time-prescription-benefit-and-electronic-prior-authorization/).
- Adds health IT certification criteria for provider ePA APIs based on the Da Vinci FHIR IGs:
  - **Coverage Requirements Discovery (CRD)**
  - **Documentation Templates and Rules (DTR)**
  - **Prior Authorization Support (PAS)**
- Adopts NCPDP SCRIPT 2023011. Developers may use either the old or new version through Dec 31, 2027; from Jan 1, 2028 only 2023011 is allowed.
- Adds real-time prescription benefit to the Base EHR definition on Jan 1, 2028.
- A Rural Health Info Center summary lists the rule as effective Oct 1, 2025 — [MO Rural Health](https://ruralhealthinfocenter.health.mo.gov/policy-update-health-data-technology-and-interoperability-electronic-prescribing-real-time-prescription-benefit-and-electronic-prior-authorization-hti-4-final-rule-effective-october-1-2025).

**CMS-0062-P: 2026 Interoperability Standards & Prior Authorization for Drugs [PROPOSED, fact sheet Apr 10, 2026]**. Source for all bullets in this group: [CMS fact sheet](https://www.cms.gov/newsroom/fact-sheets/2026-cms-interoperability-standards-prior-authorization-drugs-proposed-rule).
- Extends the PA API, denial reasons, timeframes and metrics to **drugs**:
  - Medical-benefit drugs go through the FHIR PA API.
  - Pharmacy-benefit drugs use NCPDP SCRIPT, Formulary & Benefit (F&B) and Real-Time Prescription Benefit (RTPB).
- Adds small-group FF-SHOP QHPs as impacted payers.
- Proposed decision timeframes:
  - **24 hours** for drugs in Medicaid/CHIP.
  - For FFE QHPs, **72 hours standard / 24 hours expedited** for drugs.
- Proposes adopting **HL7 FHIR as a HIPAA standard** for PA transactions, plus the Da Vinci CDex IG for attachments. Compliance would be 24 months after the final rule (36 months for small plans).
- Payers would have to report numeric counts alongside percentages in their PA metrics. New drug-PA metrics would start in 2028, covering 2027 data.
- Most compliance dates are **Oct 1, 2027**.
- Status: as of the latest source found (Aug 26, 2026), it was still proposed — [AJMC](https://www.ajmc.com/view/faq-prior-authorization-reform-will-changes-go-far-enough-by-2027-).

**AHIP/BCBSA voluntary PA commitments [VOLUNTARY; announced June 2025]**
- **Who signed:** nearly 60 insurers, developed with HHS/CMS — [AJMC Apr 8 2026](https://www.ajmc.com/view/insurers-cut-11-of-prior-authorizations-expand-continuity-of-care-protections). Other sources say more than 60 insurers — [AMA](https://www.ama-assn.org/practice-management/prior-authorization/only-1-3-doctors-trusts-insurers-prior-authorization). The signers cover about **270M Americans** — [AJMC Aug 2026](https://www.ajmc.com/view/faq-prior-authorization-reform-will-changes-go-far-enough-by-2027-).
- **Commitments** — [AJMC Apr 2026](https://www.ajmc.com/view/insurers-cut-11-of-prior-authorizations-expand-continuity-of-care-protections); [AMA](https://www.ama-assn.org/practice-management/prior-authorization/only-1-3-doctors-trusts-insurers-prior-authorization):
  - Reduce the scope of services that need PA by **Jan 1, 2026**.
  - Honor existing PAs for about **90 days** when a patient changes plans.
  - Give clearer denial explanations.
  - Have medical reviews of nonapproved requests.
  - Standardize ePA by **Jan 1, 2027**.
- **Reported progress (Apr 7, 2026):** PA requirements cut **11%**, about **6.5M fewer** authorizations. MA PA use fell **more than 15%** — [AJMC](https://www.ajmc.com/view/insurers-cut-11-of-prior-authorizations-expand-continuity-of-care-protections).
- **2026:** plans, vendors and providers are implementing standardized documentation fields.
- **Jan 2027:** standardization is fully implemented and expands to more services.
- **Target:** at least **80% of electronic requests submitted with complete documentation get a decision in real time ("in seconds")**. This does not mean 80% of all requests are approved instantly — [AJMC Aug 2026](https://www.ajmc.com/view/faq-prior-authorization-reform-will-changes-go-far-enough-by-2027-).

### Inferences
- "Why now" has three parts:
  1. As of 2026, regulated payers must decide within 72 hours or 7 days, give reasons for denials, and publish metrics.
  2. In 2027, FHIR PA APIs become mandatory, along with the provider ePA measure and the pledge's real-time target.
  3. Drug PA likely follows from Oct 2027, pending a final CMS-0062 rule.
- A hackathon product aligned to Da Vinci CRD/DTR/PAS data structures and the CMS metric definitions maps directly onto these compliance needs.
- The real-time target depends on "complete documentation." Assembling complete clinical evidence automatically, for example with Cortex extracting from notes, is the leverage point.

### Gaps
- I could not confirm the official list of CMS-0057-F public metric definitions from a fetched page. Commonly cited metrics are:
  - % of standard and expedited requests approved and denied
  - % approved after appeal
  - % where the timeframe was extended and the request then approved
  - Average and median time from submission to decision

  These need checking against 42 CFR / the [Federal Register rule](https://www.federalregister.gov/documents/2024/02/08/2024-00895).
- I could not verify the CMS savings estimate for the rule ("about $15B over 10 years" is often cited) from the fetched fact sheet.
- I found no evidence of a delay to the CMS-0057-F 2026/2027 dates.

## Q3. State PA reform, gold carding, AI-denial laws; CMS AI guidance; WISeR

### Takeaway
States are converging on three things: gold-carding exemptions, faster turnaround, and a ban on AI or algorithms making adverse determinations alone (CA SB 1120, TX SB 815, MD HB 820). CMS's Feb 2024 FAQ says MA coverage decisions must rest on individual patient circumstances. Meanwhile, CMS's own WISeR model [live since Jan 1, 2026] uses AI vendors for PA in traditional Medicare in 6 states, with clinicians making every non-payment decision.

### Cited Findings
**Gold carding**
- Before the 2025 session, six states had gold-card laws: **Arkansas, Colorado, Louisiana, Texas, West Virginia and Wyoming** — [MultiState, Aug 2025](https://www.multistate.us/insider/2025/8/14/prior-authorization-reform-gains-momentum-in-states).
- 2025 enactments include AR HB 1301, IA HF 303, IN SB 480, MD HB 820, MT HB 398, NM HB 39, TX HB 3812 and WV SB 833 — [MultiState](https://www.multistate.us/insider/2025/8/14/prior-authorization-reform-gains-momentum-in-states).
- **Texas HB 3812 (2025)** extends the gold-card look-back period from 6 months to 1 year — [MultiState](https://www.multistate.us/insider/2025/8/14/prior-authorization-reform-gains-momentum-in-states). It also strengthens rules against arbitrary denials — [AAOS Now, Jun 2026](https://www.aaos.org/aaosnow/2026/jun/advocacy/advocacy05/).
- **Oregon HB 3134 (July 2025)** lowered the gold-card approval threshold from 90% to 80% over 12 months — [AAOS Now](https://www.aaos.org/aaosnow/2026/jun/advocacy/advocacy05/).
- Uptake is low: only 5% of physicians take part in gold-card or exemption programs — [AMA](https://www.ama-assn.org/practice-management/prior-authorization/only-1-3-doctors-trusts-insurers-prior-authorization). Coverage reports that state gold-card programs "offer little relief" — [MDedge](https://mdedge.com/content/state-mandated-gold-card-programs-ease-prior-authorization-burdens-offer-little-relief-experts-say).

**AI and algorithm restrictions**
- **California SB 1120** (chaptered Sep 28, 2024; effective **Jan 1, 2025**; H&S Code §1367.01 and Ins. Code §10123.135) — [CASRAI summary](https://www.casrai.org/guides/ai-claim-denials-state-utilization-review-laws); [CA Senate press release](https://sd13.senate.ca.gov/news/press-release/december-9-2024/landmark-law-prohibits-health-insurance-companies-using-ai-to):
  - AI or algorithms may not deny, delay or modify care based on medical necessity. Only a licensed physician or competent professional may make that call.
  - Tools must use the individual enrollee's clinical history, must not discriminate, and must be auditable and periodically reviewed.
- **Texas SB 815** (signed Jun 20, 2025; effective Sep 1, 2025; applies to plans from Jan 1, 2026) — [CASRAI](https://www.casrai.org/guides/ai-claim-denials-state-utilization-review-laws):
  - A utilization review agent may not use an automated decision system to make an adverse determination "wholly or partly."
  - The Texas Department of Insurance may audit at any time.
- **Maryland HB 820 (2025)** — [MultiState](https://www.multistate.us/insider/2025/8/14/prior-authorization-reform-gains-momentum-in-states):
  - AI-based utilization review must use patient-specific data.
  - Insurers must report AI use in adverse determinations.
- **Nevada SB 128**, an AI-in-UR bill, was vetoed — [AAOS Now](https://www.aaos.org/aaosnow/2026/jun/advocacy/advocacy05/).
- States kept introducing AI-in-UR bills despite a 2025 presidential executive order threatening action against state AI regulation — [AAOS Now](https://www.aaos.org/aaosnow/2026/jun/advocacy/advocacy05/).
- **CMS MA FAQ (Feb 6, 2024)** — [DLA Piper](https://www.dlapiper.com/en/insights/publications/2024/02/cms-issues-faq-to-medicare-advantage-organizations):
  - Medical-necessity decisions must rest on the individual patient's circumstances (history, physician recommendation, clinical notes), not on a larger data set alone.
  - Algorithms and AI may assist but must comply with MA rules and avoid discrimination and bias.
  - The FAQ builds on the Apr 5, 2023 MA final rule.

**CMS WISeR model (Wasteful and Inappropriate Service Reduction) [ACTIVE]** — [HCC Buddy, Jul 2026](https://hccbuddy.com/news/wiser-model-ai-prior-authorization-2026)
- Runs **Jan 1, 2026 to Dec 31, 2031** in Original Medicare (not MA) in **AZ, NJ, OH, OK, TX and WA**.
- Six technology vendors use AI/ML alongside clinician review, and licensed clinicians make every non-payment recommendation.
- 15 service families were listed in the July 1, 2025 notice (90 FR 28749). On Apr 6, 2026, CMS delayed two of them (deep brain stimulation and lumbar decompression), leaving 13. The remaining services include nerve stimulators, epidural steroid injections, cervical fusion, knee arthroscopy for osteoarthritis, and skin substitutes.
- On May 12, 2026, GAO decided the WISeR notice is a "rule" under the Congressional Review Act.
- Sen. Wyden's S.J.Res.192 (a disapproval resolution) was introduced May 19, 2026 and placed on the Senate calendar June 9. It had not passed as of Jul 8, 2026. Its status after that is unknown.

### Inferences
- **Design principle:** the AI may auto-approve or recommend, but any adverse determination goes to a licensed clinician, with an audit trail. This keeps the product compliant in CA, TX and MD and with CMS MA guidance.
- Payer-side approval-rate analytics by provider and service (gold-card eligibility tracking) are a natural Snowflake analytics feature.
- WISeR shows CMS is willing to use AI-assisted PA, which validates the category.

### Gaps
- I did not find a full, current count of states with gold-card laws or AI-in-UR laws as of Oct 2026, so the AMA or NCSL trackers should be checked.
- I did not verify the threshold in Texas's original 2021 gold-card law (HB 3459), which is commonly cited as 90% over 6 months.
- The six WISeR vendors were not named in the source I found.

## Q4. Market landscape of ePA vendors

### Takeaway
The market splits into three groups:
- **Pharmacy ePA networks:** CoverMyMeds, Surescripts.
- **Payer-provider portals and clearinghouses:** Availity, Waystar.
- **AI-native UM and PA automation:** Cohere, Rhyme, Infinitus, SamaCare, Banjo, AKASA, Thoughtful.

There is a gap for a data-platform-native (Snowflake) layer that unifies PA analytics, evidence assembly and regulatory metrics on the data where payer and provider records already sit.

### Cited Findings
- **CoverMyMeds (McKesson):** Pharmacy-benefit ePA. McKesson acquired it in 2017 for $1.1B. It claims 500+ EHR integrations and payers covering 94% of US prescription volume, and it acquired RxLightning and FastAuth in 2025. The figures are vendor-reported — [IntuitionLabs](https://intuitionlabs.ai/articles/electronic-prior-authorization-platforms). It is embedded in Epic — [CoverMyMeds/Epic](https://www.covermymeds.health/partners/epic).
- **Surescripts (CompletEPA, Touchless PA):** E-prescribing network with ePA. Touchless PA reached 76,000+ prescribers across 70+ drugs with a **22-second median approval** (2025). 84% of prescribers use EHRs that have Surescripts ePA. The figures are vendor-reported — [IntuitionLabs](https://intuitionlabs.ai/articles/electronic-prior-authorization-platforms).
- **Availity:** Payer-provider network and multi-payer portal with end-to-end authorizations. Its AuthAI gives recommendations in under 90 seconds and claims up to 80% UM automation. It announced an Abridge partnership in Jan 2026 — [IntuitionLabs](https://intuitionlabs.ai/articles/electronic-prior-authorization-platforms).
- **Epic:** About 65% of Epic organizations used ePA in 2025, and Epic ePA volume grew from 16M per quarter (2023) to 29M per quarter (early 2025) — [IntuitionLabs](https://intuitionlabs.ai/articles/electronic-prior-authorization-platforms). I did not find details on Epic Payer Platform.
- **Cohere Health:** AI clinical-intelligence platform that automates PA and UM decision support between health plans and providers — [CB Insights](https://www.cbinsights.com/esp/healthcare-&-life-sciences/health-insurance-&-rcm-tech/prior-authorization-software).
- **Rhyme:** Automates PA end to end, tracking requests and coordinating between payers and providers — [CB Insights](https://www.cbinsights.com/esp/healthcare-&-life-sciences/health-insurance-&-rcm-tech/prior-authorization-software).
- **Infinitus:** AI voice agents for payer phone calls, such as benefit verification and PA follow-up — [CB Insights](https://www.cbinsights.com/esp/healthcare-&-life-sciences/health-insurance-&-rcm-tech/prior-authorization-software).
- **Other vendors** — [CB Insights](https://www.cbinsights.com/esp/healthcare-&-life-sciences/health-insurance-&-rcm-tech/prior-authorization-software):
  - **SamaCare:** medical-benefit PA for specialty practices.
  - **Banjo Health:** turns payer and PBM clinical criteria into decision trees and manages appeals.
  - **AKASA:** generative AI for hospital revenue cycle, including PA.
  - **Waystar:** revenue cycle and financial clearance platform.
  - **Itiliti Health:** payer-provider PA collaboration.
  - **Thoughtful AI:** revenue cycle agents for eligibility and PA.
  - **Vim:** in-EHR integration layer.
  - **AidIn:** discharge and referral management with PA support.
- **Other vendors** — [IntuitionLabs](https://intuitionlabs.ai/articles/electronic-prior-authorization-platforms):
  - **OptimizeRx:** therapy-initiation workflow reaching 700k+ providers.
  - **DrFirst:** ePA built on the CoverMyMeds and Surescripts networks.

### Inferences
- Incumbents are strong at transport (networks, portals, the EHR channel) and pharmacy PA. Medical-service PA is less electronic (40% adoption).
- **Differentiation for the hackathon:**
  1. Cortex AI extracts and summarizes clinical evidence against payer criteria, producing DTR-like questionnaire answers.
  2. The AI recommends approval, and a clinician handles any adverse decision, which fits state AI laws.
  3. Built-in CMS-0057-F metrics and turnaround-time SLA monitoring.
  4. Analytics for gold-card eligibility and denial and overturn patterns.
  5. Runs where the data already lives in Snowflake, with no data movement and with governance.

### Gaps
- Vendor statistics are vendor-reported, collected by a secondary source (IntuitionLabs), and not independently verified.
- I found no current descriptions of Epic Payer Platform, Change Healthcare/Optum PA, Anterior, Basys, Myndshft or Infinx.
- I found no recent funding figures for Cohere, Rhyme or Infinitus.

## Q5. Key KPIs a PA product should measure

### Takeaway
Use KPIs that match regulator-defined and pledge-defined metrics, so the product's dashboards double as compliance evidence. The core set is turnaround time against the 72-hour/7-day limits, approval and denial rates, approval after appeal, real-time decision rate, and documentation completeness.

### Cited Findings
- **Turnaround SLA:** % of expedited requests decided within 72 hours and % of standard requests within 7 calendar days — [CMS-0057-F](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f). For drugs under CMS-0062-P [PROPOSED], 24 hours in Medicaid/CHIP and 72 hours standard / 24 hours expedited for QHPs — [CMS](https://www.cms.gov/newsroom/fact-sheets/2026-cms-interoperability-standards-prior-authorization-drugs-proposed-rule).
- **Public PA metrics:** payers must post them annually from Mar 31, 2026 — [CMS](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f). CMS-0062-P would add numeric counts and drug metrics — [CMS](https://www.cms.gov/newsroom/fact-sheets/2026-cms-interoperability-standards-prior-authorization-drugs-proposed-rule).
- **Real-time / touchless rate:** the pledge target is at least 80% of complete electronic requests decided in real time by 2027 — [AJMC](https://www.ajmc.com/view/faq-prior-authorization-reform-will-changes-go-far-enough-by-2027-). The benchmark is Surescripts Touchless PA's 22-second median approval — [IntuitionLabs](https://intuitionlabs.ai/articles/electronic-prior-authorization-platforms).
- **Denial rate, appeal rate and overturn-on-appeal rate:** MA benchmarks for 2024 are 7.7% denied, 11.5% of denials appealed and 80.7% overturned — [KFF](https://www.kff.org/medicare/medicare-advantage-insurers-made-nearly-53-million-prior-authorization-determinations-in-2024/).
- **PA volume / scope reduction:** the pledge benchmark is an 11% reduction in PA requirements (about 6.5M fewer) — [AJMC](https://www.ajmc.com/view/insurers-cut-11-of-prior-authorizations-expand-continuity-of-care-protections).
- **Electronic submission rate:** the industry baseline is 40% fully electronic for medical PA — [CAQH 2025](https://index.caqh.org/hubfs/Index/CAQH_IndexReport_2025_Executive%20Report_v6.pdf).
- **Staff time and cost per PA:** the baselines are about 13 hours a week per physician — [AMA](https://www.ama-assn.org/practice-management/prior-authorization/only-1-3-doctors-trusts-insurers-prior-authorization) — and $10.97 manual vs $5.79 electronic per transaction for providers [OLDER, 2023] — [Nirmitee/CAQH 2023](https://nirmitee.io/blog/true-cost-prior-authorization-data-driven-analysis-cms-ama-caqh/).
- **Gold-card eligibility:** the share of providers with an approval rate of at least 80% to 90% for a service over 12 months, using the Oregon and Texas thresholds and look-back periods — [AAOS Now](https://www.aaos.org/aaosnow/2026/jun/advocacy/advocacy05/); [MultiState](https://www.multistate.us/insider/2025/8/14/prior-authorization-reform-gains-momentum-in-states).

### Inferences
- These product-specific KPIs are my own suggestions and are not sourced:
  - **First-pass approval rate:** approved without a pend or request for more information.
  - **Pend/RFI rate:** requests sent back for additional information.
  - **Documentation completeness at submission.**
  - **% of adverse recommendations routed to a clinician:** should be 100% for AI-law compliance.
  - **AI recommendation agreement rate with the clinician reviewer.**
  - **Days to decision, mean and median.**
- First-pass approval and RFI rate are the leading indicators for the pledge's real-time target.

### Gaps
- I found no authoritative industry benchmark for first-pass approval rate or touchless/auto-approval rate in medical-service PA. Vendor claims, such as Availity's "up to 80% UM automation," are unverified.
