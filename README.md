# AuthBridge

Electronic prior authorization (ePA) for the Snowflake hackathon. A clinic (EHR simulator) and a health plan talk to each other with the HL7 Da Vinci standards: CRD for coverage requirements, DTR for documentation and PAS for submission. Snowflake holds every record and payer rule and runs the AI; the app tier runs on your laptop.

Product requirements: [docs/AuthBridge_PRD.md](docs/AuthBridge_PRD.md). All patients and policies here are synthetic.

```
Browser ─► Next.js UI :3000 ──► Provider service :8001 ──CRD/DTR/PAS──► Payer service :8002
                                  (EHR simulator)    ◄──notification──   (CDS Hooks + FHIR)
                                        │                                      │
                                        └──────────── Snowflake ───────────────┘
                     CORE / PROVIDER tables, AI.SP_DTR_AUTOFILL   PAYER tables, SP_CRD_EVALUATE, SP_PAS_SUBMIT,
                                                                  SP_RECORD_DECISION, Cortex Search, Cortex Agents
```

## Run it in 2 minutes (no Snowflake needed)

The default `mock` mode keeps data in memory and uses a pattern-based stand-in for the AI, so you can build the UI and rehearse the demo offline.

```bash
cp .env.example .env
docker compose up --build
# open http://localhost:3000
```

Without Docker (needs Python 3.11+ and Node 20+):

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r services/requirements-dev.txt
cp .env.example .env
./dev.sh payer      # terminal 1
./dev.sh provider   # terminal 2
cd ui && npm install && npm run dev   # terminal 3
./dev.sh test       # 12 end-to-end tests across all demo scenarios
```

When running without Docker, change the `*_PRIVATE_KEY_PATH` values in `.env` from `/secrets/...` to `./secrets/...` (relative to `services/`, so `../secrets/...`).

## Demo script

| Clinic step | Patient | Order | What happens |
|---|---|---|---|
| No PA needed | any | X-ray lumbar spine (72100) | CRD returns `no-auth` at signing |
| Gold card | James Carter, ordering as **Dr. Vikram Rao** | MRI lumbar spine (72148) | CRD returns `satisfied` with a PA number |
| Real-time approval | Maria Gonzalez | CPAP (E0601) | AI fills AHI 22 and the face-to-face visit with quotes → A1 |
| Pend, then approve | James Carter, as Dr. Anita Patel | MRI lumbar spine | 3 weeks of conservative care → A4 asks for therapy notes → attach the PT re-evaluation → resubmit → A1 |
| Red flag | Linda Nguyen | MRI lumbar spine, urgent | Saddle anesthesia quote → A1 |
| Clinician review | Robert Hughes | Oxygen concentrator (E1390) | SpO2 92/90/91 → "Recommend deny" → Health plan → case → only Dr. Chen (medical director) can deny → clinic is notified → "Draft an appeal" |
| Drug PA | Susan Miller | Semaglutide (MedicationRequest, route and duration) | 3.1% weight loss → clinician review |

Every order page has a **FHIR messages** drawer showing the real CDS Hooks requests, `$questionnaire-package`, PAS Bundles and notifications.

## Connect Snowflake

1. **Keys.** Create two key pairs and put the private keys in `secrets/` (git-ignored):
   ```bash
   openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out secrets/payer_key.p8 -nocrypt
   openssl rsa -in secrets/payer_key.p8 -pubout -out secrets/payer_key.pub
   # repeat for provider_key
   ```
2. **Setup.** Edit the placeholders in `snowflake/sql/00_setup.sql` (your user, both public keys), and decide on `CORTEX_ENABLED_CROSS_REGION` (Claude models need cross-region inference in most regions).
3. **Deploy.** With the Snowflake CLI (`snow connection add` first):
   ```bash
   ./snowflake/scripts/deploy.sh <connection> --setup
   ```
   Or run the files `00`–`09` in order in a Snowsight worksheet. `08_agents.sql` is best run one statement at a time; check the agent spec against the current docs if a statement fails.
4. **Model.** Set the model for auto-fill in `AI.APP_CONFIG` (`LLM_MODEL`, default `claude-haiku-5-5`) to one available in your region.
5. **Switch modes** in `.env`: `AUTHBRIDGE_BACKEND=snowflake`, then `AUTHBRIDGE_AI=cortex`. Restart.

Smoke tests (expected results are in the comments of `03_crd_procedures.sql` and `04_pas_procedures.sql`):

```sql
CALL AUTHBRIDGE.PAYER.SP_CRD_EVALUATE('M100002','pt-002','72148','CPT','1477589632','order-sign');  -- gold card
CALL AUTHBRIDGE.PAYER.SP_COMPLETENESS('q-mri-lumbar','{"conservative_weeks":{"value":3,"verified":true}}');
```

Before a live demo, resume `AUTHBRIDGE_APP_WH` so the first hook call has no warehouse start delay.

## Repository layout

| Path | What it is |
|---|---|
| `services/common` | Shared Python: criteria engine, FHIR helpers, Snowflake client (SQL + Agents REST with key-pair JWT or PAT), validation, mock AI |
| `services/payer` | Payer service: `GET /cds-services`, `POST /cds-services/order-select-crd`, `/order-sign-crd`, `POST /fhir/Questionnaire/$questionnaire-package`, `POST /fhir/Claim/$submit`, `POST /fhir/Subscription`, plus `/internal/*` for the workbench |
| `services/provider` | EHR simulator backend: builds CDS Hooks requests, DTR QuestionnaireResponse, PAS Bundles; receives PAS notifications |
| `services/tests` | End-to-end tests (provider ↔ payer over HTTP, mock mode) |
| `ui` | Next.js 14 + TypeScript + Tailwind: clinic screens, payer work queue, case review with the criteria tree, analytics with agent chat |
| `shared/seed` | Synthetic patients and notes, payer plans/members/rules/criteria, four questionnaires, four self-authored demo policies |
| `snowflake/sql` | DDL, seed, procedures, Cortex Search, streams and tasks, semantic view, agents, governance |
| `snowflake/templates`, `scripts/build_sql.py` | Generates `02_seed.sql`, `04_pas_procedures.sql` and `05_ai.sql`; embeds the same criteria engine the mock uses |

## Design rules the code enforces

- **No LLM on the CRD path.** `SP_CRD_EVALUATE` is plain SQL: eligibility, rule lookup, gold card.
- **The model extracts; the engine decides.** Thresholds live in `PAYER.POLICY_CRITERIA` and are evaluated by `criteria.py` (three-valued logic).
- **Citations are checked mechanically.** A quote must be an exact substring of the cited document, or the answer is dropped (DTR) or treated as unverified (PAS → pend, never approve).
- **AI never denies.** Outcomes are auto-approve, pend, or recommend-deny to a clinician queue. Only `MEDICAL_DIRECTOR` can record A3 (`SP_RECORD_DECISION`), with a named signer and reason.
- **Clinician edits drop AI evidence.** If a clinician changes an AI-filled value, its quote no longer supports the answer, so the plan asks for documentation.
- **Everything is audited** in `AI.AI_RECOMMENDATION_AUDIT` with an AI-assisted flag.

## What is and isn't tested

- **Tested here:** both services and the full UI flow in mock mode (pytest, plus a headless-browser walk-through of every scenario), the production UI build, embedded Python procedure bodies (parsed and linted).
- **Not yet run against a live Snowflake account:** the SQL files, the Python stored procedures, Cortex Search, the semantic view and the agent specs. Expect small syntax fixes on first deploy, most likely in `07_analytics.sql` (semantic view clauses) and `08_agents.sql` (agent spec fields).
- **Docker images** were not built in this environment (Docker Hub was unreachable); the commands they run were tested directly.

## Things to verify before claiming conformance

Items marked `VERIFY` in `services/common/authbridge_common/fhir.py`: the CRD `reason` code system, DTR `information-origin` extension URL, PAS `administrationReferenceNumber` URL, PAS supporting-info category codes and the PAS Subscription topic URL. Also verify CPT/HCPCS/ICD-10 codes, replace the demo GLP-1 code with RxNorm/NDC, and confirm the CMS-0057-F metric definitions. Running the Inferno CRD/DTR/PAS test kits against the payer service is the strongest check.
