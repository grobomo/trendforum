#!/usr/bin/env python3
"""Metacognition Module Discovery — scans for metacog.yaml manifests.

Discovers metacognition modules contributed by extensions, projects, and skills.
Delegates approval tracking to the UNIFIED APPROVAL PIPELINE when available,
falls back to local registry otherwise.

Usage:
    python3 discovery.py scan              # Scan for new metacog.yaml files
    python3 discovery.py status            # Show all discovered modules + status
    python3 discovery.py approve <id>      # Approve a module after monitoring
    python3 discovery.py suspend <id>      # Suspend a module
    python3 discovery.py verify            # Re-verify hashes of approved modules
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

WORKSPACE = Path.home() / ".openclaw" / "workspace"
EXTENSIONS_DIR = Path.home() / ".openclaw" / "extensions"
SKILL_DIR = Path(__file__).resolve().parent.parent

# Try to import unified pipeline
sys.path.insert(0, str(WORKSPACE / "approval-pipeline"))
try:
    from pipeline import ApprovalPipeline, EvidenceConfig
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False
REGISTRY_PATH = SKILL_DIR / "discovered.yaml"

# How long a module must be monitored before it can be approved
DEFAULT_MONITORING_HOURS = 24

# Directories to scan for metacog.yaml manifests
SCAN_DIRS = [
    EXTENSIONS_DIR,                          # ~/.openclaw/extensions/*/metacognition/
    WORKSPACE / "skills",                    # workspace skills
    WORKSPACE / "plugins",                   # workspace plugin sources
    Path.home() / "openclaw-dm",             # openclaw-dm project
]

# Patterns that flag a script as suspicious during static analysis
SUSPICIOUS_PATTERNS = [
    "os.system",
    "subprocess.call",
    "subprocess.Popen",
    "subprocess.run",
    "urllib.request",
    "requests.get",
    "requests.post",
    "socket.",
    "http.client",
    "smtplib",
    "ftplib",
    "paramiko",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
]


def hash_file(path: Path) -> str:
    """SHA256 hash of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return f"sha256:{h.hexdigest()[:16]}"


def hash_directory(dir_path: Path) -> str:
    """SHA256 hash of all files in a directory."""
    h = hashlib.sha256()
    for f in sorted(dir_path.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(dir_path)).encode())
            h.update(f.read_bytes())
    return f"sha256:{h.hexdigest()[:16]}"


def load_registry() -> dict:
    """Load the discovery registry."""
    if not REGISTRY_PATH.exists():
        return {"discovered": [], "modules": {}}
    try:
        if yaml:
            with open(REGISTRY_PATH) as f:
                return yaml.safe_load(f) or {"discovered": [], "modules": {}}
        else:
            # JSON fallback
            with open(REGISTRY_PATH) as f:
                return json.load(f)
    except Exception:
        return {"discovered": [], "modules": {}}


def save_registry(registry: dict):
    """Save the discovery registry."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if yaml:
        with open(REGISTRY_PATH, "w") as f:
            yaml.dump(registry, f, default_flow_style=False, sort_keys=False)
    else:
        with open(REGISTRY_PATH, "w") as f:
            json.dump(registry, f, indent=2, default=str)


def parse_manifest(manifest_path: Path) -> dict:
    """Parse a metacog.yaml manifest file."""
    try:
        if yaml:
            with open(manifest_path) as f:
                data = yaml.safe_load(f)
        else:
            # Try JSON fallback
            with open(manifest_path) as f:
                data = json.load(f)
        return data or {}
    except Exception as e:
        return {"_error": str(e)}


def static_analyze_script(script_path: Path) -> dict:
    """Quick static analysis of a script for suspicious patterns."""
    result = {
        "path": str(script_path),
        "exists": script_path.exists(),
        "suspicious": [],
        "safe": True,
    }
    if not script_path.exists():
        result["safe"] = False
        result["suspicious"].append("File does not exist")
        return result

    try:
        source = script_path.read_text(errors="replace")
    except Exception as e:
        result["safe"] = False
        result["suspicious"].append(f"Cannot read: {e}")
        return result

    result["lines"] = source.count("\n") + 1
    result["size"] = len(source)

    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in source:
            # Find line numbers
            for i, line in enumerate(source.splitlines(), 1):
                if pattern in line and not line.strip().startswith("#"):
                    result["suspicious"].append(f"L{i}: {pattern} — `{line.strip()[:80]}`")
                    result["safe"] = False

    return result


def discover_manifests() -> list:
    """Scan all directories for metacog.yaml files."""
    found = []

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue

        # Look for metacognition/metacog.yaml at root and up to 3 levels deep
        for depth in range(0, 4):
            if depth == 0:
                pattern = "metacognition/metacog.yaml"
            else:
                pattern = "/".join(["*"] * depth) + "/metacognition/metacog.yaml"
            for manifest in scan_dir.glob(pattern):
                # Determine project name from parent structure
                metacog_dir = manifest.parent
                project_dir = metacog_dir.parent
                project_name = project_dir.name

                found.append({
                    "manifest_path": str(manifest),
                    "metacog_dir": str(metacog_dir),
                    "project_name": project_name,
                    "project_dir": str(project_dir),
                    "source_root": str(scan_dir),
                })

    return found


def module_id(project_name: str, module_name: str) -> str:
    """Generate a unique module ID."""
    return f"{project_name}/{module_name}"


def do_scan():
    """Scan for new metacog.yaml files and update registry."""
    registry = load_registry()
    manifests = discover_manifests()
    now = datetime.now(timezone.utc).isoformat()

    new_count = 0
    changed_count = 0

    for manifest_info in manifests:
        manifest_path = Path(manifest_info["manifest_path"])
        metacog_dir = Path(manifest_info["metacog_dir"])
        project_name = manifest_info["project_name"]

        # Parse the manifest
        data = parse_manifest(manifest_path)
        if "_error" in data:
            print(f"  ⚠️  Error parsing {manifest_path}: {data['_error']}")
            continue

        manifest_hash = hash_file(manifest_path)
        dir_hash = hash_directory(metacog_dir)

        # Check if already discovered
        existing = None
        for d in registry["discovered"]:
            if d.get("manifest_path") == str(manifest_path):
                existing = d
                break

        if existing:
            # Check for changes
            if existing.get("dir_hash") != dir_hash:
                print(f"  🔄 CHANGED: {manifest_path}")
                existing["dir_hash"] = dir_hash
                existing["manifest_hash"] = manifest_hash
                existing["last_changed"] = now
                changed_count += 1

                # Suspend any approved modules from this manifest
                modules = data.get("modules", {})
                for mod_name in modules:
                    mid = module_id(project_name, mod_name)
                    if mid in registry["modules"]:
                        old_status = registry["modules"][mid].get("status")
                        if old_status == "approved":
                            registry["modules"][mid]["status"] = "suspended"
                            registry["modules"][mid]["suspend_reason"] = "Script changed after approval"
                            registry["modules"][mid]["suspended_at"] = now
                            print(f"  🚨 SUSPENDED: {mid} (code changed after approval)")
        else:
            # New discovery
            print(f"  🆕 NEW: {manifest_path}")
            registry["discovered"].append({
                "manifest_path": str(manifest_path),
                "metacog_dir": str(metacog_dir),
                "project_name": project_name,
                "project_dir": manifest_info["project_dir"],
                "found_at": now,
                "manifest_hash": manifest_hash,
                "dir_hash": dir_hash,
            })
            new_count += 1

        # Process modules from manifest
        modules = data.get("modules", {})
        for mod_name, mod_config in modules.items():
            mid = module_id(project_name, mod_name)

            if mid not in registry["modules"]:
                # New module — static analyze then set to monitoring
                script_name = mod_config.get("script", f"{mod_name}.py")
                script_path = metacog_dir / script_name

                analysis = static_analyze_script(script_path)

                registry["modules"][mid] = {
                    "id": mid,
                    "project": project_name,
                    "name": mod_name,
                    "description": mod_config.get("description", ""),
                    "tier": mod_config.get("tier", "deep"),
                    "script_path": str(script_path),
                    "script_hash": hash_file(script_path) if script_path.exists() else None,
                    "status": "monitoring",
                    "discovered_at": now,
                    "monitoring_started": now,
                    "monitoring_hours_required": mod_config.get(
                        "monitoring_hours", DEFAULT_MONITORING_HOURS
                    ),
                    "monitoring_runs": 0,
                    "monitoring_findings": [],
                    "static_analysis": {
                        "safe": analysis["safe"],
                        "suspicious_count": len(analysis.get("suspicious", [])),
                        "suspicious": analysis.get("suspicious", [])[:10],
                        "lines": analysis.get("lines", 0),
                        "size": analysis.get("size", 0),
                    },
                    "approved_at": None,
                    "approved_by": None,
                }

                safety = "✅ clean" if analysis["safe"] else f"⚠️ {len(analysis['suspicious'])} suspicious pattern(s)"
                print(f"    📋 Module: {mid} → monitoring ({safety})")

    save_registry(registry)

    # Check for modules ready for approval
    ready = []
    for mid, mod in registry["modules"].items():
        if mod["status"] == "monitoring":
            started = datetime.fromisoformat(mod["monitoring_started"])
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            elapsed = datetime.now(timezone.utc) - started
            required = timedelta(hours=mod.get("monitoring_hours_required", DEFAULT_MONITORING_HOURS))
            if elapsed >= required:
                mod["status"] = "pending-approval"
                ready.append(mid)

    if ready:
        save_registry(registry)
        print(f"\n📋 {len(ready)} module(s) ready for approval:")
        for mid in ready:
            print(f"  → {mid}")

    print(f"\nScan complete: {new_count} new, {changed_count} changed, "
          f"{len(registry['modules'])} total modules")


def do_status():
    """Show status of all discovered modules."""
    registry = load_registry()

    if not registry["discovered"]:
        print("No metacog.yaml files discovered yet. Run 'scan' first.")
        return

    print("# Discovered Metacognition Sources\n")
    for d in registry["discovered"]:
        print(f"📦 {d['project_name']}")
        print(f"   Path: {d['manifest_path']}")
        print(f"   Found: {d['found_at'][:19]}")
        print(f"   Hash: {d.get('dir_hash', '?')}")
        print()

    print("# Module Status\n")
    print(f"{'ID':<40} {'Status':<20} {'Tier':<8} {'Safe':<6} Notes")
    print("-" * 100)

    for mid, mod in sorted(registry["modules"].items()):
        status = mod["status"]
        icon = {
            "monitoring": "👁️",
            "pending-approval": "⏳",
            "approved": "✅",
            "suspended": "🚨",
            "disabled": "❌",
        }.get(status, "?")

        safe = "✅" if mod.get("static_analysis", {}).get("safe") else "⚠️"
        tier = mod.get("tier", "?")

        notes = ""
        if status == "monitoring":
            started = datetime.fromisoformat(mod["monitoring_started"])
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            elapsed = datetime.now(timezone.utc) - started
            remaining = timedelta(hours=mod.get("monitoring_hours_required", 24)) - elapsed
            if remaining.total_seconds() > 0:
                hours = remaining.total_seconds() / 3600
                notes = f"{hours:.1f}h remaining"
            else:
                notes = "ready for approval"
        elif status == "suspended":
            notes = mod.get("suspend_reason", "")[:30]

        print(f"{mid:<40} {icon} {status:<17} {tier:<8} {safe:<6} {notes}")


def do_approve(module_id_str: str):
    """Approve a module after monitoring."""
    registry = load_registry()

    if module_id_str not in registry["modules"]:
        print(f"❌ Module '{module_id_str}' not found")
        print(f"Available: {', '.join(registry['modules'].keys())}")
        sys.exit(1)

    mod = registry["modules"][module_id_str]

    if mod["status"] not in ("pending-approval", "monitoring"):
        print(f"⚠️  Module is '{mod['status']}', not pending-approval")
        if mod["status"] == "approved":
            print("Already approved.")
            return
        if mod["status"] == "suspended":
            print("Module is suspended. Investigate suspension reason before re-approving.")

    # Verify hash hasn't changed
    script_path = Path(mod["script_path"])
    if script_path.exists():
        current_hash = hash_file(script_path)
        if mod.get("script_hash") and current_hash != mod["script_hash"]:
            print(f"🚨 HASH MISMATCH — script changed since discovery!")
            print(f"   Expected: {mod['script_hash']}")
            print(f"   Current:  {current_hash}")
            print("Re-run 'scan' and restart monitoring.")
            sys.exit(1)

    # Check static analysis
    if not mod.get("static_analysis", {}).get("safe"):
        print(f"⚠️  Static analysis flagged suspicious patterns:")
        for s in mod.get("static_analysis", {}).get("suspicious", []):
            print(f"   {s}")
        print("\nApproving anyway (user override).")

    now = datetime.now(timezone.utc).isoformat()
    mod["status"] = "approved"
    mod["approved_at"] = now
    mod["approved_by"] = "human"  # Future: MFA verification
    mod["script_hash"] = hash_file(script_path) if script_path.exists() else mod.get("script_hash")

    save_registry(registry)

    # Sync to unified pipeline
    if PIPELINE_AVAILABLE:
        try:
            pipeline = ApprovalPipeline()
            pipeline_id = f"module:{module_id_str}"
            pipeline.submit(pipeline_id, kind="module", display_name=module_id_str)
            pipeline.approve(pipeline_id, approved_by="human")
            print(f"   ✅ Synced to unified approval pipeline")
        except Exception as e:
            print(f"   ⚠️  Pipeline sync failed: {e}")

    print(f"✅ Approved: {module_id_str}")
    print(f"   Approved at: {now}")
    print(f"   Note: Future versions will require MFA for approval")


def do_suspend(module_id_str: str):
    """Suspend an approved module."""
    registry = load_registry()

    if module_id_str not in registry["modules"]:
        print(f"❌ Module '{module_id_str}' not found")
        sys.exit(1)

    mod = registry["modules"][module_id_str]
    now = datetime.now(timezone.utc).isoformat()
    mod["status"] = "suspended"
    mod["suspended_at"] = now
    mod["suspend_reason"] = "Manual suspension"

    save_registry(registry)

    # Sync to unified pipeline
    if PIPELINE_AVAILABLE:
        try:
            pipeline = ApprovalPipeline()
            pipeline_id = f"module:{module_id_str}"
            pipeline.suspend(pipeline_id, reason="Manual suspension")
        except Exception:
            pass

    print(f"🚨 Suspended: {module_id_str}")


def do_verify():
    """Re-verify hashes of all approved modules."""
    registry = load_registry()
    issues = 0

    for mid, mod in registry["modules"].items():
        if mod["status"] != "approved":
            continue

        script_path = Path(mod["script_path"])
        if not script_path.exists():
            print(f"❌ {mid}: script missing — {mod['script_path']}")
            mod["status"] = "suspended"
            mod["suspend_reason"] = "Script file missing"
            issues += 1
            continue

        current_hash = hash_file(script_path)
        expected = mod.get("script_hash")
        if expected and current_hash != expected:
            print(f"🚨 {mid}: HASH MISMATCH — code changed since approval!")
            print(f"   Expected: {expected}")
            print(f"   Current:  {current_hash}")
            mod["status"] = "suspended"
            mod["suspend_reason"] = f"Hash mismatch: expected {expected}, got {current_hash}"
            mod["suspended_at"] = datetime.now(timezone.utc).isoformat()
            issues += 1
        else:
            print(f"✅ {mid}: verified")

    if issues:
        save_registry(registry)
        print(f"\n🚨 {issues} module(s) suspended due to verification failures")
    else:
        print(f"\n✅ All approved modules verified")


def get_approved_modules() -> list:
    """Get list of approved modules for the runner to execute.
    
    Called by metacog-runner.py to get project-contributed modules.
    """
    registry = load_registry()
    approved = []
    for mid, mod in registry["modules"].items():
        if mod["status"] == "approved":
            script_path = Path(mod["script_path"])
            # Re-verify hash before returning
            if script_path.exists():
                current = hash_file(script_path)
                if mod.get("script_hash") and current != mod["script_hash"]:
                    continue  # Silently skip — hash changed
                approved.append({
                    "id": mid,
                    "name": mod["name"],
                    "project": mod["project"],
                    "tier": mod.get("tier", "deep"),
                    "script_path": str(script_path),
                    "description": mod.get("description", ""),
                })
    return approved


def main():
    parser = argparse.ArgumentParser(description="Metacognition module discovery")
    parser.add_argument("action", choices=[
        "scan", "status", "approve", "suspend", "verify",
    ])
    parser.add_argument("module_id", nargs="?", help="Module ID for approve/suspend")
    args = parser.parse_args()

    if args.action == "scan":
        do_scan()
    elif args.action == "status":
        do_status()
    elif args.action == "approve":
        if not args.module_id:
            print("Usage: discovery.py approve <module-id>")
            sys.exit(1)
        do_approve(args.module_id)
    elif args.action == "suspend":
        if not args.module_id:
            print("Usage: discovery.py suspend <module-id>")
            sys.exit(1)
        do_suspend(args.module_id)
    elif args.action == "verify":
        do_verify()


if __name__ == "__main__":
    main()
