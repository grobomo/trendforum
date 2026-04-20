# CDT File Guide — Signal Ranking

All paths relative to `CDT-<timestamp>/IMSVA/LogFile/`. Signal: ★★★ must read, ★★ usually read, ★ situational.

## Triage Priority Order (Deferred Email Root-Causing)

1. `Event5/maillog*` — classify deferrals by mode A/B/C, identify top queue IDs/timestamps
2. `Event3/log.imss.*` — imssd-side errors at deferral timestamps
3. `Event3/msgerror.imss.*` + `msgretry.imss.*` — imssd's error/retry view
4. `Event3/MsgTracing.log*` or `msgtra.imss.*` — per-UUID deep-dive
5. `Event4/timestamp_core.txt` — crashes during incident window
6. `SystemInfo.Report.txt` — disk/inode/memory pressure
7. `Event5/main.cf` + `master.cf` + `Event1/imss.ini` — config sanity
8. `Event3/tlsagent.*` — outbound TLS delivery failures
9. `Event3/bifconnect-backend.log` + `prefilter-backend.log` — external service health
10. `Event3/cache_server.ldapcache.local*` — LDAP cache status

## Event1/ — Configuration Snapshot

| File | Signal | Contents |
|---|---|---|
| `imss.ini` | ★★★ | Master config: scanner_id, uuid, proc_*, smtp settings |
| `foxproxy.ini` | ★★ | FoxProxy front-end config |
| `fox_tls_forced_domain.list` | ★★★ | TLS-forced domains (mismatch = deferral source) |
| `ps_info.txt` | ★★★ | Process snapshot (count imssd workers) |
| `Policy.xml` | ★★ | Active rule set |
| `resolv.conf` | ★★ | DNS resolvers |
| `iptables`, `ip6tables` | ★★ | Host firewall (blocks on :10025?) |

## Event3/ — Application Logs (Primary Analysis Target)

| Pattern | Signal | Contents |
|---|---|---|
| `log.imss.*` | ★★★ | Scanning Daemon: errors, timeouts, verdicts, crashes |
| `MsgTracing.log*` | ★★★ | Per-message trace (receipt→scan→verdict→delivery) |
| `msgtra.imss.*` | ★★★ | Message tracking (imssd view) |
| `msgerror.imss.*` | ★★★ | Failed scan messages with reasons |
| `msgretry.imss.*` | ★★★ | IMSVA-internal retry queue |
| `tlsagent.*` | ★★★ | TLS handshake outcomes |
| `sysevt.imss.*` | ★★ | System events (20001=start, 20002=stop) |
| `imssmgr.*` | ★★ | Manager: restarts, config reloads |
| `imssps.*` | ★★ | Policy Server: thread pool, LDAP queries, SOAP faults |
| `smtpconnagent.*` | ★★ | Outbound SMTP stats/errors |
| `foxmsg.*` | ★★ | FoxProxy message trace |
| `bifconnect-backend.log` | ★★ | Smart Protection / Apex Central connectivity |
| `cache_server.ldapcache.local*` | ★★ | LDAP cache status |

## Event4/ — Core Dumps

| File | Signal | Contents |
|---|---|---|
| `timestamp_core.txt` | ★★★ if non-empty | Core dump timestamps + binary names |

## Event5/ — MTA (Postfix) Logs

| File | Signal | Contents |
|---|---|---|
| `maillog*` | ★★★ | Postfix logs: status=deferred, Deferred Queue Event markers |
| `messages*` | ★★ | /var/log/messages: OOM kills, kernel events |
| `main.cf` | ★★★ | content_filter, imss_timeout, imss_connect_timeout |
| `master.cf` | ★★★ | imss transport, :10026/:10027 listeners |

## Top-Level

| File | Signal | Contents |
|---|---|---|
| `SystemInfo.Report.txt` | ★★★ | uname, uptime, free, df, netstat, process list |
| `ReadmeFirst.txt` | ★ | Case metadata, capture time |

## Deferral Classification Commands

```bash
# Mode A (connect failures)
grep -E "connect to (localhost|127\.0\.0\.1)\[127\.0\.0\.1\]:10025:" maillog*

# Mode B (data-phase timeout)
grep -E "conversation with (localhost|127\.0\.0\.1)\[127\.0\.0\.1\]:10025 timed out" maillog*

# Mode C (imssd 4xx)
grep -E "said:\s+4[0-9]{2}\s" maillog* | grep ":10025"

# All deferrals with reason
grep -hE "status=deferred" maillog* | sed -E 's/.*status=deferred //' | sort | uniq -c | sort -rn

# Service start/stop
grep -E "(20001|20002)" sysevt.imss.*

# Deferred Queue Event markers (Trend-patched Postfix)
grep "Deferred Queue Event" maillog*
```
