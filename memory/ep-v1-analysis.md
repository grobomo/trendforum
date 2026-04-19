# EP V1 Cloud Posture Analysis — 2026-04-19 05:25 CDT

## API Query
- Endpoint: `GET /v3.0/cam/awsAccounts` (EP tenant)
- Token: `EP_API_KEY` from Windows Credential Manager → stored in Linux keyring

## Key Findings

**Total: 46 AWS accounts. ZERO connected. ALL need attention.**

| State | Count | Meaning |
|-------|-------|---------|
| outdated | 41 | CloudFormation stack version behind — needs update |
| failed | 5 | Stack completely broken — likely decommissioned |
| connected | 0 | — |

### Failed accounts (5) — likely decommissioned
All last updated Nov 4, 2025. All EP UK staging/testing:
- 894699194647 | EP UK Casting CA Staging
- 754635743528 | EP UK Casting UK Staging
- 955144779734 | EP UK Casting US Staging
- 473139015774 | EP UK Security Testing
- 485964675259 | EP UK UAT

### Outdated accounts by creation wave

**Wave 1: Oct 2-3, 2024 (14 accounts) — Original EP UK deployment**
- EP UK Casting UK/US/CA Live (Prod) — 675328086166, 210977011156, 129742340240
- EP UK Buildkite (CI/CD) — 404098547650 (9,555 resources)
- EP UK Observability, Backups, Audit, Users, Demos, Shared Services, Archive, Log Archive, Sandbox, Unused
- Created Oct 2-3, 2024 — the "Oct 3" freeze date in original RCA

**Wave 2: Jul 2024 (2 accounts) — Early US accounts**
- eparchproto, epmlproto

**Wave 3: Jun 2025 (15 accounts) — Major US org deployment**
- epcprod (613378223610) — PRODUCTION, highest priority
- entertainmentpartners, epmlprod, eppopprod, epcnonprod, etc.

**Wave 4: Jul-Aug 2025 (10 accounts) — Latest additions**
- eplogarchive, ep-opstooling, epaudit, epbreeze, epprod, etc.

### Critical correction to original RCA
- Original said "19 accounts froze Oct 3, 2024" — WRONG
- Reality: 14 EP UK accounts were *created* Oct 2-3, 2024, and are now outdated
- But 27 MORE accounts added in 2025 are ALSO outdated
- ALL 46 accounts are disconnected, not just 19
- epcprod was created Jun 2025, not Oct 2024 — so Oct 2024 freeze doesn't apply to it

### Root cause (revised)
The "outdated" state means the V1 CloudFormation stack template has been updated by Trend Micro, but EP hasn't redeployed the newer version. This is NOT a sudden disconnection — it's a gradual drift as V1 updates its stack requirements and EP doesn't keep up.

The 5 "failed" accounts truly lost their IAM role connection (stack deleted or role removed).

### Priority
1. **epcprod** (613378223610) — PRODUCTION, outdated since creation
2. **epprod** (653733036938) — also PRODUCTION
3. All 41 outdated accounts need stack updates
4. 5 failed accounts — confirm with Dan if truly decommissioned, then remove
