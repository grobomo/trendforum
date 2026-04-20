---
name: cdt-imsva-analyzer
description: Analyze IMSVA (InterScan Messaging Security Virtual Appliance) CDT (Customer Diagnostic Toolkit) bundles to diagnose deferred emails, scan failures, and service issues. Use when a support case involves IMSVA email deferrals, CDT log analysis, mail flow troubleshooting, or IMSVA configuration assessment. Triggers on CDT analysis, IMSVA deferred mail, IMSVA scan failures, IMSVA troubleshooting, port 10025 issues, imssd errors, imssps policy server failures.
---

# IMSVA CDT Analyzer

Analyze extracted IMSVA CDT bundles to identify root causes of deferred emails, scan failures, and service instability. Based on verified analysis of IMSVA 9.1 source code and real CDT cases.

## Quick Start

1. Extract CDT if needed:
```bash
bash scripts/extract_cdt.sh <archive.zip> [output_dir]
```

2. Run automated analysis:
```bash
python3 scripts/parse_cdt.py <cdt_root> --format markdown
```

3. Review the output, then deep-dive into flagged areas using the guidance below.

## Analysis Workflow

### Step 1 — Classify Deferrals

Run the parser or manually classify from `Event5/maillog*`:

- **Mode A** — `connect to localhost:10025: Connection timed out/refused` → imssd not listening
- **Mode B** — `conversation with localhost:10025 timed out` → scan hung past `imss_timeout`
- **Mode C** — `said: 451 ...` → scan pipeline failed (policy server, engine, external lookup)

Each mode has a different remedy. Do not treat "port 10025 deferrals" as one problem.

### Step 2 — Correlate to Scanner Logs

For top deferral timestamps, pull matching lines from `Event3/log.imss.*`:
- `[ERROR] Failed to receive policy response` → imssps SOAP timeout (check `imssps.*` for SOAP faults)
- `ERROR: Scan result uncertain` → imssd gave up on scan verdict
- `ERROR: RetrieveRuleSet return=1606` → policy retrieval failed
- `SIGSEGV` / core dump → check `Event4/timestamp_core.txt`

### Step 3 — Detect Incidents

The parser auto-detects:
- **Mass deferrals**: single queue ID with ≥100 deferrals (bulk DL fan-out → imssps serial recipient processing overwhelms cold LDAP cache)
- **Service restarts**: sysevt events 20001/20002, correlate ±2 min to deferral spikes
- **Chronic connect timeouts**: steady ~20/hr Mode A rate from tight `imss_connect_timeout`

### Step 4 — Check Config Risks

Flag these from `Event5/main.cf` and `Event1/imss.ini`:
- `imss_connect_timeout ≤ 2s` → chronic Mode A deferrals (recommend ≥5s)
- `recv_timeout_secs < 120` in imssps → cold-cache large DL timeouts
- Low `proc_min_init_num` → more worker respawns → more accept stalls

### Step 5 — Generate Recommendations

The parser produces ranked recommendations. Always include:
- Severity (IMMEDIATE / HIGH / MEDIUM)
- Risk level of the fix (LOW / MEDIUM / HIGH)
- Exact setting name, current value, and recommended value
- Evidence from the CDT (file:line references)

## Key Architecture Insight

**imssps processes recipients SERIALLY** (source-verified in `ImssPolicyCache::GetRuleSet()`). For a 999-recipient DL with cold LDAP cache, one imssps thread runs ~999 sequential LDAP lookups. This easily exceeds `recv_timeout_secs` (default 60s) → imssd returns `451 Scan result uncertain` for ALL recipients. Retry succeeds because cache warmed.

This means:
- Raising thread pool size helps concurrent messages but NOT per-message bulk recipient speed
- The real fix is raising `recv_timeout_secs` and/or warming LDAP cache proactively
- Long-term fix requires code change: parallelize the recipient loop

## Reference Material

- **Architecture details**: Read `references/imsva-architecture.md` for port map, daemon roles, mail flow, config settings
- **CDT file guide**: Read `references/cdt-file-guide.md` for signal ranking and grep commands per Event directory

## Output Rules

- Always include evidence: log excerpts with file:line references
- Always include delay breakdown from Postfix (`delays=a/b/c/d` = before-queue/active-queue/connect/data-phase)
- For customer-facing reports: executive summary first, technical details below
- **Never send L3 docs (internal PDFs) to customers** — excerpt small sections only
- Always provide clear next steps with documentation references (Online Help, Admin Guides, KB articles)
