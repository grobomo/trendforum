# SOP: Software Research & Evaluation

_Source: Joel Ginsberg, Teams message 2026-07-16. Canonical reference for how we vet new tools, services, and dependencies._

## The Pipeline

### Step 1: Vet the Software Maker
Before installing or building on any new service/app, research:
- **Open source?** Prefer OSS with transparent code
- **Widely used?** Large user base = more eyeballs on bugs
- **Frequently updated?** Active development, not abandonware
- **Many contributors?** Healthy community, not a single-maintainer project
- **Third-party security audits?** Independent verification > trust-me claims
- **Internal controls?** NIST, FedRAMP, SOC2, etc.
- **Active community?** Forums, Discord, GitHub issues with responsive maintainers
- **Good reputation?** User feedback, company track record

### Step 2: Research the Code
After vetting the maker, dig into the implementation:
- How does it work? (architecture, dependencies)
- Is it secure? (auth model, data handling, known CVEs)
- Well-built? (code quality, test coverage, CI/CD)
- Easy to use? (docs, onboarding experience, learning curve)
- Modular? (pluggable, composable, not monolithic)
- Standardized? (uses industry standards, APIs, protocols)
- **Don't pretend to know everything** — ask other bots, Google what you should be Googling for. Wisdom = knowing what you don't know.

### Step 3: Google Search Strategy
Joel's IT troubleshooting secret sauce:

> **"Identify Core Problem + Describe Platform + Google Search"**

1. Start with: `"how to solve X problem, on Y platform"`
2. Add qualifiers: `"gotchas"`, `"<current year>"`, `"reddit"`
3. **Reddit** is the best source for unfiltered, non-marketing feedback (anonymous accounts = honest opinions)
4. Group research tabs in a single browser window per task

### Step 4: Document What You Learned
- Use the most effective (easy to remember) method possible
- Options to test: LLM-wiki, structured markdown files, Trello cards
- **Scientific method for documentation systems:**
  1. Define core problem and solution requirements
  2. Design 2-3 candidate systems
  3. Define success criteria and hypotheses
  4. Test each system
  5. Collect results and analyze
  6. Write down findings
  7. Share with team
  8. Repeat / iterate

## When This Applies
- Any time we consider new software, tools, or dependencies
- When brainstorming solutions to problems
- When evaluating third-party integrations
- Before committing to any new service in the stack

## Reference Links (Tailscale Funnel Research Example)
- [Google: enable tailscale funnel gotchas windows](https://www.google.com/search?q=enable+tailscale+funnel+gotchas+windows)
- [Reddit: Problems with Tailscale Funnel](https://www.reddit.com/r/Tailscale/comments/19alg5b/problems_with_tailscale_funnel_and_some_service…)
- [Tailscale Funnel Docs](https://tailscale.com/docs/features/tailscale-funnel)
- [GitHub Issue #15043](https://github.com/tailscale/tailscale/issues/15043)
- [How I Use Tailscale (blog)](https://chameth.com/how-i-use-tailscale/)
- [Tailscale Connectivity Troubleshooting](https://tailscale.com/docs/reference/troubleshooting/connectivity/connect-device-failure)
- [YouTube: Tailscale Funnel](https://www.youtube.com/watch?v=qAuPoAQImo0)

---

_This is a living document. Update as the process evolves._
