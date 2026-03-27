# Compliance Platform — Complete Feature Guide

---

### What This Platform Does (Non-Technical Summary)

This platform helps organizations **identify, assess, and manage cybersecurity risks** across their technology systems. Think of it as a "security health checkbook" — you describe your technology environment, the system finds potential threats, scores how dangerous each one is using real-world intelligence data, and recommends what to do about them. Risks that can't be fixed immediately are tracked in a living register until they're resolved.

---

### End-to-End User Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        COMPLIANCE RISK ASSESSMENT PLATFORM                       │
│                              End-to-End User Flow                                │
└─────────────────────────────────────────────────────────────────────────────────┘

 ┌──────────┐
 │  LOGIN   │  User authenticates via AWS Cognito (SSO / username+password)
 └────┬─────┘
      │
      ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                              DASHBOARD                                       │
 │                                                                              │
 │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
 │  │ Assessments  │  │ Active Risks │  │  Audit Logs  │  │  ML Model    │     │
 │  │    Count     │  │    Count     │  │    Count     │  │   Status     │     │
 │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
 │                                                                              │
 │  Quick access to all assessments, risks, and intelligence features           │
 └──────┬───────────────────┬───────────────────┬───────────────────┬───────────┘
        │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼
 ┌─────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
 │ ASSESSMENTS │   │ RISK         │   │ AUDIT LOGS   │   │ INTELLIGENCE     │
 │ LIST        │   │ REGISTER     │   │              │   │ HUB              │
 └──────┬──────┘   └──────────────┘   └──────────────┘   └──────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                       CREATE / EDIT ASSESSMENT                               │
 │                                                                              │
 │  Name: "Cloud Migration Risk Assessment"                                     │
 │  Scope: "AWS infrastructure migration for patient records system"            │
 │  Industry Sector: [Healthcare ▼]    ◄── NEW: enables sector-specific intel   │
 │  Tech Stack: [AWS EC2, S3, RDS, Lambda, VPN]                                │
 │  Compliance: [HIPAA, SOC2]                                                   │
 └──────┬───────────────────────────────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                         ASSESSMENT DETAIL PAGE                               │
 │                                                                              │
 │  ┌─── THREATS ──────────────────────────────────────────────────────────┐    │
 │  │                                                                      │    │
 │  │  ┌──────────────────────────────────────────────────────────────┐    │    │
 │  │  │ Threat: "Phishing Attack on Admin Credentials"               │    │    │
 │  │  │ Category: Social Engineering  │  Severity: High              │    │    │
 │  │  │                                                              │    │    │
 │  │  │ ┌─ Enrichment Badge ─┐  ┌─ ML Score Badge ──────────────┐  │    │    │
 │  │  │ │ 🔍 Intel: 3 feeds  │  │ ⚡ Score: 78/100 (High)       │  │    │    │
 │  │  │ └────────────────────┘  │ 📊 Why: KEV+25, CVSS+20...    │  │    │    │
 │  │  │                         └────────────────────────────────┘  │    │    │
 │  │  │                                                              │    │    │
 │  │  │ ┌─ ATT&CK Context (expandable) ────────────────────────┐   │    │    │
 │  │  │ │ Mapped Techniques: T1566 Phishing, T1078 Valid Accts  │   │    │    │
 │  │  │ │ [Manage Mappings]  [Build Threat Progression]          │   │    │    │
 │  │  │ │                                                        │   │    │    │
 │  │  │ │ ┌─ Kill Chain Flow (React Flow graph) ──────────────┐ │   │    │    │
 │  │  │ │ │ Initial    →  Execution  →  Credential  →  Impact │ │   │    │    │
 │  │  │ │ │ Access        T1059         Access         T1486   │ │   │    │    │
 │  │  │ │ │ T1566                       T1003                  │ │   │    │    │
 │  │  │ │ │                              [⛶ Fullscreen]        │ │   │    │    │
 │  │  │ │ └───────────────────────────────────────────────────┘ │   │    │    │
 │  │  │ └───────────────────────────────────────────────────────┘   │    │    │
 │  │  └──────────────────────────────────────────────────────────────┘    │    │
 │  │                                                                      │    │
 │  │  ┌──────────────────────────────────────────────────────────────┐    │    │
 │  │  │ Threat: "Insider Data Exfiltration" (No CVE)                 │    │    │
 │  │  │ Category: Insider Threats  │  Severity: High                 │    │    │
 │  │  │ Intel: 🎯 12 ATT&CK groups │ 📊 Sector: 180/1K orgs/yr     │    │    │
 │  │  │ ML Score: 72/100 (High) — sector_rate+15, groups+10...      │    │    │
 │  │  └──────────────────────────────────────────────────────────────┘    │    │
 │  └──────────────────────────────────────────────────────────────────────┘    │
 │                                                                              │
 │  ┌─── ADVANCED ANALYTICS (4 tabs) ─────────────────────────────────────┐    │
 │  │                                                                      │    │
 │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │    │
 │  │  │   Intel    │ │ ML Scoring │ │   Threat   │ │ Clustering │       │    │
 │  │  │ Enrichment │ │            │ │   Graph    │ │            │       │    │
 │  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘       │    │
 │  │        │              │              │              │               │    │
 │  │        ▼              ▼              ▼              ▼               │    │
 │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │    │
 │  │  │Enrich all│  │Train     │  │Interactive│  │Risk clusters │       │    │
 │  │  │threats   │  │model,    │  │node graph │  │with keyword  │       │    │
 │  │  │from 4+   │  │score all,│  │PageRank   │  │labels,       │       │    │
 │  │  │feeds     │  │explain   │  │critical   │  │similar threat│       │    │
 │  │  │(dual     │  │scores,   │  │nodes,     │  │finder        │       │    │
 │  │  │track)    │  │survival  │  │cascade    │  │              │       │    │
 │  │  │          │  │analysis  │  │paths      │  │              │       │    │
 │  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘       │    │
 │  └──────────────────────────────────────────────────────────────────────┘    │
 │                                                                              │
 │  ┌─── EVIDENCE ─────────────────────────────────────────────────────────┐    │
 │  │  Upload network diagrams, scan results, policies → S3 (encrypted)    │    │
 │  │  AI analyzes evidence → auto-generates threats                        │    │
 │  └──────────────────────────────────────────────────────────────────────┘    │
 │                                                                              │
 │  ┌─── RECOMMENDATIONS ─────────────────────────────────────────────────┐    │
 │  │  AI-generated + manual remediation actions per threat                 │    │
 │  │  Priority: Critical / High / Medium / Low                             │    │
 │  └──────────────────────────────────────────────────────────────────────┘    │
 └──────────────────────────────────────────────────────────────────────────────┘
        │
        │ Threats that can't be fixed immediately
        ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                          ACTIVE RISK REGISTER                                │
 │                                                                              │
 │  ┌──────────────────────────────────────────────────────────────────────┐    │
 │  │ Risk: "Unpatched Legacy Database"                                    │    │
 │  │ Status: [Monitoring]  │  Risk Score: 82/100 (ML-computed)           │    │
 │  │ 🔒 Score Locked: No   │  Est. Persistence: ~90 days                 │    │
 │  │ Review Due: Mar 15    │  Residual Risk: High                        │    │
 │  │ Cluster: "Database Infrastructure Risks"                             │    │
 │  │ PageRank: 0.15 (high cascade risk)                                   │    │
 │  │                                                                      │    │
 │  │ [Accept Risk] [Mitigate] [Transfer] [Lock Score 🔒]                 │    │
 │  └──────────────────────────────────────────────────────────────────────┘    │
 │                                                                              │
 │  View: [Flat List ▼] / [By Status] / [By Risk Cluster]                     │
 └──────────────────────────────────────────────────────────────────────────────┘
        │
        │ Every action is recorded
        ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                             AUDIT LOG                                        │
 │                                                                              │
 │  2026-02-23 14:32  assessment_created    "Cloud Migration" by analyst@co    │
 │  2026-02-23 14:33  ml_score              threat abc → 78 (model: gbm-v2)   │
 │  2026-02-23 14:35  active_risk_created   auto-created (CISA KEV flagged)   │
 │  2026-02-23 14:40  active_risk_updated   score_locked=true by owner@co     │
 └──────────────────────────────────────────────────────────────────────────────┘
```

---

### Component-by-Component Explanation

#### 1. Dashboard
**What it does:** The landing page after login. Shows summary counts of assessments, active risks, audit log entries, and ML model health at a glance.

**For non-technical users:** Think of it as your "security health summary" — one screen that tells you how many risk assessments are underway, how many open risks need attention, and whether the AI scoring system is operational.

**For technical users:** Fetches from `GET /assessments`, `GET /active-risks`, `GET /audit-logs`, and `GET /ml/model-info`. Dashboard stat cards link to detail pages. ML model card shows feature count, training sample count, and last-trained timestamp.

---

#### 2. Assessment Management
**What it does:** Create, edit, and manage risk assessments. Each assessment represents a specific project, system, or environment being evaluated for security risks.

**For non-technical users:** You're filling out a form that says "I want to evaluate the security of [this system]." You describe what technology is involved (servers, databases, cloud services), what compliance rules apply (HIPAA, SOC2), and what industry you're in. The system uses all of this to find relevant threats.

**For technical users:** CRUD operations on `Assessment` model. `tech_stack` (string array) drives threat catalogue matching. `industry_sector` (new) feeds into Track B enrichment for sector-specific incident frequency lookups. `compliance_frameworks` influences recommendation generation. Supports `draft → in_progress → completed → archived` lifecycle.

---

#### 3. Threat Identification & Catalogue
**What it does:** Each assessment contains threats — potential security problems. Threats can be added manually, matched from a built-in catalogue of 50+ common threats, or auto-generated by AI analysis of uploaded evidence.

**For non-technical users:** The system maintains a "library" of known security problems (like phishing attacks, data breaches, insider threats). When you describe your technology, it suggests which problems are most relevant. You can also add your own, or upload documents and let the AI find threats automatically.

**For technical users:** `ThreatCatalogue` contains pre-defined entries keyed by category (e.g., `social_engineering_phishing`, `insider_threats`, `cloud_misconfiguration`). The `intelligence_service` uses Bedrock (Claude/Nova) to analyze evidence files and generate threats with severity, likelihood, and impact. Each threat has `cve_ids` (optional), `category`, `severity`, `likelihood`, `impact`.

---

#### 4. MITRE ATT&CK Integration
**What it does:** Maps each threat to real-world attack techniques from the MITRE ATT&CK framework — the industry-standard encyclopedia of how attackers actually operate.

**For non-technical users:** Imagine a criminal playbook that catalogues every known method attackers use. This system connects each of your threats to specific entries in that playbook. This tells you: "If this threat materializes, here's exactly how an attacker would do it — step by step." This makes your risk assessment grounded in reality, not guesswork.

**For technical users:** 691 techniques across 14 tactics synced from MITRE's STIX/TAXII feed into local PostgreSQL cache. `ThreatAttackMapping` links threats to techniques with confidence scores. Three mapping modes: AI-suggested (Bedrock maps threat description → techniques), manual search, and visual Browse Matrix (14-column tactic grid with click-to-map). Sub-techniques nested under parents with expand/collapse.

---

#### 5. Kill Chain / Threat Progression
**What it does:** For each threat, generates a realistic multi-stage attack scenario showing how an attacker would progress from initial access to final impact.

**For non-technical users:** Instead of just saying "phishing is a risk," the system shows: "Step 1: Attacker sends phishing email → Step 2: Employee clicks link → Step 3: Attacker gets credentials → Step 4: Attacker accesses database → Step 5: Data is stolen." Each step is linked to a real technique from the ATT&CK playbook. You can expand this to a full-screen interactive diagram.

**For technical users:** Deterministic kill chain engine (not LLM-selected). Stages built from DB-validated techniques ordered by `AttackTactic.phase_order` (1–14). LLM only writes contextual narrative per stage. Rendered using React Flow (`@xyflow/react`) with dagre layout. Each stage node shows technique name, MITRE ID, tactic color, detection hints (from `x_mitre_detection`), and actor behavior. Supports fullscreen via `createPortal`.

---

#### 6. Intel Enrichment (Phase 1 — Dual Track)
**What it does:** Enriches every threat with real-world intelligence data from multiple external sources. Works for both vulnerability-type threats (with CVE IDs) and non-vulnerability threats (insider threats, phishing, misconfigurations).

**For non-technical users:** The system goes out and checks: "Is this vulnerability actually being exploited by attackers right now? How many security researchers are tracking it? Are there public tools available to exploit it? How often does this type of attack happen in your industry?" This transforms abstract risk entries into evidence-backed assessments.

**For technical users:**

| Track | Threats | Sources | Key signals |
|-------|---------|---------|-------------|
| **Track A** (CVE-based) | ~15% of catalogue | NVD v2 API (CVSS, CWE, EPSS), CISA KEV (actively exploited bool), OTX by CVE (pulse count, IOCs), GitHub Search (PoC repos) | `cvss_v3_score`, `cisa_kev`, `exploit_repo_count`, `otx_pulse_count` |
| **Track B** (Non-CVE) | ~85% of catalogue | ATT&CK Groups (intrusion sets using mapped techniques), OTX by technique ID, sector frequency table (DBIR/X-Force stats), ATT&CK metadata (detection/mitigation coverage) | `attack_group_count`, `sector_incident_rate`, `detection_coverage`, `mitigation_coverage` |

Auto-creates `ActiveRisk` entries for threats flagged by CISA KEV or with ≥10 known threat groups.

---

#### 7. ML Likelihood Scoring (Phase 2)
**What it does:** Replaces guesswork risk scores with a computed 0–100 score based on 10 real-world features. Explains exactly why each threat received its score.

**For non-technical users:** Instead of a human guessing "this is probably High risk," the system calculates a precise score using measurable factors: "This vulnerability has a severity of 9.1/10, is actively exploited by nation-states, has 5 public exploit tools available, and attacks in your industry happen 340 times per year per 1,000 organizations. Score: 82/100 (Critical)." You can click "Why this score?" to see a chart breaking down each factor's contribution.

**For technical users:** Two scoring modes:
- **Formula (bootstrap):** Weighted sum of 10 normalized features → 0–100 → Low/Med/High/Critical. Deterministic, auditable.
- **ML model (when data accumulates):** `GradientBoostingClassifier` or `RandomForestClassifier` trained on historical labeled risks. SHAP explainability via `shap.TreeExplainer`. Model artifacts stored in S3 with candidate → promote pipeline.

Survival analysis (`lifelines.KaplanMeierFitter`) estimates `estimated_persistence_days` — how long each risk is likely to remain open based on historical resolution patterns.

Weekly retraining via CloudWatch cron with F1 quality gate and bias monitoring (class imbalance detection).

---

#### 8. Threat Graph (Phase 3)
**What it does:** Visualizes your entire assessment as an interactive network diagram showing how technology components, threats, attack techniques, and tactics are interconnected. Identifies which components are most "pivotal" — meaning if they're compromised, the damage cascades widely.

**For non-technical users:** Imagine a map of your technology where each component (server, database, application) is connected to the threats that could affect it, and those threats are connected to the attack methods that enable them. The system highlights which components are the "linchpins" — the ones where a single breach would cause the most widespread damage. These are your highest priority to protect.

**For technical users:** NetworkX `DiGraph` with 4 node types (TechComponent, Threat, AttackTechnique, AttackTactic) and weighted directed edges. PageRank + betweenness centrality computed server-side. React Flow visualization with node size proportional to PageRank score. Supports neighbourhood queries, critical node ranking (top-5), and shortest path analysis between any two nodes.

---

#### 9. Vulnerability Clustering (Phase 4)
**What it does:** Automatically groups threats into natural risk categories using machine learning. Instead of seeing 30 individual threats, you see them organized into themes like "Credential-Based Attacks" or "Cloud Misconfiguration Risks."

**For non-technical users:** When you have many threats, it's hard to see patterns. The system automatically sorts them into groups based on similarity — like sorting a deck of cards by suit. Each group gets a descriptive label (e.g., "Supply Chain & Third-Party Risk") so you can address entire categories at once rather than one threat at a time. You can also ask "show me threats similar to this one" to find related risks across different assessments.

**For technical users:** DBSCAN clustering (`eps=0.5, min_samples=2, metric='cosine'`) over a combined feature matrix: TF-IDF (100 components) on `title + description` concatenated with scaled numeric features (`risk_score`, `technique_count`, `tactic_coverage`, `cisa_kev`, `attack_group_count`). Noise points get singleton clusters. Top-5 TF-IDF keywords extracted per cluster centroid for labeling. Silhouette scoring for cluster quality. Cross-assessment similar-threat finder using cosine similarity on feature vectors.

---

#### 10. Active Risk Register
**What it does:** A living tracker for risks that can't be immediately fixed. Each risk has a score, a review schedule, an estimated resolution timeline, and a status (monitoring, mitigating, accepted, closed).

**For non-technical users:** Some risks can't be patched or fixed right away — maybe the vendor hasn't released an update, or the fix would cost too much. These go into the "Risk Register" — a watched list. Each entry shows: how dangerous it is (ML-computed score), how long it's likely to stay open (survival analysis), when it's due for review, and whether a human has manually set the risk level (locked score). Overdue reviews are flagged automatically.

**For technical users:** `ActiveRisk` model with `risk_score` (ML-written), `likelihood`/`impact` (decomposed), `residual_risk`, `estimated_persistence_days` (survival analysis), `next_review_date` (auto-computed from `review_cycle_days`), `score_locked` (human override protection), `extra_data` JSONB (stores `pagerank`, `cluster_id`, `cluster_label`). Full audit trail for every state change. Auto-created for CISA KEV-flagged threats.

---

#### 11. Evidence Management
**What it does:** Upload supporting documents (network diagrams, scan results, security policies) to encrypted cloud storage. AI can analyze these documents to automatically identify threats.

**For non-technical users:** Attach your security scan reports, architecture diagrams, or compliance documents. The system stores them securely (encrypted) and can read them using AI to automatically find threats you might have missed.

**For technical users:** S3 presigned URL upload flow with SSE-KMS encryption. Textract OCR for document parsing. Bedrock (Claude) analyzes extracted text to generate threats with severity/likelihood/impact. Evidence linked to assessments via `Evidence` model.

---

#### 12. Intelligence Hub
**What it does:** A dedicated page for managing the platform's AI and intelligence capabilities — training models, viewing bias reports, running survival analysis, and monitoring system health.

**For non-technical users:** The "control center" for the platform's intelligence features. Administrators can see how accurate the scoring model is, whether it's treating all risk categories fairly (bias monitoring), and train it on new data as more assessments are completed.

**For technical users:** Dashboard with model metadata (algorithm, feature count, training samples, accuracy metrics), bias report table (per-sector class distribution with imbalance flags), survival curve visualization, and controls for training, scoring, and tenant-wide clustering. Links to per-assessment Advanced Analytics tabs.

---

#### 13. Audit Logging
**What it does:** Records every action taken on the platform — who did what, when, and what changed. Supports compliance requirements for traceability.

**For non-technical users:** A tamper-proof activity log. If an auditor asks "who changed this risk score and why?", the answer is in the audit log — including whether it was changed by a human or by the AI, what the score was before and after, and which model version produced the new score.

**For technical users:** `AuditLog` model with `tenant_id`, `user_id`, `action_type` (25+ types including `ml_score`, `active_risk_created`, `active_risk_updated`), `resource_type`, `resource_id`, `changes` (JSONB before/after diff), `ip_address`, `user_agent`. Queryable via API with date range, action type, and user filters.

---

### Data Flow Summary

```
Evidence Upload ──► AI Analysis ──► Threats Generated
                                         │
Manual Entry ──────────────────────► Threats Added
                                         │
Threat Catalogue Match ────────────► Threats Matched
                                         │
                                         ▼
                                 ┌── ATT&CK Mapping ──┐
                                 │   (14 tactics,      │
                                 │    691 techniques)   │
                                 └────────┬────────────┘
                                          │
                              ┌───────────┼───────────┐
                              ▼           ▼           ▼
                        Kill Chain    Intel         Graph
                        Generation   Enrichment    Building
                              │      (Dual Track)     │
                              │           │           │
                              │     ┌─────┴─────┐    │
                              │     │ Track A:   │    │
                              │     │ NVD, CISA, │    │
                              │     │ OTX, GitHub│    │
                              │     ├────────────┤    │
                              │     │ Track B:   │    │
                              │     │ ATT&CK     │    │
                              │     │ Groups,    │    │
                              │     │ Sector     │    │
                              │     │ Stats, OTX │    │
                              │     └─────┬──────┘    │
                              │           │           │
                              └───────────┼──────────┘
                                          │
                                          ▼
                                   ML Scoring Engine
                                   (Formula → ML Model)
                                          │
                              ┌───────────┼───────────┐
                              ▼           ▼           ▼
                        Likelihood   Survival     Clustering
                        Score 0-100  Analysis     (DBSCAN)
                              │      (days to        │
                              │       resolve)       │
                              └───────────┼──────────┘
                                          │
                                          ▼
                                  Active Risk Register
                                  (tracked until resolved)
                                          │
                                          ▼
                                     Audit Log
                                  (every action recorded)
```

---

### Security & Trust Safeguards

| Safeguard | What it means for users |
|-----------|------------------------|
| **Score Lock 🔒** | If you manually set a risk score, the AI will never override it without your permission |
| **"Why this score?"** | Every AI-generated score shows exactly what factors drove it — full transparency |
| **No client data leaves the system** | Only public identifiers (CVE IDs, MITRE technique IDs) are sent to external intelligence feeds — never your assessment names, threat descriptions, or any client information |
| **Model promotion gate** | New AI model versions must be explicitly approved by an admin before they go live |
| **Bias monitoring** | The system checks whether the AI model treats all risk categories and industry sectors fairly |
| **Complete audit trail** | Every action — human or AI — is permanently recorded with full before/after details |
