# Lesson: Use gh_auto for GitHub Operations — Never Push Directly

## Observation
2026-04-24: When trying to push context-reset commits, I used `git push` directly and got "Permission denied" because the default credential (joel-ginsberg_tmemu) doesn't have access to grobomo repos. Joel has `gh_auto` — a script that automatically switches GitHub accounts based on `.github/publish.json` in each project.

## The System

**gh_auto** — automatic GitHub account switching.
- Location: `~/.local/bin/gh_auto` (WSL) / `~/bin/gh_auto` (Windows)
- Source: `/mnt/c/Users/joelg/Documents/ProjectsCL1/_grobomo/gh-auto/gh_auto`

### How it works:
1. Walks up from `$PWD` looking for `.github/publish.json`
2. Reads `github_account` field (e.g. `"grobomo"` or `"joel-ginsberg_tmemu"`)
3. Gets the correct auth token via `gh auth token -u <account>`
4. Sets `GH_TOKEN` to that account's token
5. Forwards git subcommands (`push`, `pull`, `fetch`) to `git`
6. Forwards everything else to `gh` CLI

### Safety checks (automatic, every command):
- **Folder-account consistency:** Projects under `_grobomo/` MUST use the `grobomo` account. Projects under `_tmemu/` MUST use `joel-ginsberg_tmemu`. Aborts on mismatch.
- **Remote URL check:** Verifies the git remote URL matches the publish.json account. Aborts on mismatch.
- **Token check:** Verifies a valid token exists for the account. Aborts if missing.

### publish.json format:
```json
{
  "github_account": "grobomo",
  "visibility": "public",
  "reason": "Context reset wrapper for Claude Code. No customer data or secrets."
}
```

### Usage:
```bash
# Instead of: git push origin main
gh_auto push origin main

# Instead of: gh pr create --title "..."
gh_auto pr create --title "..."

# Verify consistency
gh_auto check

# Get token for a specific account (for scripts)
gh_auto get-token grobomo
```

### WSL caveat:
`gh_auto push` forwards to `git push` with `GH_TOKEN` set, but git's credential helper may still use the wrong cached credential. If push fails with "Permission denied", use the token URL directly:
```bash
GH_TOKEN=$(gh auth token -u grobomo) && git push "https://grobomo:${GH_TOKEN}@github.com/grobomo/repo.git" main
```

## Rules for Coconut
1. **ALWAYS use `gh_auto` instead of raw `git push` or `gh` for Joel's projects**
2. Check for `.github/publish.json` in any project before pushing
3. If `gh_auto` isn't available, use `gh auth token -u <account>` to get the right token
4. Never hardcode tokens — always derive from `gh auth`
5. grobomo repos = grobomo account, tmemu repos = tmemu account, never cross them

## Source
- Script: grobomo/gh-auto
- Conversation with: Joel, 2026-04-24
- Date observed: 2026-04-24

## Retrieval Triggers
- Pushing to GitHub
- Permission denied on push
- GitHub account switching
- gh_auto, publish.json
- grobomo vs tmemu repos
- "can't push to grobomo"
