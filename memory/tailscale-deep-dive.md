# Tailscale Deep Dive — Three-Layer Research
_Compiled 2026-04-18 by Coconut_

## 1. DNS Services

### MagicDNS
MagicDNS automatically assigns DNS names to every device in your tailnet so you can use `hostname` instead of IP addresses. Names follow the pattern `<machine-name>.<tailnet-name>.ts.net` (e.g., `nabu-2wd56m3-1.orca-decibel.ts.net`). It's enabled by default in the admin console under DNS settings.

**Machine Names:** Each device gets a name derived from its OS hostname at first registration. You can rename in the admin console. Names must be unique within the tailnet; if duplicates exist, Tailscale appends a suffix (`-1`, `-2`). Names are lowercase, alphanumeric + hyphens, max 63 chars.

**Tailnet Name:** Your tailnet gets a unique `<adjective>-<noun>.ts.net` domain (ours: `orca-decibel.ts.net`). This is permanent and cannot be changed. Enterprise plans can set a custom "fun name" alias, but the underlying ts.net domain remains.

**How DNS resolution works:**
- Tailscale intercepts DNS queries on each device via a local DNS proxy (100.100.100.100)
- Queries for `*.ts.net` are resolved by Tailscale's control plane
- All other queries are forwarded to your configured nameservers (global or split DNS)
- Split DNS lets you route specific domains to specific nameservers (e.g., `corp.example.com` → internal DNS)

### NextDNS Integration
NextDNS is a cloud DNS filtering service (ad blocking, malware protection, analytics). Tailscale has a native integration:
- Configure in admin console → DNS → Add nameserver → NextDNS
- Requires a NextDNS Configuration ID (from your NextDNS account)
- Tailscale shares device info with NextDNS so you get per-device analytics
- Acts as a global nameserver — all DNS queries from all tailnet devices route through NextDNS
- Uses DNS-over-HTTPS (DoH) for privacy
- If you use NextDNS, avoid adding other global nameservers (could bypass filtering)
- Works with Tailscale v1.16+, requires MagicDNS enabled

### Control D Integration
Similar to NextDNS — a customizable DNS service for blocking threats, ads, trackers:
- Configure as a global nameserver in admin console
- Requires a Control D resolver ID
- Supports per-device profiles via `nodeAttrs` in the policy file (e.g., different filtering for servers vs workstations)
- Priority system for overlapping profiles (`?priority=1`, `?priority=2`)
- Uses DoH; requires Tailscale v1.70+
- Cannot be used as a split DNS server (global only)

### DNS Architecture Summary
```
Device → Tailscale local proxy (100.100.100.100)
  ├── *.ts.net queries → Tailscale control plane (MagicDNS)
  ├── Split DNS domains → configured restricted nameservers
  └── Everything else → global nameservers (NextDNS/Control D/custom)
```

---

## 2. Exposing Services: Serve vs Funnel

### Tailscale Serve (Tailnet-only)
Serve routes traffic from *other devices on your tailnet* to a local service. Think of it as sharing a service privately within your network.

**What it can serve:**
- Reverse proxy to local HTTP services (e.g., `tailscale serve localhost:3000`)
- Static files or directories
- Plain text (for debugging)
- TCP forwarding (raw or TLS-terminated)

**Key features:**
- Auto-provisions TLS certificates (requires HTTPS enabled in tailnet)
- Injects identity headers into proxied requests:
  - `Tailscale-User-Login` (e.g., alice@example.com)
  - `Tailscale-User-Name` (display name)
  - `Tailscale-User-Profile-Pic`
- Access control rules apply — only authorized tailnet members can reach it
- Can forward app capability headers via `--accept-app-caps` (v1.92+)
- Supports PROXY protocol for preserving client IP

**Limitations:**
- Only available within tailnet (not public internet)
- Same port can't be used for both Serve and Funnel simultaneously
- macOS file serving limited to open-source variant
- DNS names restricted to `*.ts.net`

### Tailscale Funnel (Public Internet)
Funnel exposes a local service *to the entire internet* via your Tailscale hostname.

**How it works:**
- Traffic flows: Internet → Tailscale Funnel infrastructure → your device
- Automatically provisions a TLS certificate for your `*.ts.net` hostname
- Must be explicitly enabled in admin console (Access Controls → funnel section)
- Allowed ports: 443, 8443, 10000 only

**What it can serve (same as Serve):**
- Reverse proxy (`tailscale funnel localhost:3000`)
- Static files/directories
- Plain text
- TCP forwarding (raw or TLS-terminated)

**CLI flags:**
- `--bg` — run persistently in background (survives reboots)
- `--https=<port>` — specify HTTPS port (default 443)
- `--tcp=<port>` — raw TCP forwarding
- `--tls-terminated-tcp=<port>` — TLS-terminated TCP forwarding
- `--set-path=<path>` — mount at a specific URL path
- `--proxy-protocol=<1|2>` — preserve client IP via PROXY protocol

**Background mode (`--bg`):**
- Persists through reboots and `tailscale down/up` cycles
- Must explicitly turn off: `tailscale funnel --https=443 off`
- Without `--bg`, must manually restart after reboot

**Security notes:**
- No identity headers on Funnel traffic (it's public, anonymous)
- Anyone on the internet can reach it
- WireGuard encryption still protects the tunnel from Funnel infra to your device

### Serve vs Funnel Decision Matrix
| Need | Use |
|------|-----|
| Share with tailnet only | Serve |
| Expose to internet | Funnel |
| Need user identity headers | Serve |
| Webhook endpoints | Funnel |
| Dev/staging previews | Either |
| Production services | Funnel (or Serve + subnet router) |

---

## 3. Networking Architecture

### Connection Types (Three Tiers)

**1. Direct connections (best):**
- Peer-to-peer UDP between devices
- Lowest latency, highest throughput
- Tailscale uses NAT traversal to establish these
- Most connections end up direct

**2. Peer Relay connections (good fallback):**
- Traffic relayed through another device in your tailnet
- You designate specific devices as peer relays
- Lower latency than DERP (runs in your infrastructure)
- Requires Tailscale v1.86+, grant policy with `tailscale.com/cap/relay`
- Not available on iOS/Android/Apple TV as relay servers (can use them as clients)

**3. DERP Relayed connections (last resort):**
- Traffic relayed through Tailscale's global DERP servers
- Higher latency but always available
- All DERP traffic is still end-to-end encrypted (DERP can't decrypt)

**Connection negotiation flow:**
1. Device A wants to reach Device B
2. Both connect to DERP servers (used for discovery/signaling)
3. Exchange connection details via DERP
4. Attempt NAT traversal for direct UDP connection
5. If direct fails → try peer relay
6. If peer relay unavailable → stay on DERP
7. Tailscale periodically retries upgrading to direct

**Diagnosing connections:**
- `tailscale status` — shows "direct", "relay", or "peer-relay" per peer
- `tailscale ping <host>` — shows connection path and latency
- `tailscale netcheck` — shows DERP latency and NAT type

### DERP Servers
DERP = Designated Encrypted Relay for Packets. Two purposes:
1. Connection negotiation (DISCO protocol for discovery)
2. Fallback relay when direct connections fail

**Tailscale DERP locations (30+ servers):**
- US: Ashburn, Chicago, Dallas, Denver, Honolulu, LA, Miami, NYC, SF, Seattle
- Europe: Amsterdam, Frankfurt, Helsinki, London, Madrid, Nuremberg, Paris, Warsaw
- Asia-Pacific: Bengaluru, Hong Kong, Singapore, Sydney, Tokyo
- Other: Dubai, Johannesburg, Nairobi, São Paulo, Toronto

**Key facts:**
- Dual-stack (IPv4 + IPv6) — can bridge IPv4-only ↔ IPv6-only devices
- Each client picks a "home" DERP based on latency
- DERP map is cached locally — survives coordination server outages
- Custom DERP servers possible but rarely needed (build `cmd/derper` binary)
- Can disable specific DERP regions via policy file for compliance

### Peer Relay (New Feature)
Alternative to DERP for environments with hard NAT/firewalls:
- Configure a device: `tailscale set --relay-server-port 40000`
- Create grant policy with `tailscale.com/cap/relay` capability
- Best for: corporate networks, cloud VPCs behind strict NAT
- Advantages over DERP: lower latency, no egress costs, in your infrastructure
- Use specific tags/hostnames in grant src (avoid `*` — causes unintended routing)

### Control Plane vs Data Plane

**Control Plane (Tailscale coordination server):**
- Centralized server managing: authentication, key distribution, policy enforcement, device discovery, NAT traversal coordination, DERP region selection
- Does NOT route any traffic — only metadata/configuration
- If coordination server goes down:
  - Existing connections continue working
  - Cached policies still enforced
  - Can't establish NEW connections or update keys/policies

**Data Plane (on each device):**
- Handles actual encrypted packet movement via WireGuard
- Establishes tunnels, encrypts/decrypts, routes packets
- Applies access control rules from control plane
- Monitors connection health, manages failover

**Key architectural insight:** Tailscale doesn't do authentication itself — it delegates to your identity provider (Google, GitHub, Okta, etc.) via OAuth 2.0/OIDC. The coordination server manages tokens and enforces policies, but never sees passwords.

---

## 4. Security & Access Control

### Access Control System
Default posture: *deny all*. All connections between devices are blocked unless explicitly permitted.

**Two methods (can coexist):**

**1. Grants (recommended, modern):**
- Unified syntax for network AND application layer permissions
- Define: source → destination → capabilities
- Supports app-level capabilities (e.g., `tailscale.com/cap/relay`, SSH, etc.)
- More flexible, more granular

**2. ACLs (legacy, still supported):**
- Network-layer only
- Simpler syntax: source → destination → ports
- Tailscale recommends migrating to grants

**Targets & Selectors:**
- Users (email addresses)
- Groups (custom-defined)
- Tags (device tags like `tag:server`)
- Autogroups (built-in like `autogroup:member`)
- IP addresses / CIDR ranges
- IP Sets (named network segments)

### Tailnet Policy File
Central HuJSON configuration file controlling your tailnet. Sections:
- `acls` — network-level access rules
- `grants` — network + app-level access rules
- `groups` — named user/device groupings
- `tagOwners` — who can assign which tags
- `hosts` — hostname aliases
- `ipsets` — named network segments
- `ssh` — Tailscale SSH rules
- `nodeAttrs` — extra device attributes (e.g., DNS overrides)
- `postures` — device posture rules
- `autoApprovers` — bypass approval for subnet routers/exit nodes
- `tests` / `sshTests` — policy assertions
- `derpMap` — customize DERP server usage

Managed via: admin console, GitOps (GitHub/GitLab/Bitbucket), or API.

### Tailscale Encryption
- All traffic encrypted end-to-end with WireGuard
- Uses Curve25519 for key exchange, ChaCha20-Poly1305 for encryption
- Private keys never leave the device
- Even DERP-relayed traffic is encrypted — DERP servers can't read it
- Additional SSH encryption layer when using Tailscale SSH

### Tailnet Lock
Prevents the Tailscale coordination server from being a single point of compromise:
- Devices must be "signed" by trusted signing keys before joining the tailnet
- Even if someone compromises your Tailscale account, they can't add unauthorized devices
- Signing keys are held by trusted admins (not stored on Tailscale's servers)
- Must be explicitly enabled — not on by default

### HTTPS Certificates
- Tailscale auto-provisions TLS certificates for `*.ts.net` hostnames
- Uses Let's Encrypt with DNS-01 challenges (Tailscale manages the DNS records)
- Required for Serve and Funnel
- Enable in admin console → DNS → HTTPS Certificates
- `tailscale cert <hostname>` to manually provision/renew
- Certificates are standard Let's Encrypt certs — trusted by all browsers

### Tailscale SSH
Replaces traditional SSH key management with Tailscale identity:
- Tailscale manages authentication via your identity provider
- No SSH key distribution needed — uses WireGuard node keys
- Centralized access control via policy file (not authorized_keys)
- User revocation is instant (update policy → seconds to enforce)
- "Check mode" — require re-authentication for high-risk connections (e.g., root)
- SSH session recording available for compliance/audit
- Doesn't modify `/etc/ssh/sshd_config` — non-Tailscale SSH still works
- Server-side: Linux and macOS (open-source variant) only
- Client-side: any Tailscale device

Enable: `tailscale set --ssh` on the destination device, plus SSH rules in policy file.

---

## 5. Network Features

### Subnet Routers
Expose entire subnets to your tailnet without installing Tailscale on every device:
- A device advertises routes: `tailscale set --advertise-routes=192.168.1.0/24`
- Other tailnet devices can reach `192.168.1.x` through the subnet router
- Great for: legacy devices, IoT, printers, NAS, anything that can't run Tailscale
- Must be approved in admin console (or via `autoApprovers` in policy)
- Can advertise multiple subnets from one device
- High-availability: multiple devices can advertise the same subnet

### Exit Nodes
Route ALL internet traffic through a specific tailnet device:
- Advertise: `tailscale set --advertise-exit-node` on the exit node device
- Use: `tailscale set --exit-node=<hostname>` on the client device
- Use cases: access geo-restricted content, route through a trusted network, comply with corporate policies
- Can run on cloud VMs, home servers, etc.
- Must be approved in admin console (or `autoApprovers`)
- Only one exit node active per client at a time

### Device Sharing
Share specific devices with people outside your tailnet:
- Invite external users by email
- They get access to specific devices only (not the whole tailnet)
- Shared users appear in your device list with limited permissions
- Great for: sharing a dev server with a contractor, giving a friend access to a game server
- Access control rules still apply to shared devices

---

## 6. What's Relevant to Our Setup

**Currently active on our tailnet (`orca-decibel.ts.net`):**
- `nabu-2wd56m3-1` (WSL/Linux) — Coconut's home, Funnel active → proxying to OpenClaw on 127.0.0.1:18789
- `nabu-2wd56m3` (Windows) — Joel's Windows host
- `iphone-15` (iOS) — Joel's phone

**Funnel config:** `https://nabu-2wd56m3-1.orca-decibel.ts.net` → `http://127.0.0.1:18789` (OpenClaw web UI, publicly accessible)

**Potential next steps to explore:**
- *NextDNS/Control D* — ad/malware blocking across all devices
- *Tailscale SSH* — keyless SSH to the WSL instance from anywhere
- *Subnet routers* — if Joel wants to reach other LAN devices remotely
- *Exit nodes* — route phone traffic through home network
- *Tailnet Lock* — harden against account compromise
- *Serve* — share internal services with tailnet without public exposure

---

_Sources: 20+ pages from tailscale.com/docs, fetched 3 layers deep from initial feature pages._
