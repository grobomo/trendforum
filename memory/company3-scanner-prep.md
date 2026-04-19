# Company 3 — Containerized Scanner Prep (Monday Call)

## Context
- **Contact:** Robert Romero, Sr. Director Core Infrastructure
- **Issue:** Got containerized scanner working with Service Gateway on port 80, no TLS, no API key
- **Robert's words:** "I don't understand why it works, but it works"
- **Security concern:** Unencrypted, unauthenticated scanner traffic
- **Andre Fernandes may join the call**

## Robert's Email (Apr 18)
> Not sure what virtual appliance we are referring to.
> But we somehow got it working with our service gateway.
> But it looks like it is possibly unintended usage that works.
> We set Andres' scanner/wrapper to connect to our service gateway over port 80, no TLS, and no API key and it just works.

## Key Questions for Monday
1. What "scanner/wrapper" did Andre build? (Custom wrapper around V1FS SDK?)
2. Is the SG exposing an unauthenticated scanning endpoint on port 80?
3. Is this the FSVA module inside the SG, or a standalone containerized scanner?
4. What platforms need scanning? (Mac + Windows EC2 per Trello card)

## Research Notes
- V1 File Security (V1FS) can run as:
  - FSVA module inside Service Gateway (K8s-based, self-healing)
  - Standalone containerized scanner
  - SDK integration (stream/off-stream scanning)
- Franz Fiorim (SE-NA) has deep experience with V1FS SDK across enterprise customers
- Standard deployment should use TLS + API key — port 80 without auth is likely an SG misconfiguration or dev endpoint

## Prep TODO
- [ ] Test deploying containerized scanner on Mac EC2
- [ ] Test deploying on Windows EC2
- [ ] Document proper TLS + API key setup
- [ ] Check if port 80 without auth is a known SG behavior or security gap
- [ ] Prepare walkthrough for Robert
