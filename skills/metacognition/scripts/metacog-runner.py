#!/usr/bin/env python3
"""Metacognition Cron Runner — loads modules.yaml and executes enabled modules.

Usage:
    python3 metacog-runner.py --tier quick          # Run all quick-tier modules
    python3 metacog-runner.py --tier deep            # Run all deep-tier modules
    python3 metacog-runner.py --module conflict-resolution  # Run one module
    python3 metacog-runner.py --tier deep --dry-run  # Show what would run
    python3 metacog-runner.py --list                 # List all modules + status
"""

import argparse
import os
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
MODULES_YAML = SKILL_DIR / "modules.yaml"
MODULES_DIR = Path(__file__).resolve().parent / "modules"
OUTPUT_DIR = Path.home() / ".openclaw/workspace/memory/metacognition"


def load_modules() -> dict:
    """Load modules.yaml and return modules dict."""
    if not MODULES_YAML.exists():
        print(f"ERROR: {MODULES_YAML} not found", file=sys.stderr)
        sys.exit(2)
    with open(MODULES_YAML) as f:
        data = yaml.safe_load(f)
    return data.get("modules", {})


def run_module(name: str, module_config: dict) -> int:
    """Run a single module. Returns exit code."""
    script = MODULES_DIR / f"{name}.py"
    if not script.exists():
        print(f"  ⚠️  Script not found: {script}")
        return 2

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, str(script), "--output-dir", str(OUTPUT_DIR)]

    # Pass config as env vars prefixed with METACOG_
    env = os.environ.copy()
    config = module_config.get("config", {})
    for k, v in config.items():
        env[f"METACOG_{k.upper()}"] = str(v)

    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=120
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"  ⏰ TIMEOUT: {name} exceeded 120s")
        return 2
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return 2


def main():
    parser = argparse.ArgumentParser(description="Metacognition cron runner")
    parser.add_argument("--tier", choices=["quick", "deep"], help="Run modules for this tier")
    parser.add_argument("--module", help="Run a specific module by name")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run")
    parser.add_argument("--list", action="store_true", help="List all modules")
    args = parser.parse_args()

    modules = load_modules()

    if args.list:
        print("# Metacognition Modules")
        print(f"{'Name':<25} {'Tier':<8} {'Enabled':<9} Description")
        print("-" * 80)
        for name, cfg in sorted(modules.items()):
            enabled = "✅" if cfg.get("enabled") else "❌"
            tier = cfg.get("tier", "?")
            desc = cfg.get("description", "")[:40]
            print(f"{name:<25} {tier:<8} {enabled:<9} {desc}")
        return

    if args.module:
        # Run single module regardless of tier/enabled
        if args.module not in modules:
            print(f"ERROR: Unknown module '{args.module}'")
            print(f"Available: {', '.join(modules.keys())}")
            sys.exit(2)
        cfg = modules[args.module]
        print(f"🧠 Running: {args.module} (tier={cfg.get('tier', '?')})")
        if args.dry_run:
            print(f"  [DRY RUN] Would run {MODULES_DIR / f'{args.module}.py'}")
            return
        rc = run_module(args.module, cfg)
        sys.exit(rc)

    if not args.tier:
        parser.error("--tier or --module required")

    # Run all enabled modules for the given tier
    to_run = [
        (name, cfg)
        for name, cfg in modules.items()
        if cfg.get("enabled") and cfg.get("tier") == args.tier
    ]

    if not to_run:
        print(f"No enabled modules for tier '{args.tier}'")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"🧠 Metacognition {args.tier} tier — {timestamp}")
    print(f"   Modules: {', '.join(n for n, _ in to_run)}")

    if args.dry_run:
        for name, cfg in to_run:
            script = MODULES_DIR / f"{name}.py"
            exists = "✅" if script.exists() else "❌ MISSING"
            print(f"  [DRY RUN] {name} — {exists}")
        return

    results = {}
    for name, cfg in to_run:
        print(f"\n--- {name} ---")
        rc = run_module(name, cfg)
        results[name] = rc
        status = {0: "✅ ok", 1: "📋 findings", 2: "❌ error"}.get(rc, f"? ({rc})")
        print(f"  Result: {status}")

    # Summary
    print(f"\n--- Summary ---")
    for name, rc in results.items():
        icon = {0: "✅", 1: "📋", 2: "❌"}.get(rc, "?")
        print(f"  {icon} {name}")


if __name__ == "__main__":
    main()
