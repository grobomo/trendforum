# IMSVA 9.x Architecture Reference

## Port Map

| Port | Listener | Role |
|---|---|---|
| 25 | Postfix smtpd (or FoxProxy) | Inbound MTA receive |
| 2500 | Postfix smtpd | Internal from FoxProxy |
| 10020 | smtpd_proxy_filter | Before-queue content filter |
| 10024 | imssd (SMTP_REPROCESS) | Reprocessing channel (IBE/EUQ) |
| **10025** | **imssd (SMTP_SERVICE)** | **After-queue content filter — hot path** |
| 10026 | Postfix smtpd | Re-injection (scanned→delivery) |
| 10027 | Postfix smtpd | Hand-off (recipient rewrite) |
| 5060 | imssps | Policy Server SOAP |
| 5432 | PostgreSQL | Config DB |

## Key Daemons

- **imssd** — Scanning Daemon. Multi-process: 1 master + N workers. Each worker handles one message at a time on :10025. Settings: `proc_min_init_num`, `proc_max_worker_proc`, `proc_max_connections`.
- **imssps** — Policy Server. Serves scan rules to imssd workers via SOAP on :5060. **Processes recipients SERIALLY on a single thread per SOAP request** (verified in source: `ImssPolicyCache::GetRuleSet()` runs two sequential for-loops over the recipient vector for LDAP group resolution and policy matching).
- **imssmgr** — Manager. Watches `tb_version_number`, regenerates local config from DB, restarts components. Watchdog for processes/disk/queue.
- **foxproxyd** (TmFoxProxy) — Front-end proxy on :25. ACL/IP Profiler/ERS checks.
- **foxdns** — Local BIND for reputation/ERS queries.
- **Postfix** — Vendored 2.7.1, **Trend-patched** to write `Deferred Queue Event:Message=<qid>,Action=in|out` markers to maillog.

## Normal Mail Flow

```
SMTP client :25 → FoxProxy → Postfix smtpd :2500 (incoming queue)
    → Postfix smtp (imss transport) → imssd :10025
        → scan workers → Postfix smtpd :10026 (re-injection)
            → outgoing queue → destination :25
```

## Three Deferral Failure Modes at :10025

| Mode | Postfix sees | Root cause |
|---|---|---|
| **A** | `connect to localhost:10025: Connection timed out/refused` | imssd not listening (crashed/restarting/accept stall) |
| **B** | `conversation with localhost:10025 timed out (end of data)` | imssd worker hung > `imss_timeout` |
| **C** | `said: 451 ...` (Scan result uncertain / StartRuleSetRetrieval) | imssd reached, scan pipeline failed (imssps timeout, engine error) |

## Key imssd 4xx Responses

| Response | Meaning |
|---|---|
| `451 Transaction failed. ERROR: Scan result uncertain.` | Scanner couldn't determine verdict — engine/policy/external-lookup failure |
| `451 ... StartRuleSetRetrieval` | Can't reach imssps for policy rules |
| `451 Queue full` | Internal job queue saturated |
| `421 Service unavailable` | Shutting down / overloaded |

## Serial Recipient Processing (Source-Verified)

When imssd scans a multi-recipient message, it makes ONE SOAP call to imssps carrying sender + full recipient vector. Inside imssps, `ImssPolicyCache::GetRuleSet()` processes recipients in two sequential for-loops:

1. `for (i=0; i<recipients.size(); i++) GetLdapGroups(recipients[i])` — LDAP group resolution
2. `for (i=0; i<recipients.size(); i++) GetPolicySet(recipients[i])` — rule matching

For 999 recipients with cold LDAP cache, this can take minutes on a single thread — easily exceeding `recv_timeout_secs` (default 60s). imssd gives up and returns 451. imssps finishes later and gets "Broken pipe".

## Key Config Files

- `Event5/main.cf` — Postfix main config (`content_filter`, `imss_timeout`, `imss_connect_timeout`)
- `Event5/master.cf` — Postfix transport defs (the `imss unix` line dials :10025)
- `Event1/imss.ini` — imssd master config (worker pool, scanner_id, uuid)
- `Event3/imssps.*` — Policy Server logs (thread pool, LDAP queries, SOAP faults)
- `Event3/log.imss.*` — Scanning Daemon logs (scan errors, timeouts, verdicts)
- `Event3/sysevt.imss.*` — System events (service start/stop: events 20001/20002)
- `Event4/timestamp_core.txt` — Core dump timestamps
- `SystemInfo.Report.txt` — Host snapshot (load, memory, disk, IPs)

## Known Risk Patterns

| Setting | Risk threshold | Impact |
|---|---|---|
| `imss_connect_timeout ≤ 2s` | HIGH | Chronic background deferrals (~20/hr) when workers momentarily slow to accept |
| `imssps threads < 50` | MEDIUM | Concurrent message capacity limited (but doesn't help per-message bulk recipient speed due to serial loop) |
| `recv_timeout_secs < 120` | MEDIUM | Cold-cache large DL lookups exceed timeout → 451 for entire message |
| `proc_min_init_num < 20` | LOW | More worker respawns → more accept stalls |
