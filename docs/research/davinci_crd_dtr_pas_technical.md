# Da Vinci Burden Reduction (CRD, DTR, PAS) + CDS Hooks: Technical Note for an End-to-End Prior Auth Demo

Method note: hl7.org/build.fhir.org pages returned only header banners through the web-fetch tool, so most technical detail below was extracted directly from the IG source repositories (FSH/markdown/JSON) on GitHub, which are what the published pages are generated from. The source files' `publication-request.json` and `sushi-config.yaml` confirm the CI-build version equals the latest published version for all three IGs (CRD 2.2.1, DTR 2.2.0, PAS 2.2.1) as of the clones made 2026-10-18 (last commits: CRD 2026-05-12, DTR 2026-09-24, PAS 2026-03-26). Links to the published page equivalents are given alongside the source files.

Source repos:
- CRD: https://github.com/HL7/davinci-crd (published: https://hl7.org/fhir/us/davinci-crd/)
- DTR: https://github.com/HL7/davinci-dtr (published: https://hl7.org/fhir/us/davinci-dtr/)
- PAS: https://github.com/HL7/davinci-pas (published: https://hl7.org/fhir/us/davinci-pas/)

## 1. Current published versions, FHIR version and dependencies

### Takeaway
All three IGs are at **STU 2.2** on **FHIR R4 (4.0.1)**: CRD **2.2.1**, DTR **2.2.0**, PAS **2.2.1**. They support US Core 3.1.1, 6.1.0 and 7.0.0 side by side. The CI builds currently match the published versions. Note that the CMS-0057-F rule *recommends* the older STU 2.0.x versions (CRD 2.0.1 / DTR 2.0.0 / PAS 2.0.1). Inferno test kits cover both 2.0.x and 2.2.x.

### Cited Findings
- CRD hl7.org home page states "v2.2.1 … STU 2.2 … based on FHIR R4 … current published version" — [CRD IG](https://hl7.org/fhir/us/davinci-crd/)
- DTR hl7.org home page: "v2.2.0, STU 2 … FHIR R4 … current published version" — [DTR IG](https://hl7.org/fhir/us/davinci-dtr/)
- PAS hl7.org home page: "v2.2.1, STU 2 … FHIR R4 … current published version" — [PAS IG](https://hl7.org/fhir/us/davinci-pas/)
- CRD `publication-request.json`: package `hl7.fhir.us.davinci-crd`, version 2.2.1, path http://hl7.org/fhir/us/davinci-crd/2.2.1, status trial-use, mode "technical-correction", sequence "STU 2.2". DTR: `hl7.fhir.us.davinci-dtr` 2.2.0, mode "milestone", path …/davinci-dtr/2.2.0. PAS: `hl7.fhir.us.davinci-pas` 2.2.1, technical-correction, path …/davinci-pas/2.2.1 — [CRD repo](https://github.com/HL7/davinci-crd), [DTR repo](https://github.com/HL7/davinci-dtr), [PAS repo](https://github.com/HL7/davinci-pas)
- build.fhir.org CI pages for CRD and PAS show "continuous build for version 2.2.1", the same as published — [CRD CI](https://build.fhir.org/ig/HL7/davinci-crd/), [PAS CI](https://build.fhir.org/ig/HL7/davinci-pas/specification.html)
- Dependencies from `sushi-config.yaml`:
  - **CRD 2.2.1** depends on:
    - `fhirVersion: 4.0.1`
    - US Core 7.0.0 (USCDI v4), US Core 6.1.0 (`hl7.fhir.us.core.v610`, USCDI v3) and US Core 3.1.1 (`hl7.fhir.us.core.v311`, USCDI v1)
    - `hl7.fhir.uv.xver-r5.r4` 0.1.0, to pre-adopt R5 elements
    - `hl7.fhir.uv.cds-hooks` **3.0.0-ballot**, the CDS Hooks spec CRD is based on
    - `hl7.fhir.uv.cds-hooks-library` **1.0.1**, the hook definitions
    - `hl7.fhir.uv.tools` 1.1.2, for the CDS Hooks logical models

    Source: [CRD sushi-config](https://github.com/HL7/davinci-crd/blob/master/sushi-config.yaml)
  - **DTR 2.2.0** depends on:
    - US Core 7.0.0 / 6.1.0 / 3.1.1
    - `hl7.fhir.uv.sdc` **4.0.0**
    - `hl7.fhir.us.davinci-hrex` **1.2.0**
    - CQL is per "Clinical Quality Language (CQL) N1"

    Source: [DTR sushi-config](https://github.com/HL7/davinci-dtr/blob/master/sushi-config.yaml); [DTR index](https://hl7.org/fhir/us/davinci-dtr/)
  - **PAS 2.2.1** depends on:
    - US Core 3.1.1 / 6.1.0 / 7.0.0
    - SDC 4.0.0, for the US Core/SDC QuestionnaireResponse reference
    - xver-r5.r4 0.1.0, to pre-adopt R5 Encounter elements
    - `hl7.fhir.us.davinci-crd` 2.2.1

    Source: [PAS sushi-config](https://github.com/HL7/davinci-pas/blob/master/sushi-config.yaml)
- The CMS fact sheet for CMS-0057-F recommends (does not require) CRD STU 2.0.1, DTR STU 2.0.0 and PAS STU 2.0.1 — [CMS fact sheet](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f)
- Inferno test kits, all updated 09/08/2026:
  - PAS test kit v0.15.2 targets PAS v2.0.1 and v2.2.1
  - DTR test kit v0.18.0 targets DTR v2.0.1 and v2.2.0
  - CRD test kit v0.14.2 targets CRD STU 2.0.1 and STU 2.2.1

  All three are marked "Low" maturity. Source: [Inferno test kits](https://inferno.healthit.gov/test-kits/)

### Inferences
- For a demo, target CRD 2.2 / DTR 2.2 / PAS 2.2 with US Core 6.1.0 or 7.0.0 profiles. If the product must claim CMS-0057 alignment, it should also be able to state compatibility with 2.0.x (the regulatory recommendation baseline). The Inferno kits allow testing against either.
- In CRD discovery and requests, the CRD version is declared with only two segments, e.g. `"davinci-crd.version": ["2.2"]` (see section 3).

### Gaps
- Exact publication dates of CRD 2.2.1 / DTR 2.2.0 / PAS 2.2.1 could not be retrieved (the history.html pages returned no content through the fetch tool, and hl7.org/packages.fhir.org were blocked from the shell).
- I found no evidence of a newer STU 3 ballot for these IGs as of October 2026, but I could not fully verify ballot listings.

## 2. CDS Hooks: hooks, request structure, and mapping of the proposed flow

### Takeaway
CRD runs on CDS Hooks. The client POSTs `{hook, hookInstance, fhirServer, fhirAuthorization, context, prefetch}` to `{base}/cds-services/{id}`, and discovery is `GET {base}/cds-services`. CRD defines six hooks:

- **Primary** hooks: `order-sign`, `order-dispatch`, `appointment-book`. The server SHALL return a Coverage Information systemAction.
- **Secondary** hooks: `order-select`, `encounter-start`, `encounter-discharge`. Responses are optional and may be ignored.

The proposed flow ("POST Bundle of Patient/ServiceRequest/Coverage for order-select, then submit on order-sign") needs restructuring to be faithful:

- The hook body is **not** a FHIR Bundle. It is a CDS Hooks JSON request.
- The **draft orders** go in `context.draftOrders`, a Bundle of type `collection`.
- **Patient** and **Coverage** go in `prefetch` keyed by the service's prefetch template, or the server fetches them from `fhirServer` using `fhirAuthorization`.
- `order-select` additionally carries `context.selections`.
- `order-sign` is the authoritative call.

### Cited Findings
- **CDS Hooks spec version.** The current published CDS Hooks spec is **v2.0.1 (STU 2 Release 2)**, based on FHIR R4 — [cds-hooks.hl7.org](https://cds-hooks.hl7.org/). CRD 2.2.1 is pinned to `hl7.fhir.uv.cds-hooks` **3.0.0-ballot**, with the hook library at 1.0.1 — [CRD sushi-config](https://github.com/HL7/davinci-crd/blob/master/sushi-config.yaml). CRD says it "relies on enhanced prefetch capabilities newly introduced in the ballot version of CDS Hooks", i.e. a limited FHIRPath in prefetch templates similar to x-fhir-query, and "CRD Clients SHALL be able to parse and execute prefetches that use the simple FHIRPath approach" — [CRD foundation.md](https://github.com/HL7/davinci-crd/blob/master/input/pagecontent/foundation.md) / [published](https://hl7.org/fhir/us/davinci-crd/foundation.html#prefetch)
- **HTTP request fields** — [CDS Hooks](https://cds-hooks.hl7.org/):
  - `hook` (required)
  - `hookInstance` (required; an unguessable UUID)
  - `fhirServer` (conditional; required if `fhirAuthorization` is sent; https in production)
  - `fhirAuthorization` (optional): `access_token`, `token_type`, `expires_in`, `scope`, `subject`, and conditionally `patient`
  - `context` (required)
  - `prefetch` (optional)
- **Endpoints.** Discovery is `GET {baseUrl}/cds-services`. Feedback is `POST {baseUrl}/cds-services/{id}/feedback` with outcome `accepted` or `overridden`, plus `acceptedSuggestions` or `overrideReason` — [CDS Hooks](https://cds-hooks.hl7.org/)
- **Hook list and minimum support.** CRD identifies six hooks: appointment-book, encounter-start, encounter-discharge, order-dispatch, order-select, order-sign. Clients SHALL support at least one hook. Clients that order CRD-supported request types SHALL support order-sign for those order types — [CRD hooks.md](https://github.com/HL7/davinci-crd/blob/master/input/pagecontent/hooks.md) / [published](https://hl7.org/fhir/us/davinci-crd/hooks.html)
- **Primary vs secondary hooks.** The "primary" hooks are appointment-book, order-sign and order-dispatch. Unless reporting an error, or unless coverage info already exists and nothing is new, the server SHALL include a Coverage Information systemAction for these hooks. The "secondary" hooks are order-select, encounter-start and encounter-discharge: they "MAY return cards or system actions, but are not expected to, and CRD clients are free to ignore" them. Coverage info returned for secondary hooks SHALL NOT include messages indicating a need for clinical or administrative information — [CRD hooks.md](https://hl7.org/fhir/us/davinci-crd/hooks.html#hook-categories)
- **order-select.**
  - CRD refers to version 1.0 of the hook, and support is optional.
  - Its value is early caching of back-end queries "before Order Sign is reached" and early guidance.
  - Coverage requirements SHOULD be limited to resources in the `selections` context.
  - Allowed draft order types: CommunicationRequest, DeviceRequest, MedicationRequest, ServiceRequest, NutritionOrder, VisionPrescription.
  - The context SHALL conform to the logical model `CRDOrderSelectContext`.

  Source: [CRD hooks](https://hl7.org/fhir/us/davinci-crd/hooks.html#order-select)
- **order-sign.**
  - Version 1.0 of the hook.
  - "All the listed draft orders are considered 'complete' … appropriate to provide warnings if there is insufficient information." The `selections` field is not used.
  - The context SHALL conform to `CRDOrderSignContext`.
  - The order-sign hook MAY be used for payer attribution.

  Source: [CRD hooks](https://hl7.org/fhir/us/davinci-crd/hooks.html#order-sign)
- **Hook library versions.** The CDS Hooks hook library lists order-select (version 4), order-sign (version 5), order-dispatch (version 0), appointment-book (1), encounter-start (1). These are hook-revision numbers, not maturity — [cds-hooks.hl7.org](https://cds-hooks.hl7.org/)
- **Error codes.**
  - CRD servers SHALL use 400 for unparsable or invalid requests. This includes when the primary Coverage is missing, multiple Coverages are accessible, or the Coverage `payer.identifier` is not handled by that endpoint; an OperationOutcome SHOULD be returned.
  - 422 is used for requests that are valid but violate CRD constraints.
  - Unrecognized context elements SHALL be ignored.

  Source: [CRD hooks](https://hl7.org/fhir/us/davinci-crd/hooks.html)
- **Prefetch content.** Standard prefetch should cover: Patient, the relevant Coverage, the request (if not in context), authoring Practitioner and Organization, requested performer Practitioner and Organization, Location, Medication and Device. "Coverage included in prefetch must be limited to a single instance reflecting the coverage relevant" to the request. CRD clients and servers SHALL support CDS Hooks prefetch — [CRD foundation](https://hl7.org/fhir/us/davinci-crd/foundation.html#prefetch)
- **Exact prefetch template** from the CRD example discovery document (`CRDServices.json`) for `order-sign` (service id `order-sign-crd`); the same template is used for `order-select-crd`:
  ```json
  "prefetch": {
    "patient": "Patient/{{context.patientId}}",
    "encounter": "Encounter/{{context.encounterId}}",
    "coverage": "Coverage?patient={{context.patientId}}&status=active",
    "devices": "Device?_id={{context.draftOrders.entry.resource.ofType(DeviceRequest).code.resolve().id}}",
    "medications": "Medication?_id={{context.draftOrders.entry.resource.ofType(MedicationRequest).medication.resolve().id}}",
    "practitionerRoles": "PractitionerRole?_id={{%encounter.participant.individual.resolve().ofType(PractitionerRole).id|context.draftOrders.entry.resource.requester.resolve().ofType(PractitionerRole).id|...}}",
    "practitioners": "Practitioner?_id={{%practitionerRoles.entry.resource.practitioner.resolve().id|...}}",
    "organizations": "Organization?_id={{%practitionerRoles.entry.resource.organization.resolve().id|...}}",
    "locations": "Location?_id={{%practitionerRoles.entry.resource.location.resolve().id|...}}"
  },
  "extension": { "davinci-crd.version": ["2.2"], "davinci-crd.configuration-options": [ {"code":"coverage-info","type":"boolean","name":"Coverage Information","default":true}, ... ] }
  ```
  Source: [CRD resources/CRDServices.json](https://github.com/HL7/davinci-crd/blob/master/input/resources/CRDServices.json); rendered at [foundation.html#standard-prefetch](https://hl7.org/fhir/us/davinci-crd/foundation.html#standard-prefetch). The `...` marks elided alternates; the full template also checks sender, recipient, performer, orderer and prescriber.
- **Configuration options.**
  - Options listed in discovery for order-sign: `coverage-info`, `insurance`, `duplicate-therapy`, `off-guideline`, `guideline`, `cost`, `claim`, `network`, `appropriate-use`, `therapy-alternatives-opt`, … For order-select, `clinical-reminder` is also listed.
  - The client sends chosen values in the request-level `davinci-crd.configuration` extension.
  - Servers SHALL NOT require configuration and SHALL ignore unsupported options.

  Source: [CRD deviations](https://hl7.org/fhir/us/davinci-crd/deviations.html#new-hook-configuration-mechanism)
- **Version declaration.** The `davinci-crd.version` extension goes in discovery. The `davinci-crd.requestedVersion` extension goes at the root of the request and is required if the service supports multiple versions. Both are limited to "first two nodes" of the version (e.g. 2.2) — [CRD deviations](https://hl7.org/fhir/us/davinci-crd/deviations.html#crd-version-declaration)
- **Example order-sign request**, abridged from `CRDServiceRequest.json`:
  ```json
  {
    "hookInstance": "d5a80646-7ef5-4edf-ade9-72407ca28c76",
    "fhirServer": "http://example.org/some-payer/fhir/crd",
    "hook": "order-sign",
    "fhirAuthorization": {"access_token":"some-opaque-fhir-access-token","token_type":"Bearer","expires_in":300,
       "scope":"user/Patient.read user/Observation.read","subject":"cds-service4","patient":"123"},
    "context": {
      "userId": "Practitioner/ABC", "patientId": "123", "encounterId": "987",
      "draftOrders": { "resourceType": "Bundle", "type": "collection", "entry": [ {
        "fullUrl": "http://example.org/someEHR/fhir/ServiceRequest/2468",
        "resource": { "resourceType": "ServiceRequest", "id": "2468", "status": "draft", "intent": "original-order",
          "code": {"coding":[{"system":"https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets","code":"E0431"}]},
          "subject": {"reference":"http://example.org/fhir/Patient/123"},
          "encounter": {"reference":"http://example.org/fhir/Encounter/987"},
          "authoredOn": "2019-02-15",
          "requester": {"reference":"http://example.org/fhir/PractitionerRole/ABC"} } } ] } },
    "prefetch": { "patient": { "resourceType": "Patient", "id": "123", ... }, "coverage": {...}, ... }
  }
  ```
  - The same example's first ServiceRequest (SNOMED 726551006 mammography) uses the `http://hl7.org/fhir/us/davinci-crd/StructureDefinition/ext-billing-options` extension on `code` to list candidate CPT codes (77061, 77062, 77065, 77066).

  Source: [CRD resources/CRDServiceRequest.json](https://github.com/HL7/davinci-crd/blob/master/input/resources/CRDServiceRequest.json)
- **CRD request logical model.** The general request is profiled as `StructureDefinition-CRDHooksRequest`. The per-hook context models are `CRDOrderSelectContext`, `CRDOrderSignContext`, `CRDOrderDispatchContext`, `CRDAppointmentBookContext`, and the tools-IG `CDSHookEncounterStartContext` / `CDSHookEncounterDischargeContext`. These are CRD 2.2 artifacts — [CRD hooks](https://hl7.org/fhir/us/davinci-crd/StructureDefinition-CRDHooksRequest.html)

### Inferences
- **Mapping the user's flow to the spec:**
  1. **EHR simulator, order entry.** Create a draft `ServiceRequest` (status `draft`, intent `original-order`, CPT 72148 for MRI lumbar spine, `reasonCode` ICD-10-CM). Optionally call `order-select` with `context.selections: ["ServiceRequest/sr1"]` and `context.draftOrders` (Bundle `collection`), for caching or early cards only.
  2. **On "Sign".** Call `order-sign` with `context.{userId, patientId, encounterId, draftOrders}`. Supply Patient and Coverage via `prefetch` (keys `patient`, `coverage`, …) or expose a FHIR server URL plus token. Do not POST a FHIR transaction Bundle to the hook endpoint.
  3. **Payer CRD service.** Return a `systemActions[]` `update` of the ServiceRequest with the `ext-coverage-information` extension (`covered`, `pa-needed=auth-needed`, `doc-needed=clinical`, `questionnaire` canonical, `coverage-assertion-id`), plus optional info cards.
  4. **Launch DTR** (section 4).
  5. **PAS `Claim/$submit`** (section 5).
- For a demo, `order-select` can be a "light" cache-warmer that returns `{"cards": []}`. The authoritative response should come on `order-sign`.

### Gaps
- I could not fetch the hook-library pages (cds-hooks.hl7.org/hooks/...) for the exact field cardinalities of `selections`. From the CDS Hooks order-select definition, `selections` is an array of strings like `"ServiceRequest/123"` and is required for order-select. This should be verified at the hook library: https://cds-hooks.hl7.org/hooks/
- CDS Hooks 3.0 publication status beyond "3.0.0-ballot" was not confirmed.

## 3. CRD response: cards, systemActions, and the coverage-information extension

### Takeaway
The Coverage Information response is **always a systemAction (never a card)** that `update`s the order with the `http://hl7.org/fhir/us/davinci-crd/StructureDefinition/ext-coverage-information` extension. Cards are used for the other response types: External Reference, Instructions, Propose Alternate Request, Identify Additional Orders, Request Form Completion, Update Coverage Records, and Launch SMART App. **DTR is no longer launched via a SMART-link card.** It is triggered by the coverage-information extension (`doc-needed` + `questionnaire`).

### Cited Findings
- **Response types.** CRD defines these response types, with profiles in the form `StructureDefinition-CRDHooksResponse-*`:

  | Response type | Profile |
  |---|---|
  | External Reference | externalReference |
  | Instructions | instructions |
  | Coverage Information | coverageInformation |
  | Propose Alternate Request | alternateRequest |
  | Identify Additional Orders | additionalOrders |
  | Request Form Completion | formCompletion |
  | Update Coverage Records | adjustCoverage |
  | Launch SMART Application | launchSMART |

  All responses SHALL comply with `CRDHooksResponseBase`. Clients and servers SHALL support Coverage Information and SHOULD support the others — [CRD cards.md](https://github.com/HL7/davinci-crd/blob/master/input/pagecontent/cards.md) / [published](https://hl7.org/fhir/us/davinci-crd/cards.html)
- **Card rules** — [CRD cards](https://hl7.org/fhir/us/davinci-crd/cards.html#general-card-and-systemaction-rules):
  - `indicator` is from the clinician's perspective. Most coverage requirements SHOULD be `info`; reimbursement issues are generally `warning`; `critical` is reserved for serious clinical outcomes.
  - `Suggestion.uuid` SHALL be populated.
  - `source.label` SHALL be the insurer name on the patient's card.
  - `source.topic` SHALL be populated, with an extensible binding to the CRD Response Types ValueSet (system `http://terminology.hl7.org/CodeSystem/cdshooks-card-type`).
  - `summary` is at most 140 characters and actionable.
  - Links SHOULD also be in `Card.links` (not only in markdown).
  - Where systemActions are used, equivalent cards SHOULD NOT be returned.
- **Base CDS Hooks card attributes:**
  - `uuid`
  - `summary` (required, under 140 characters)
  - `detail` (GitHub-flavored Markdown)
  - `indicator`: `info` | `warning` | `critical`
  - `source` (`label`, `url`, `icon`, `topic`)
  - `suggestions` (with `selectionBehavior`: `at-most-one` | `any`)
  - `overrideReasons`
  - `links` (`type`: `absolute` | `smart`, plus `appContext`)
  - Action `type`: `create` | `update` | `delete`; delete uses `resourceId`

  Source: [CDS Hooks](https://cds-hooks.hl7.org/)
- **Coverage Information rules** — [CRD cards](https://hl7.org/fhir/us/davinci-crd/cards.html#coverage-information-response-type):
  - It "uses a systemAction to automatically update the order … Regardless of the content, this 'Coverage Information' response type SHALL NOT use a card."
  - Servers SHALL support it for order-sign, order-dispatch and appointment-book.
  - A systemAction SHALL be returned for each in-scope request resource unless nothing new.
  - The update SHALL NOT change any data elements other than the coverage-information extensions.
  - If an Appointment is basedOn a ServiceRequest, the update targets the ServiceRequest.
- **DTR trigger and launch.** If `doc-needed` is indicated, the extension SHOULD reference the questionnaire(s). If DTR is supported, the client SHALL let clinical users launch DTR in the current workflow. "Launching DTR does not necessarily mean launching a SMART on FHIR application" — [CRD cards](https://hl7.org/fhir/us/davinci-crd/cards.html#coverage-information-response-type)
- **Error semantics:**
  - Technical failure → `indeterminate` with reason `technical`.
  - Patient not resolved → `covered=not-covered` with reason `no-member-found`.
  - No active coverage or unresolvable coverage → `not-covered` with `coverage-not-found` or `no-active-coverage`.
  - Missing data is not a hook error; a coverage-information systemAction is still required.

  Source: [CRD cards](https://hl7.org/fhir/us/davinci-crd/cards.html#coverage-information-response-type)
- **Claims linkage.** A claim for an order with a coverage-information extension SHALL carry the `coverage-assertion-id`, as a Request resource attachment to the X12 837, and the `satisfied-pa-id` in the 837 REF Prior Authorization segment — [CRD cards](https://hl7.org/fhir/us/davinci-crd/cards.html#coverage-information-response-type)
- **CMS enforcement discretion in CRD.** On Feb 28, 2024 CMS OBRHI NSG announced enforcement discretion for X12 278 when using the FHIR Prior Authorization API (CMS-0057-F). This "allows payers to return a prior authorization number … in coverage extension of the CRD and DTR IGs", specifically `satisfied-pa-id` — [CRD index.md](https://hl7.org/fhir/us/davinci-crd/index.html#cmsdiscretion); [CMS enforcement letter](https://www.cms.gov/files/document/discretion-x12-278-enforcement-guidance-letter-remediated-2024-02-28.pdf)
- **Extension definition** (`ext-coverage-information`, canonical `http://hl7.org/fhir/us/davinci-crd/StructureDefinition/ext-coverage-information`).
  - Allowed contexts: Appointment, CommunicationRequest, Encounter, DeviceRequest, MedicationRequest, NutritionOrder, QuestionnaireResponse, ServiceRequest, VisionPrescription.
  - Sub-extensions (relative URLs):

    | Sub-extension | Cardinality | Type / binding |
    |---|---|---|
    | `coverage` | 1..1 | Reference(CRDCoverage) |
    | `covered` | 1..1 | code, required VS `coverageInfo`: `covered` \| `not-covered` \| `conditional` \| `indeterminate` |
    | `pa-needed` | 0..1 | code, VS `coveragePaDetail`: `no-auth` \| `auth-needed` \| `satisfied` \| `performpa` \| `conditional` \| `indeterminate` |
    | `doc-needed` | 0..* | code, VS `AdditionalDocumentation`: `clinical` \| `admin` \| `patient` \| `conditional` \| `indeterminate` |
    | `doc-purpose` | 0..* | VS `DocReason`: `withpa` \| `withclaim` \| `withorder` \| `retain-doc` |
    | `info-needed` | 0..* | VS `informationNeeded`: `performer` \| `location` \| `timeframe` \| `contract-window` \| `detail-code` |
    | `billingCode` | 0..* | Coding |
    | `reason` | 0..* | CodeableConcept, extensible VS `coverageAssertionReasons`: `gold-card`, `no-member-found`, `no-active-coverage`, `coverage-not-found`, `auth-out-network`, `technical` |
    | `detail` | 0..* | complex: `category` (`cat-limitation` \| `cat-decisional` \| `cat-other`), `code`, `value` (boolean/string/url/Quantity/Period), `qualification` |
    | `dependency` | 0..* | Reference to another CRD request |
    | `questionnaire` | 0..* | canonical(Questionnaire) |
    | `date` | 1..1 | date |
    | `coverage-assertion-id` | 1..1 | string |
    | `satisfied-pa-id` | 0..1 | string |
    | `contact` | 0..* | |
    | `expiry-date` | 0..1 | |

  - Code systems: `CoverageInformationCodes` (id `coverage-information-codes`) and `CRDTempCodes` (id `temp`).

  Source: [CRD fsh/extensions/CoverageInformation.fsh](https://github.com/HL7/davinci-crd/blob/master/input/fsh/extensions/CoverageInformation.fsh); [CRD codesystems](https://github.com/HL7/davinci-crd/tree/master/input/fsh/codesystems); [published extension](https://hl7.org/fhir/us/davinci-crd/StructureDefinition-ext-coverage-information.html)
- **Key invariants** — [CRD CoverageInformation.fsh](https://github.com/HL7/davinci-crd/blob/master/input/fsh/extensions/CoverageInformation.fsh):
  - **crd-ci-q1:** `questionnaire` implies `doc-needed`.
  - **crd-ci-q2:** `not-covered` implies no `pa-needed`.
  - **crd-ci-q3:** any `conditional` implies `info-needed`.
  - **crd-ci-q5:** `pa-needed=satisfied` if and only if `satisfied-pa-id` is present.
  - **crd-ci-q9:** `indeterminate` implies `reason`.
- **Example systemAction**, verbatim structure from `CRDServiceResponse3.json`:
  ```json
  { "cards": [], "systemActions": [ { "type": "update", "resource": {
      "resourceType": "CommunicationRequest", "id": "example",
      "extension": [ { "url": "http://hl7.org/fhir/us/davinci-crd/StructureDefinition/ext-coverage-information",
        "extension": [
          {"url":"covered","valueCode":"covered"},
          {"url":"pa-needed","valueCode":"no-auth"},
          {"url":"coverage","valueReference":{"reference":"http://example.org/fhir/Coverage/example"}},
          {"url":"date","valueDate":"2022-11-16"},
          {"url":"coverage-assertion-id","valueString":"example-assertion-id-123"} ] } ],
      "status": "draft", ... } } ] }
  ```
  For the demo, the analogous "PA needed + documentation" variant would add `{"url":"pa-needed","valueCode":"auth-needed"}`, `{"url":"doc-needed","valueCode":"clinical"}`, `{"url":"doc-purpose","valueCode":"withpa"}` and `{"url":"questionnaire","valueCanonical":"http://payer.example/fhir/Questionnaire/mri-lumbar|1.0.0"}`. This variant is constructed from the extension definition above, not quoted from the IG. Source: [CRD resources/CRDServiceResponse3.json](https://github.com/HL7/davinci-crd/blob/master/input/resources/CRDServiceResponse3.json)
- **Example cards** from `CRDServiceResponse.json`:
  - A `guideline` card with `links[].type: "absolute"` and card-level extension `"davinci-crd.associated-resource": [{"reference":"ServiceRequest/2468"}]`.
  - A `therapy-alternatives-opt` card with suggestion actions `delete` (`resourceId: "ServiceRequest/2468"`) and `create` (new ServiceRequest E0430 + DeviceRequest).
  - `CRDServiceResponse2.json` shows `therapy-alternatives-req` with `"selectionBehavior": "any"`, and a `clinical-reminder` card with a `create` action for a lab ServiceRequest (CPT 80076).

  Source: [CRD resources](https://github.com/HL7/davinci-crd/tree/master/input/resources)
- **Request Form Completion:**
  - SHALL NOT be used when DTR is applicable and supported by both sides.
  - It uses a Task (profile `profile-taskquestionnaire`) with `Task.code = complete-questionnaire`, `Task.input.type = "questionnaire"` and `Task.input.valueCanonical`.
  - It can be sent as a card or as a systemAction.

  Source: [CRD cards](https://hl7.org/fhir/us/davinci-crd/cards.html#request-form-completion-response-type)
- **Launch SMART App:** a card with `Link.type = "smart"` and `appContext`. "This mechanism is no longer to be used for launching DTR applications. That process is now handled entirely through the Coverage Information response type" — [CRD cards](https://hl7.org/fhir/us/davinci-crd/cards.html#launch-smart-application-response-type)
- **Update Coverage Records:** a card or systemAction that updates Coverage. It SHOULD NOT be sent as a card for clinician-triggered hooks like order-select or order-sign, and SHALL NOT be used where regulation requires X12 270/271 — [CRD cards](https://hl7.org/fhir/us/davinci-crd/cards.html#update-coverage-records-response-type)

### Inferences
- For the demo payer service (e.g., Snowflake Cortex agent behind a CDS service facade), the minimum faithful response on `order-sign` is one `systemActions[]` `update` on the ServiceRequest with the coverage-information extension.
- An optional `info` card (topic `coverage-info` or `guideline`) is reasonable for UX, but CRD says not to duplicate systemAction content in cards. The EHR simulator should render the extension itself (e.g., "PA required – documentation needed – Launch DTR").
- **"Gold carding" / auto-approve:** return `pa-needed=satisfied` + `satisfied-pa-id` (+ optional `reason=gold-card`), which skips PAS entirely.

### Gaps
- The exact `cdshooks-card-type` code list (e.g., `coverage-info`, `guideline`, `therapy-alternatives-opt/req`, `clinical-reminder`, `insurance`, `network`, `cost`, `claim`, `appropriate-use`) was taken from examples and config options, not from the full terminology ValueSet page.

## 4. DTR: $questionnaire-package, questionnaire profiles, CQL prepopulation, QuestionnaireResponse storage, SMART vs native

### Takeaway
DTR clients come in three forms: a **SMART DTR app**, a **Light DTR EHR** or a **Full DTR EHR** (native).

The client authenticates to the payer with **SMART Backend Services** and calls `POST [payer-base]/Questionnaire/$questionnaire-package`:
- **Inputs:** `coverage` (1..1), `order` (0..*), `questionnaire` canonical (0..*), `context` = CRD `coverage-assertion-id` or PAS TRN, and `changedsince`.
- **Output:** a `Parameters` resource with one `packagebundle` Bundle per Questionnaire, each containing Questionnaire + Libraries + ValueSets + a draft QuestionnaireResponse, plus an optional `outcome`.

The client pre-populates answers with CQL/FHIRPath via SDC `initialExpression`, `candidateExpression` and `calculatedExpression`. Adaptive forms use `$next-question`.

A completed QuestionnaireResponse (`dtr-questionnaireresponse`) is saved to the EHR with the `qr-context` / `qr-coverage` / `intendedUse` extensions. It is packaged in a `DTR-QRBundle` (collection, QR first) for PAS attachment.

### Cited Findings
- **Operation `questionnaire-package`** (OperationDefinition `http://hl7.org/fhir/us/davinci-dtr/OperationDefinition/questionnaire-package`):
  - `resource = Questionnaire`, `type = true`, `instance = false`.
  - inputProfile `…/StructureDefinition/dtr-qpackage-input-parameters`; outputProfile `…/dtr-qpackage-output-parameters`.
  - **In:**
    - `coverage` (1..1 Coverage)
    - `order` (0..* Resource: Appointment, Encounter, CommunicationRequest, DeviceRequest, MedicationRequest, NutritionOrder, ServiceRequest, SupplyRequest, VisionPrescription)
    - `questionnaire` (0..* canonical → `dtr-base-questionnaire`)
    - `context` (0..1 string, "Context ID from CRD or CDex")
    - `changedsince` (0..1 instant)
  - **Out:**
    - `packagebundle` (0..* Bundle: "a single Questionnaire, a single QuestionnaireResponse, and 0..* Libraries … and/or ValueSets")
    - `outcome` (0..1 OperationOutcome)

  Source: [DTR fsh/DTROperation-QuestionnairePackage.fsh](https://github.com/HL7/davinci-dtr/blob/master/input/fsh/DTROperation-QuestionnairePackage.fsh) / [published](https://hl7.org/fhir/us/davinci-dtr/OperationDefinition-questionnaire-package.html)
- **Package rules.**
  - The Bundle SHALL include the Questionnaire as the first entry, plus all external Libraries referenced via `cqf-library`.
  - References SHALL be version-specific.
  - The Bundle SHALL contain one initial draft QuestionnaireResponse.
  - The payer MAY pre-populate answers.
  - When resuming, the client SHALL call with the timestamp (`changedsince`).

  Source: [DTR questionnaire-package](https://hl7.org/fhir/us/davinci-dtr/OperationDefinition-questionnaire-package.html)
- **Invocation and auth.**
  - The call is `POST [base]/$questionnaire-package` per payer endpoint, with a `dtr-qpackage-input-parameters` instance.
  - Payers SHALL require SMART on FHIR **Backend Services** auth, with scopes `system/questionnaire.rs`, `system/valueset.rs` and `system/library.rs`.

  Source: [DTR specification](https://github.com/HL7/davinci-dtr/blob/master/input/pagecontent/specification.md) / [published](https://hl7.org/fhir/us/davinci-dtr/specification.html#retrieving-questionnaire-packages)
- **Launch triggers:**
  1. From CRD, when coverage-information indicates info is needed. The `$questionnaire-package` call SHALL pass the `coverage-assertion-id` as `context`.
  2. From PAS, when the 278 response includes LOINC **102089-0** in the HI segment. The associated TRN is the `context`.
  3. Standalone, with orders only.

  Source: [DTR specification – Launch Workflow](https://hl7.org/fhir/us/davinci-dtr/specification.html#launch-workflow)
- **SMART DTR app launch** — [DTR specification](https://hl7.org/fhir/us/davinci-dtr/specification.html#launching-a-dtr-smart-app):
  - Uses SMART EHR launch.
  - openid, user and patient contexts SHALL be provided.
  - `fhirContext` SHOULD include one Coverage, plus exactly one of: a CRD Request/Encounter, an in-progress QuestionnaireResponse, or a CDex Task.
  - Typical scopes: `patient/*.rs` and `patient/QuestionnaireResponse.cu`.
  - Minimum searchable resources: Patient, Coverage, QuestionnaireResponse, Encounter, ServiceRequest, MedicationRequest, DeviceRequest, Appointment, NutritionOrder, VisionPrescription.
- **DTR client types:** Light DTR EHR, Full DTR EHR (CapabilityStatements for US Core 3.1.1 and 6.1/7.0), and SMART DTR Client — [DTR index](https://hl7.org/fhir/us/davinci-dtr/index.html)
- **Profiles:**
  - Questionnaires: `dtr-base-questionnaire` (parent `sdc-questionnaire`), `dtr-std-questionnaire`, `dtr-questionnaire-adapt`, `dtr-questionnaire-adapt-search`.
  - QuestionnaireResponses: `dtr-questionnaireresponse` (parent SDCQuestionnaireResponse), `dtr-questionnaireresponse-adapt`.
  - Bundles: `DTR-QPackageBundle`, `DTR-QRBundle`.
  - Parameters: `dtr-qpackage-input-parameters` / `-output-parameters`, `dtr-next-question-input-parameters` / `-output-parameters`, `dtr-log-errors-input-parameters`.
  - List: `dtr-supported-Payers`.
  - Extensions: `qr-context`, `qr-coverage`, `intendedUse`, `information-origin`, `estimated-completion-time`, `request-specific`, `questionnaireAudience`, `alternativeExpression`, `containedReference`, `activeRole`.

  Source: [DTR fsh](https://github.com/HL7/davinci-dtr/tree/master/input/fsh)
- **Adaptive questionnaires.**
  - The payer returns a Questionnaire conforming to `dtr-questionnaire-adapt-search` with the SDC `questionnaireAdaptive` extension; its URL is where `$next-question` is called.
  - `$next-question` is based on `http://hl7.org/fhir/uv/sdc/OperationDefinition/Questionnaire-next-question`.
  - The QuestionnaireResponse in the package references a contained Questionnaire `derivedFrom` the canonical.
  - `$next-question` passes no context, so needed data must go in answers.
  - A coverage-information extension SHOULD be included on the completed QuestionnaireResponse.

  Source: [DTR spec – Adaptive Form Considerations](https://hl7.org/fhir/us/davinci-dtr/specification.html#adaptive-form-considerations); [DTROperation-NextQuestion.fsh](https://github.com/HL7/davinci-dtr/blob/master/input/fsh/DTROperation-NextQuestion.fsh)
- **Pre-population** — [DTR spec – Pre-Population](https://hl7.org/fhir/us/davinci-dtr/specification.html#pre-population):
  - Questionnaires SHALL include population logic where possible, relying on US Core / HRex elements.
  - DTR uses SDC expression-based population with CQL. Clients SHALL handle CQL and FHIRPath, and SHALL attempt population of `initialExpression`, `candidateExpression` and `calculatedExpression` before showing items.
  - Pre-populated items SHALL set `information-origin` `origin.source` = `auto-server` or `auto-client`. Other codes: `override` and `manual`.
  - Clients SHALL iterate population until a steady state is reached.
- **Example questionnaire.** The DTR example `home-o2-std-questionnaire` (url `http://hl7.org/fhir/us/davinci-dtr/Questionnaire/home-o2-std-questionnaire`) uses:
  - `sdc-questionnaire-initialExpression` with `language = text/fhirpath` (e.g. `today() + 7 days`)
  - an `alternativeExpression` with `application/elm+json`
  - extensions `audience = clinical`, `request-specific`, `sdc-questionnaire-entryMode = sequential`, `estimated-completion-time`

  There is also a narrative page `resources__home-o2-prepopulation.md`. Source: [DTR examples](https://github.com/HL7/davinci-dtr/tree/master/input/fsh/examples)
- **Storage and downstream use** — [DTR spec – Storing / Passing](https://hl7.org/fhir/us/davinci-dtr/specification.html#storing-questionnaireresponses):
  - The client SHALL be able to save `in-progress` QuestionnaireResponses and SHALL save `completed` ones to the EHR (create, then update).
  - Downstream use is via `qr-coverage`, `qr-context` and `intendedUse`.
  - Coverage-information on the QuestionnaireResponse SHALL be propagated to the context resources.
  - For conveyance to a payer, the QuestionnaireResponse goes in a collection Bundle per `DTR-QRBundle`, with the QuestionnaireResponse first and answerReference targets included.
  - Search for existing responses: `[EHR-base]/QuestionnaireResponse?patient=123&context=ServiceRequest/789`, using the `qr-context` SearchParameter.

### Inferences
- **Simplest faithful demo:** a "Full DTR EHR" (native renderer inside the EHR simulator) or a lightweight SMART app.
  1. Read `questionnaire` + `coverage-assertion-id` from the ServiceRequest's coverage-information extension.
  2. Call the payer's `$questionnaire-package`.
  3. Render with an SDC renderer and run FHIRPath/CQL prepopulation against the EHR FHIR server.
  4. Save the QuestionnaireResponse with `qr-context` → ServiceRequest.
  5. Attach it to PAS.
- An adaptive questionnaire with `$next-question` is a natural fit for an LLM/agent-driven payer (Cortex). Each next question can be generated server-side, and a final coverage-information extension (e.g., `satisfied` + `satisfied-pa-id`) can be returned in the completed QuestionnaireResponse.

### Gaps
- I did not extract a verbatim Parameters JSON example for the `$questionnaire-package` input or output. One exists in `Examples-Parameters.fsh` / `Examples-QuestionnairePackageOperationResult.fsh` in the DTR repo.
- I did not verify the CQL version/library details (CQL N1 is stated; ELM requirements were not checked).

## 5. PAS: Claim/$submit, bundle contents, ClaimResponse/reviewAction, $inquire, pended + Subscriptions, X12 278 and regulation

### Takeaway
The client POSTs a JSON `PASRequestBundle` (Bundle type `collection`) to **`[base]/Claim/$submit`**:
- The first entry is a `PASClaim` with `use = preauthorization`.
- It is followed by every referenced resource: Patient (`PASBeneficiary`), Coverage, insurer/UMO Organization, PractitionerRole/Practitioner, ServiceRequest, Location, and supporting info such as DocumentReference or the **US Core QuestionnaireResponse** from DTR via `supportingInfo[AdditionalInformation]`.

The synchronous response is a `PASResponseBundle` whose first entry is a `PASClaimResponse`. The decision is in `ClaimResponse.item.adjudication.extension(reviewAction).extension(code)`, using X12 code list 306:

| Code | Meaning |
|---|---|
| A1 | Certified in total |
| A3 | Not Certified |
| A4 | Pending |
| A6 | Modified |

The authorization number is in `reviewAction.number`. Pended results are delivered by R4 backport **Subscription** (rest-hook, topic `PASSubscriptionTopic`). `Claim/$inquire` is for other parties and manual checks.

### Cited Findings
- **Operations.** `Claim-submit` (`http://hl7.org/fhir/us/davinci-pas/OperationDefinition/Claim-submit`, code `submit`, resource Claim, type-level) and `Claim-inquiry` (`…/OperationDefinition/Claim-inquiry`, code **`inquire`**, type-level) — [PAS ClaimOperation.fsh](https://github.com/HL7/davinci-pas/blob/master/input/fsh/ClaimOperation.fsh); [published submit](https://hl7.org/fhir/us/davinci-pas/OperationDefinition-Claim-submit.html)
- **Profile ids:**

  | Kind | Profile id |
  |---|---|
  | Request Bundle | `profile-pas-request-bundle` |
  | Response Bundle | `profile-pas-response-bundle` |
  | Inquiry Request Bundle | `profile-pas-inquiry-request-bundle` |
  | Inquiry Response Bundle | `profile-pas-inquiry-response-bundle` |
  | Claim | `profile-claim` (abstract base `profile-claim-base`) |
  | Claim Update | `profile-claim-update` |
  | Claim Inquiry | `profile-claim-inquiry` |
  | ClaimResponse | `profile-claimresponse` (abstract base `profile-claimresponse-base`) |
  | Claim Inquiry Response | `profile-claiminquiryresponse` |
  | DocumentReference | `profile-documentreference` (parent US Core DocumentReference 7.0.0) |
  | Task | `profile-task` |
  | Subscription | `profile-subscription` |

  Source: [PAS fsh](https://github.com/HL7/davinci-pas/tree/master/input/fsh); [PAS artifacts](https://hl7.org/fhir/us/davinci-pas/fhirArtifacts.html)
- **Submission rules** — [PAS specification](https://hl7.org/fhir/us/davinci-pas/specification.html#prior-authorization-submission):
  - The Bundle "SHALL be encoded in JSON" and "the first entry … SHALL be a Claim resource" sufficient to populate X12N/005010X217.
  - Every referenced resource SHALL be included, with full traversal and each instance at most once.
  - `fullUrl` is either the EHR REST URL or `urn:uuid:`, and GUIDs are unique.
  - Supporting-information resources (DTR or otherwise) must be included and SHALL comply with US Core where applicable.
- **Claim profile constraints:**
  - `status = active`, `use = #preauthorization`
  - `patient` only `PASBeneficiary`; `insurer` 1..1 `PASInsurer`; `provider` `PASRequestor` or `PASPractitionerRole`
  - `careTeam` sliced, with X12-bound role and qualification
  - Extensions: `transmissionIdentifiers`, `levelOfServiceType`, `conditionCode`, `homeHealthCareInformation`, `authorizationNumber`, `administrationReferenceNumber`
  - `supportingInfo` slices: `PatientEvent`, `AdmissionDates`, `DischargeDates`, `AdditionalInformation`, `MessageText`
  - `supportingInfo[AdditionalInformation]`: `category = PASTempCodes#additionalInformation`, a required `documentInformation` extension, and `valueReference` only `PASDocumentReference` or `$USCoreQuestionnaireResponse` or … (other types)

  Source: [PAS Claim.fsh](https://github.com/HL7/davinci-pas/blob/master/input/fsh/Claim.fsh)
- **Example request Bundle** (`ReferralAuthorizationBundleExample`):
  - Bundle `identifier` (submitter transaction id), `type = collection`, `timestamp`.
  - Entries in order: Claim, UMO Organization, Insurer Organization, Coverage, Patient (Subscriber), ServiceRequest, PractitionerRole, Practitioner, Location, DocumentReference.
  - The Claim has:
    - `type = claim-type#professional`, `use = preauthorization`, `priority = processpriority#normal`
    - `diagnosis.diagnosisCodeableConcept = http://hl7.org/fhir/sid/icd-10-cm#G89.4`
    - `insurance.focal = true`
    - `item.extension[requestType] = https://codesystem.x12.org/005010/1525#SC`
    - `item.extension[certificationType] = …/1322#I` (Initial)
    - `item.extension[requestedService] = Reference(ServiceRequest)`
    - `item.productOrService = https://codesystem.x12.org/005010/1365#3 "Consultation"`
    - `item.locationCodeableConcept` = CMS Place of Service `#11`
    - `extension[levelOfServiceType] = …/1338#U`
    - `supportingInfo[AdditionalInformation]` with `documentInformation` (`reportTypeCode …/755#PY`, `transmissionMethod …/756#EL`)

  Source: [PAS Examples.fsh](https://github.com/HL7/davinci-pas/blob/master/input/fsh/Examples.fsh); [published](https://hl7.org/fhir/us/davinci-pas/Bundle-ReferralAuthorizationBundleExample.html)
- **Response.**
  - The response Bundle SHALL start with a ClaimResponse.
  - `ClaimResponse.request` (1..1, `PASClaim`, data-absent-reason allowed) references the Claim.
  - Pended / denied / successful "depends on the review action code … ClaimResponse.item.adjudication.extension(reviewaction).code".
  - Items SHALL echo `item.sequence`.
  - Modified authorizations: the requested item returns with **A6 'Modified'** and the authorized details go in `ClaimResponse.addItem` linked by `itemSequence`.

  Source: [PAS specification – Prior Authorization Response](https://hl7.org/fhir/us/davinci-pas/specification.html#prior-authorization-response)
- **reviewAction extension** (`http://hl7.org/fhir/us/davinci-pas/StructureDefinition/extension-reviewAction`):
  - Sub-extensions: `code` (`extension-reviewActionCode`, bound to `https://valueset.x12.org/x217/005010/response/2000F/HCR/1/01/00/306`), `number` (string), `reasonCode` (X12 278 Review Decision Reason Code), `secondSurgicalOpinionFlag`.
  - Contexts: `ClaimResponse.adjudication`, `item.adjudication`, `addItem.adjudication`.
  - Other item extensions: `itemPreAuthIssueDate`, `itemPreAuthPeriod`, `itemRequestedServiceDate`, `itemAuthorizedDetail`, `itemAuthorizedProvider`, `itemTraceNumber`, `administrationReferenceNumber`.

  Source: [PAS ClaimResponse.fsh](https://github.com/HL7/davinci-pas/blob/master/input/fsh/ClaimResponse.fsh)
- **Approved example** (`PractitionerRequestorResponseExample`):
  ```
  outcome = #complete; use = #preauthorization; request = Reference(Claim)
  item.itemSequence = 1
  item.extension[preAuthIssueDate].valueDate = 2005-05-02
  item.extension[preAuthPeriod].valuePeriod = 2005-05-02..2005-06-02
  item.adjudication.category = http://terminology.hl7.org/CodeSystem/adjudication#submitted
  item.adjudication.extension[reviewAction].extension[number].valueString = "AUTH0001"
  item.adjudication.extension[reviewAction].extension[code].valueCodeableConcept = https://codesystem.x12.org/005010/306#A1 "Certified in total"
  ```
  - The **pended** example uses `…/306#A4 "Pending"` with `item.extension[administrationReferenceNumber] = "PEND0001"`.
  - The **denied** example uses `…/306#A3 "Not Certified"`.

  Source: [PAS Examples.fsh](https://github.com/HL7/davinci-pas/blob/master/input/fsh/Examples.fsh); [approved bundle](https://hl7.org/fhir/us/davinci-pas/Bundle-ReferralAuthorizationResponseBundleExample.html), [pended bundle](https://hl7.org/fhir/us/davinci-pas/Bundle-ReferralPendingAuthorizationResponseBundleExample.html), [denied bundle](https://hl7.org/fhir/us/davinci-pas/Bundle-RejectionResponseBundleExample.html)
- **HTTP semantics.** "All transactions in PAS are synchronous" and SHALL return:
  - 2XX on success
  - 4XX (not recoverable) with an OperationOutcome
  - 5XX (temporary) with no OperationOutcome

  Processing "SHOULD happen synchronously". If a final answer is not possible in the required timeframe, items are returned 'pended' — [PAS specification](https://hl7.org/fhir/us/davinci-pas/specification.html#http-responses)
- **Pended + Subscription** — [PAS specification – Subscription](https://hl7.org/fhir/us/davinci-pas/specification.html#subscription):
  - Implementers SHALL support subscriptions, using the R4 Subscriptions Backport IG with the **rest-hook** channel only.
  - The one topic is `http://hl7.org/fhir/us/davinci-pas/SubscriptionTopic/PASSubscriptionTopic`.
  - The client POSTs a `profile-subscription` Subscription with filter `org-identifier = [sending system identifier]`, equivalent to ISA06. The subscription is per sending system, not per request.
  - Notifications SHALL include the full PAS Response Bundle.
  - `$inquire` SHOULD NOT be used by the submitter while waiting.
  - Non-submitting systems (performer, patient) use `$inquire`; payers SHALL match on member id plus provider NPI.
- **Inquiry:**
  - The request is a `PASInquiryRequestBundle` with a `PASClaimInquiry` first ("query-by-example").
  - REF-NT / REF-BB identifiers are used to target a specific authorization, and `productOrService` `not-applicable` is used for non-specific inquiries.
  - The request maps to a 278 inquiry; the response is 0..* `PASInquiryResponseBundle`, each with a `PASClaimInquiryResponse` first.

  Source: [PAS specification – Inquiries](https://hl7.org/fhir/us/davinci-pas/specification.html#prior-authorization-inquiries)
- **Updates and cancellations:**
  - Re-`$submit` with a `PASClaimUpdate` first; `Claim.related.claim` references the prior Claim.
  - Changed items are flagged with the `infoChanged` extension. Cancelled items use the modifierExtension `infoCancelled = true` plus `certificationType` code 3 (Cancel).

  Source: [PAS specification – Updating](https://hl7.org/fhir/us/davinci-pas/specification.html#updating-authorization-requests)
- **Additional information requests.** The payer can request more information through the 278 response, using PWK01 codes, LOINC attachment codes, or a single LOINC **102089-0** (payer questionnaire). The TRN associated with 102089-0 SHALL be the DTR context ID. The PAS Task profile conveys this to CDex (`Task.code` `attachment-request-code` or `attachment-request-questionnaire`), and the response returns via CDex `$submit-attachment` — [PAS additionalinfo](https://hl7.org/fhir/us/davinci-pas/additionalinfo.html)
- **X12 relationship.** "The system on which the operation is invoked will convert the Bundle into an ASC X12N 278 and 0..* additional unsolicited 275 transactions … then take the resulting 278 response and convert it into a response FHIR Bundle." Everything beyond the endpoint is a "black box" (intermediaries/clearinghouses). Mapping is to be published by ASC X12N. The CMS-exception processing guidance is on [HL7 Confluence – PAS Exception Guidance](https://confluence.hl7.org/display/DVP/PAS+Exception+Guidance), which is still marked as in progress — [PAS specification](https://hl7.org/fhir/us/davinci-pas/specification.html#summary)
- **CMS-0057-F:**
  - The Prior Authorization API must be implemented beginning **January 1, 2027**.
  - Operational provisions apply from **January 1, 2026**: decision timeframes of **72 hours expedited** and **7 calendar days standard**, specific denial reasons, and public metrics, with initial metrics due March 31, 2026.
  - Impacted payers: MA, Medicaid/CHIP FFS and managed care, and QHPs on FFEs (QHPs are excluded from the timeframes).
  - HHS will not enforce X12 278 against entities using an all-FHIR PA API.

  Source: [CMS fact sheet](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f); [CMS enforcement discretion letter, Feb 28 2024](https://www.cms.gov/files/document/discretion-x12-278-enforcement-guidance-letter-remediated-2024-02-28.pdf)

### Inferences
- **Demo payer `$submit`:**
  1. Validate the Bundle.
  2. Run the Cortex agent decision over Claim + ServiceRequest + QuestionnaireResponse.
  3. Return a `PASResponseBundle` with `ClaimResponse.outcome = complete` and `item.adjudication.extension[reviewAction]` set to A1 (with `number` as the auth number and `preAuthPeriod`), A3 (with `reasonCode`), or A4 (pended, with `administrationReferenceNumber`).
  4. For pended cases, later POST a notification Bundle containing the full PAS Response Bundle to the EHR simulator's rest-hook endpoint.
- Because of the CMS enforcement discretion, an all-FHIR demo without X12 translation is a legitimate architecture. The black-box principle allows the Snowflake payer back end to act as the "intermediary".
- **Note on the term "preAuthRef":** in R4 `ClaimResponse.preAuthRef` exists at the root, but PAS examples carry the auth number in `item.adjudication.extension[reviewAction].extension[number]` and the `authorizationNumber` extension. A demo should populate `reviewAction.number` at minimum. Whether PAS constrains root `preAuthRef` was not checked.

### Gaps
- I found no explicit "15-second" response time requirement in PAS 2.2.1 text. The spec says only "SHOULD happen synchronously" / "within the required timeframe", so a 15-second figure should not be asserted without another source.
- The full X12 306 code list beyond A1/A3/A4/A6 (e.g., A2 "Certified – partial", C "Cancelled", CT "Contact Payer", NA "No Action Required") is X12-licensed and was not verified here; codes beyond A1, A3, A4 and A6 should be treated as unverified.
- The exact fields of `PASSubscriptionTopic` (resourceTrigger on ClaimResponse, plus a Bundle trigger) were only partially seen.

## 6. FHIR validation approach

### Takeaway
Validate every exchanged payload against the IG packages:
- `hl7.fhir.us.davinci-crd#2.2.1`
- `hl7.fhir.us.davinci-dtr#2.2.0`
- `hl7.fhir.us.davinci-pas#2.2.1`
- `hl7.fhir.us.core#7.0.0` (or 6.1.0)

You can use the HL7 FHIR Validator CLI (`validator_cli.jar`) or HAPI FHIR's `FhirInstanceValidator` with an `NpmPackageValidationSupport` loaded from packages.fhir.org. Note that CDS Hooks request and response JSON is not a FHIR resource. Validate the embedded resources (draftOrders entries, prefetch, systemAction resources) against FHIR profiles, and validate the hook envelope against the CRD logical models.

### Cited Findings
- **Canonical profile URLs to validate against:**
  - PAS Bundle: `http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-pas-request-bundle`
  - PAS Claim: `…/profile-claim`
  - PAS ClaimResponse Bundle: `…/profile-pas-response-bundle`
  - DTR QuestionnaireResponse: `http://hl7.org/fhir/us/davinci-dtr/StructureDefinition/dtr-questionnaireresponse`
  - DTR QR Bundle: `…/DTR-QRBundle`
  - CRD resource profiles from the CRD pagecontent intros:
    - `profile-servicerequest`, `profile-coverage`, `profile-patient`, `profile-encounter`
    - `profile-devicerequest`, `profile-medicationrequest`, `profile-communicationrequest`, `profile-nutritionorder`, `profile-visionprescription`
    - `profile-organization`, `profile-location`, `profile-device`
    - `profile-appointment-with-order`, `profile-appointment-no-order`, `profile-taskquestionnaire`

  Source: [PAS fsh](https://github.com/HL7/davinci-pas/tree/master/input/fsh); [DTR fsh](https://github.com/HL7/davinci-dtr/tree/master/input/fsh); [CRD pagecontent](https://github.com/HL7/davinci-crd/tree/master/input/pagecontent)
- **CRD client conformance.** CRD clients SHALL ensure data in the hook invocation complies with the listed profiles. CRD servers SHALL NOT depend on data not covered by the identified profiles — [CRD hooks](https://hl7.org/fhir/us/davinci-crd/hooks.html)
- **HAPI validator service.** The HAPI `org.hl7.fhir.validator-wrapper` repo exists (`hapifhir/org.hl7.fhir.validator-wrapper`); it wraps the HL7 validator as a web service/UI. Repo existence was confirmed via git ls-remote — [GitHub](https://github.com/hapifhir/org.hl7.fhir.validator-wrapper)

### Inferences
- **Typical CLI usage**, from general knowledge of the HL7 validator; verify the flags against current docs:
  ```
  java -jar validator_cli.jar pas-request.json -version 4.0.1 \
    -ig hl7.fhir.us.davinci-pas#2.2.1 -ig hl7.fhir.us.core#7.0.0 \
    -profile http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-pas-request-bundle \
    -tx n/a   # or default tx.fhir.org; CPT/X12 codes are not resolvable on public tx
  ```
  The jar is published at github.com/hapifhir/org.hl7.fhir.core releases.
- In HAPI (Java): build a `ValidationSupportChain` of `DefaultProfileValidationSupport`, `NpmPackageValidationSupport` (`loadPackageFromClasspath` or from downloaded `.tgz`), `CommonCodeSystemsTerminologyService`, `InMemoryTerminologyServerValidationSupport` and `SnapshotGeneratingValidationSupport`, then wrap it in `FhirInstanceValidator`.
- Python alternatives (e.g., `fhir.resources`) validate base R4 structure only, not IG profiles. For profile validation from Snowflake/Python, call a validator-wrapper HTTP service.
- Expect terminology warnings for CPT (licensed), X12 code lists (`codesystem.x12.org`) and NUCC. Configure them to be ignored or treat them as warnings in the demo.

### Gaps
- The HL7 Confluence "Using the FHIR Validator" page was blocked by robots, so the exact current CLI flags are not cited from a primary source.
- I did not verify the latest validator_cli version number.

## 7. Reference implementations, test kits, sandboxes, synthetic data, example questionnaires

### Takeaway
The HL7-DaVinci "DRLS" stack provides working open-source pieces:

| Repo | Role |
|---|---|
| `CRD` | Java CDS service with a rules library |
| `test-ehr` | HAPI-based EHR FHIR server |
| `crd-request-generator` | React EHR simulator UI |
| `dtr` | SMART DTR app |
| `CDS-Library` | Questionnaires/CQL for DME use cases such as Home Oxygen and PAP devices |
| `prior-auth` | PAS RI, Spring Boot on `localhost:9015/fhir/Claim/$submit` |

Live demos are on HL7 FHIR Foundry. Inferno provides test kits for CRD, DTR and PAS at 2.0.x and 2.2.x.

### Cited Findings
- **CRD RI** (`HL7-DaVinci/CRD`) — [GitHub CRD](https://github.com/HL7-DaVinci/CRD):
  - The `server` component is a Java CDS service acting as the payer; rules come from the `CDS-Library` repo.
  - The repo also contains `examples`, `resources` and `testingClient`.
  - Related repos: `test-ehr` (FHIR server for non-prefetched queries), `crd-request-generator` (React/Node UI that builds requests and displays cards), and `dtr` (SMART app).
  - Build with JDK 8 / Gradle 6.3 (`gradle build`); optional Keycloak OAuth on port 8180.
  - Live demo: HL7 FHIR Foundry `foundry.hl7.org/products/f03f9ffa-83b1-43fd-a4d7-4641d72e275c`.
  - A docker image `hlseven/davinci-crd` is listed on Docker Hub — [Docker Hub](https://hub.docker.com/r/hlseven/davinci-crd)
- **PAS RI** (`HL7-DaVinci/prior-auth`) — [GitHub prior-auth](https://github.com/HL7-DaVinci/prior-auth):
  - Requires Java JDK 11. Run with `./gradlew embedCdsLibrary`, `./gradlew installBootDist`, `./gradlew bootRun`.
  - Endpoints: `http://localhost:9015/fhir/metadata`, `/Bundle`, `/Claim`, `/ClaimResponse`, and `POST /fhir/Claim/$submit` with `src/test/resources/bundle-prior-auth.json`.
  - Debug mode is `bootRun --args='debug'`.
  - Live demo on FHIR Foundry `foundry.hl7.org/products/0ae47685-cc05-4134-a326-e5a80c8a2b55`.
  - The README notes it expects HTTPS and a LogicaHealth tokenUri by default.
- **Repos confirmed to exist** (via git ls-remote, 2026-10-18): `HL7-DaVinci/prior-auth`, `HL7-DaVinci/dtr`, `HL7-DaVinci/test-ehr`, `HL7-DaVinci/crd-request-generator`, `HL7-DaVinci/CDS-Library`, `inferno-framework/davinci-crd-test-kit`, `inferno-framework/davinci-dtr-test-kit`, `inferno-framework/davinci-pas-test-kit` — [github.com/HL7-DaVinci](https://github.com/HL7-DaVinci), [github.com/inferno-framework](https://github.com/inferno-framework)
- **CDS-Library questionnaire/rule sets.** The `CDS-Library` `CRD-DTR` folder contains HomeBloodGlucoseMonitor, HomeHealthServices, **HomeOxygenTherapy**, HospitalBedsAndAccessories, ImmunosuppressiveDrugs, NonEmergencyAmbulanceTransportation, **PositiveAirwayPressureDevices** (CPAP), RespiratoryAssistDevices, UrologicalSupplies, Ventilators and Shared. Top-level folders: CRD-DTR, Examples, PriorAuth, RuleUtils — [GitHub CDS-Library](https://github.com/HL7-DaVinci/CDS-Library)
- **Inferno test kits** — [Inferno test kits](https://inferno.healthit.gov/test-kits/); [PAS kit client instructions v2.2.1](https://github.com/inferno-framework/davinci-pas-test-kit/wiki/Client-Instructions-v2.2.1); [ONC blog on PAS test kit](https://healthit.gov/blog/interoperability/enhancing-healthcare-interoperability-launching-the-davinci-prior-authorization-support-pas-test-kit/):
  - CRD v0.14.2: client and server
  - DTR v0.18.0: provider and payer
  - PAS v0.15.2: client and server
  - Each targets 2.0.x and 2.2.x, maturity "Low"
- **IG example resources:**
  - CRD: `CRDServiceRequest*.json`, `CRDServiceResponse*.json`, `CRDServices.json`
  - DTR: home-oxygen standard and adaptive questionnaires, Questionnaire Package Bundle, QR Bundle, Parameters
  - PAS: referral, homecare, update, approved, pended and denied bundles

  Source: [CRD resources](https://github.com/HL7/davinci-crd/tree/master/input/resources); [DTR examples](https://github.com/HL7/davinci-dtr/tree/master/input/fsh/examples); [PAS Examples.fsh](https://github.com/HL7/davinci-pas/blob/master/input/fsh/Examples.fsh)
- A community "Setting up CRD/DTR/PAS" PDF was posted on chat.fhir.org — [chat.fhir.org upload](https://chat.fhir.org/user_uploads/10155/MD566nzochvz2rIbEd48QCEh/Setting-up-CRD_DTR_PAS-2.pdf). Its content was not reviewed.

### Inferences
- **Fastest demo path:** run `test-ehr` (or any HAPI R4 server) loaded with Synthea US Core patients as the EHR FHIR server, and use `crd-request-generator` as the starting point for the EHR simulator UI. Replace the CRD rules engine and PAS adjudication with Snowflake/Cortex-backed services exposing the same CDS Hooks and `Claim/$submit` interfaces.
- **Validation:** point the Inferno CRD/DTR/PAS server-side tests at the demo payer endpoints.
- **Imaging (MRI lumbar 72148):** the IG libraries focus on DME (O2, CPAP). No ready-made imaging questionnaire was found in CDS-Library's folder listing, so a custom SDC Questionnaire would be authored. Typical lumbar-MRI criteria are red flags, at least 6 weeks of conservative therapy, and neuro deficits.

### Gaps
- Synthea was not researched in this pass; it is well known to generate US Core-like R4 bundles, but no source was fetched.
- I did not verify the current public sandboxes' availability (Logica sandbox shutdown status, FHIR Foundry uptime).
- I did not check whether the DRLS repos are actively maintained for 2.2.x or remain on 2.0.x.

## 8. Code systems commonly used

### Takeaway
Use these systems:

| Concept | System URI |
|---|---|
| CPT | `http://www.ama-assn.org/go/cpt` |
| HCPCS | `https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets` |
| ICD-10-CM | `http://hl7.org/fhir/sid/icd-10-cm` |
| X12 code lists | `https://codesystem.x12.org/005010/{list#}`, e.g. 306 review action, 1525 request type, 1322 certification type, 1338 level of service, 1365 service type, 755/756 attachment report type and transmission |
| CMS Place of Service | `https://www.cms.gov/Medicare/Coding/place-of-service-codes/Place_of_Service_Code_Set` |
| CDS card types | `http://terminology.hl7.org/CodeSystem/cdshooks-card-type` |

### Cited Findings
- **CPT and HCPCS systems as used in CRD examples:**
  - CPT system `http://www.ama-assn.org/go/cpt` (codes 77061/77062/77065/77066, 80076)
  - HCPCS system `https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets` (E0431 / E0430 portable oxygen)

  Source: [CRD CRDServiceRequest.json](https://github.com/HL7/davinci-crd/blob/master/input/resources/CRDServiceRequest.json)
- **PAS example code systems:**
  - ICD-10-CM `http://hl7.org/fhir/sid/icd-10-cm#G89.4`
  - X12 `https://codesystem.x12.org/005010/306#A1` "Certified in total", `#A3` "Not Certified", `#A4` "Pending"
  - A6 "Modified", per the PAS spec text
  - `…/1525#SC` "Specialty Care Review", `…/1322#I` "Initial", `…/1338#U` "Urgent", `…/1365#3` "Consultation"
  - `…/755#PY` "Physician's Report", `…/756#EL` "Electronically Only"
  - CMS POS `#11` (Office)

  Source: [PAS Examples.fsh](https://github.com/HL7/davinci-pas/blob/master/input/fsh/Examples.fsh); [PAS specification](https://hl7.org/fhir/us/davinci-pas/specification.html#returning-authorized-items-that-are-different-from-what-was-requested)
- **X12 ValueSet binding.** The review action code is bound to the X12 ValueSet URL `https://valueset.x12.org/x217/005010/response/2000F/HCR/1/01/00/306` — [PAS ClaimResponse.fsh](https://github.com/HL7/davinci-pas/blob/master/input/fsh/ClaimResponse.fsh)
- **NUCC taxonomy.** CRD defines a `NUCCHealthcareProviderTaxonomy` ValueSet and an `X12278RequestedServiceType` ValueSet. The PAS careTeam qualification is bound to X12 list 127 (provider specialty) — [CRD valuesets](https://github.com/HL7/davinci-crd/tree/master/input/fsh/valuesets); [PAS Claim.fsh](https://github.com/HL7/davinci-pas/blob/master/input/fsh/Claim.fsh)
- **LOINC 102089-0** is used in PAS 278 responses to request a payer questionnaire via DTR — [PAS additionalinfo](https://hl7.org/fhir/us/davinci-pas/additionalinfo.html)

### Inferences
- For the MRI demo:
  - `ServiceRequest.code`: CPT 72148 ("MRI lumbar spine without contrast"); this is common knowledge and was not verified from AMA here.
  - `reasonCode`: ICD-10-CM, e.g. M54.16 (radiculopathy, lumbar region) or M54.50 (low back pain, unspecified, FY2022+); also not verified here.
  - PAS `Claim.item.productOrService`: the same CPT code.
  - `Claim.item.category`: X12 1365 service type, e.g. code for diagnostic imaging (verify in the X12 list).
- Use NUCC taxonomy (`http://nucc.org/provider-taxonomy`) on PractitionerRole.specialty, e.g. 2085R0202X Diagnostic Radiology (verify).

### Gaps
- CPT 72148 and the ICD-10-CM example code descriptions were not verified against AMA/CMS sources in this session.
- The X12 service-type code for MRI/imaging was not verified, since X12 lists are licensed.
- The NUCC system URI and the radiology taxonomy code were not verified.
