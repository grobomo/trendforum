#!/usr/bin/env python3
"""Deep Dependency Analyzer — traces script call chains up to N layers deep.

For each cron job:
1. Extract script path(s) from the cron prompt
2. Read the script source
3. Trace: imports, subprocess calls, file reads/writes, network calls, env vars
4. Recurse into called scripts (up to --depth layers)
5. Build a dependency graph
6. Overlay against new metacognition modules to find coverage/gaps

Outputs a structured analysis document and JSON dependency graph.

Usage:
    python3 deep_analyzer.py                    # Full analysis, 10 layers deep
    python3 deep_analyzer.py --depth 5          # 5 layers
    python3 deep_analyzer.py --cron self-audit   # Analyze one cron only
    python3 deep_analyzer.py --script /path/to/script.py  # Analyze one script
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

WORKSPACE = Path.home() / ".openclaw" / "workspace"
SKILL_DIR = Path(__file__).resolve().parent.parent
ANALYSES_DIR = SKILL_DIR / "analyses"
MODULES_DIR = Path(__file__).resolve().parent / "modules"

MAX_FILE_SIZE = 500_000  # Skip files larger than 500KB


# ── Script Path Extraction ──────────────────────────────────────────

def extract_script_paths(prompt: str) -> list:
    """Extract script/file paths from a cron prompt string."""
    paths = []

    # Pattern: python3 /path/to/script.py
    for m in re.finditer(r'(?:python3?|node|bash|sh)\s+([^\s;|&]+\.(?:py|js|sh|bash))', prompt):
        paths.append(m.group(1))

    # Pattern: /absolute/path/to/script.py (standalone paths)
    for m in re.finditer(r'(?:^|\s)((?:/[\w._-]+)+\.(?:py|js|sh|bash))', prompt):
        p = m.group(1)
        if p not in paths:
            paths.append(p)

    # Pattern: ~/path or HOME-var/path
    for m in re.finditer(r'(~[\w/._-]+\.(?:py|js|sh|bash))', prompt):
        expanded = os.path.expanduser(m.group(1))
        if expanded not in paths:
            paths.append(expanded)

    return paths


# ── AST-based Python Analysis ───────────────────────────────────────

def analyze_python_ast(source: str, filepath: str) -> dict:
    """Parse Python source with AST to extract dependencies."""
    result = {
        "imports": [],
        "subprocess_calls": [],
        "file_operations": [],
        "network_calls": [],
        "env_vars": [],
        "script_calls": [],
        "class_names": [],
        "function_names": [],
        "constants": {},
        "errors": [],
    }

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        result["errors"].append(f"SyntaxError: {e}")
        # Fall back to regex analysis
        return {**result, **analyze_with_regex(source)}

    for node in ast.walk(tree):
        # Imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                result["imports"].append({
                    "type": "from",
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                })

        # subprocess calls
        elif isinstance(node, ast.Call):
            func_name = get_call_name(node)

            if func_name in (
                "subprocess.run", "subprocess.Popen", "subprocess.call",
                "subprocess.check_output", "subprocess.check_call",
                "os.system", "os.popen", "os.execvp",
            ):
                cmd = extract_call_arg(node, source)
                result["subprocess_calls"].append({
                    "function": func_name,
                    "command": cmd,
                    "line": node.lineno,
                })
                # Extract script paths from subprocess commands
                if cmd:
                    for sp in extract_script_paths(cmd):
                        result["script_calls"].append({
                            "path": sp,
                            "called_from": func_name,
                            "line": node.lineno,
                        })

            # File operations
            elif func_name in ("open", "builtins.open"):
                fpath = extract_call_arg(node, source)
                mode = extract_call_kwarg(node, "mode", source) or "r"
                result["file_operations"].append({
                    "function": "open",
                    "path": fpath,
                    "mode": mode,
                    "line": node.lineno,
                })
            elif func_name and any(
                func_name.endswith(f) for f in (
                    ".read_text", ".write_text", ".read_bytes",
                    "readFileSync", "writeFileSync",
                    "shutil.copy", "shutil.copy2", "shutil.move",
                    "shutil.copytree", "shutil.rmtree",
                )
            ):
                fpath = extract_call_arg(node, source)
                result["file_operations"].append({
                    "function": func_name,
                    "path": fpath,
                    "line": node.lineno,
                })

            # Network calls
            elif func_name and any(
                kw in func_name.lower() for kw in (
                    "requests.", "urllib", "http", "fetch",
                    "client.get", "client.post", "client.put",
                    "aiohttp", "httpx",
                )
            ):
                url = extract_call_arg(node, source)
                result["network_calls"].append({
                    "function": func_name,
                    "url": url,
                    "line": node.lineno,
                })

            # os.environ access
            elif func_name in ("os.environ.get", "os.getenv"):
                var = extract_call_arg(node, source)
                result["env_vars"].append({
                    "variable": var,
                    "line": node.lineno,
                })

            # keyring access
            elif func_name and "keyring" in func_name.lower():
                key = extract_call_arg(node, source)
                result["env_vars"].append({
                    "variable": f"keyring:{key}",
                    "line": node.lineno,
                })

        # String assignments that look like paths
        elif isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                val = node.value.value
                if val.startswith("/") and ("." in val.split("/")[-1]):
                    for target in node.targets:
                        name = get_target_name(target)
                        if name:
                            result["constants"][name] = val

        # Class and function names
        elif isinstance(node, ast.ClassDef):
            result["class_names"].append(node.name)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            result["function_names"].append(node.name)

    # Also catch sys.path manipulation
    result.update(analyze_sys_path(source))

    return result


def get_call_name(node: ast.Call) -> str:
    """Extract the function name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        parts = []
        current = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def get_target_name(node) -> Optional[str]:
    """Extract variable name from assignment target."""
    if isinstance(node, ast.Name):
        return node.id
    return None


def extract_call_arg(node: ast.Call, source: str) -> str:
    """Extract the first positional argument as a string."""
    if node.args:
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        elif isinstance(arg, ast.JoinedStr):
            return "<f-string>"
        elif isinstance(arg, ast.BinOp):
            return "<dynamic>"
        # Try to get the source text
        try:
            return ast.get_source_segment(source, arg) or "<complex>"
        except Exception:
            return "<complex>"
    return "<unknown>"


def extract_call_kwarg(node: ast.Call, name: str, source: str) -> Optional[str]:
    """Extract a keyword argument value."""
    for kw in node.keywords:
        if kw.arg == name:
            if isinstance(kw.value, ast.Constant):
                return str(kw.value.value)
    return None


def analyze_sys_path(source: str) -> dict:
    """Find sys.path manipulation for import resolution."""
    paths = []
    for m in re.finditer(
        r'sys\.path\.(?:insert|append)\(\s*(?:\d+\s*,\s*)?["\']([^"\']+)["\']', source
    ):
        paths.append(m.group(1))
    for m in re.finditer(
        r'sys\.path\.(?:insert|append)\(\s*(?:\d+\s*,\s*)?os\.path\.expanduser\(["\']([^"\']+)["\']\)',
        source,
    ):
        paths.append(os.path.expanduser(m.group(1)))
    return {"sys_path_additions": paths} if paths else {}


# ── Regex Fallback Analysis ─────────────────────────────────────────

def analyze_with_regex(source: str) -> dict:
    """Regex-based analysis for non-Python or unparseable files."""
    result = {
        "subprocess_calls": [],
        "file_operations": [],
        "network_calls": [],
        "script_calls": [],
        "env_vars": [],
    }

    # Script calls (bash: source, ., python3, node, etc.)
    for m in re.finditer(
        r'(?:python3?|node|bash|sh|source|\.)\s+([^\s;|&"]+\.(?:py|js|sh|bash))', source
    ):
        result["script_calls"].append({"path": m.group(1), "line": 0})

    # curl/wget calls
    for m in re.finditer(r'(?:curl|wget)\s+[^\n]*?(https?://[^\s"\']+)', source):
        result["network_calls"].append({"function": "curl/wget", "url": m.group(1), "line": 0})

    # File paths in quotes
    for m in re.finditer(r'["\'](/[\w/._ -]+\.(?:py|json|yaml|yml|md|txt|log))["\']', source):
        result["file_operations"].append({"path": m.group(1), "line": 0})

    # Environment variables
    for m in re.finditer(r'\$\{?(\w+)\}?', source):
        var = m.group(1)
        if var.isupper() and len(var) > 2:
            result["env_vars"].append({"variable": var, "line": 0})
    for m in re.finditer(r'os\.environ(?:\.get)?\[?["\'](\w+)', source):
        result["env_vars"].append({"variable": m.group(1), "line": 0})

    return result


# ── Shell Script Analysis ───────────────────────────────────────────

def analyze_shell(source: str, filepath: str) -> dict:
    """Analyze bash/sh scripts."""
    result = {
        "imports": [],
        "subprocess_calls": [],
        "file_operations": [],
        "network_calls": [],
        "env_vars": [],
        "script_calls": [],
        "function_names": [],
        "errors": [],
    }

    # Source/dot includes
    for m in re.finditer(r'(?:source|\.)\s+([^\s;|&]+)', source):
        result["script_calls"].append({"path": m.group(1), "called_from": "source", "line": 0})

    # Function definitions
    for m in re.finditer(r'^(\w+)\s*\(\)\s*\{', source, re.MULTILINE):
        result["function_names"].append(m.group(1))

    result.update(analyze_with_regex(source))
    return result


# ── JavaScript/Node Analysis ────────────────────────────────────────

def analyze_javascript(source: str, filepath: str) -> dict:
    """Analyze JavaScript/Node files with regex."""
    result = {
        "imports": [],
        "subprocess_calls": [],
        "file_operations": [],
        "network_calls": [],
        "env_vars": [],
        "script_calls": [],
        "function_names": [],
        "errors": [],
    }

    # require() calls
    for m in re.finditer(r'require\(["\']([^"\']+)["\']\)', source):
        result["imports"].append({"type": "require", "module": m.group(1), "line": 0})

    # import statements
    for m in re.finditer(r'import\s+.*?from\s+["\']([^"\']+)["\']', source):
        result["imports"].append({"type": "import", "module": m.group(1), "line": 0})

    # child_process / exec
    for m in re.finditer(
        r'(?:exec|execSync|spawn|spawnSync|execFile)\(\s*["\']([^"\']*)["\']', source
    ):
        result["subprocess_calls"].append({"function": "child_process", "command": m.group(1), "line": 0})

    # process.env
    for m in re.finditer(r'process\.env\.(\w+)', source):
        result["env_vars"].append({"variable": m.group(1), "line": 0})
    for m in re.finditer(r'process\.env\[["\'](\w+)["\']\]', source):
        result["env_vars"].append({"variable": m.group(1), "line": 0})

    # fetch/http calls
    for m in re.finditer(r'fetch\(["\']([^"\']+)["\']', source):
        result["network_calls"].append({"function": "fetch", "url": m.group(1), "line": 0})

    result.update(analyze_with_regex(source))
    return result


# ── File Analyzer (dispatch by type) ────────────────────────────────

def analyze_file(filepath: str) -> dict:
    """Analyze a single file, dispatching by file type."""
    p = Path(filepath)
    if not p.exists():
        return {"errors": [f"File not found: {filepath}"], "exists": False}
    if p.stat().st_size > MAX_FILE_SIZE:
        return {"errors": [f"File too large: {p.stat().st_size} bytes"], "exists": True}
    if p.is_dir():
        return {"errors": [f"Is a directory: {filepath}"], "exists": True}

    try:
        source = p.read_text(errors="replace")
    except Exception as e:
        return {"errors": [f"Cannot read: {e}"], "exists": True}

    ext = p.suffix.lower()
    info = {
        "path": str(p),
        "size": p.stat().st_size,
        "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        "type": ext,
        "exists": True,
        "line_count": source.count("\n") + 1,
    }

    if ext == ".py":
        info.update(analyze_python_ast(source, str(p)))
    elif ext in (".sh", ".bash"):
        info.update(analyze_shell(source, str(p)))
    elif ext == ".js":
        info.update(analyze_javascript(source, str(p)))
    elif ext in (".md", ".txt", ".yaml", ".yml", ".json"):
        # Non-executable: extract referenced paths
        info.update(analyze_with_regex(source))
        info["type"] = "config/doc"
    else:
        info.update(analyze_with_regex(source))

    return info


# ── Recursive Dependency Tracer ─────────────────────────────────────

def trace_dependencies(entry_path: str, max_depth: int = 10) -> dict:
    """Recursively trace all dependencies from an entry script."""
    graph = {}  # {path: analysis_dict}
    queue = [(entry_path, 0)]  # (path, depth)
    visited = set()

    while queue:
        current_path, depth = queue.pop(0)

        # Normalize path
        expanded = os.path.expanduser(current_path)
        resolved = str(Path(expanded).resolve()) if os.path.exists(expanded) else expanded

        if resolved in visited:
            continue
        if depth > max_depth:
            graph[resolved] = {"skipped": True, "reason": f"max depth {max_depth} exceeded"}
            continue

        visited.add(resolved)
        analysis = analyze_file(resolved)
        analysis["depth"] = depth
        graph[resolved] = analysis

        if not analysis.get("exists", False):
            continue

        # Queue child scripts
        for sc in analysis.get("script_calls", []):
            child_path = sc.get("path", "")
            if child_path and child_path not in visited:
                # Resolve relative paths against parent directory
                if not child_path.startswith("/"):
                    child_path = str(Path(resolved).parent / child_path)
                queue.append((child_path, depth + 1))

        # Queue imported local modules
        for imp in analysis.get("imports", []):
            module = imp.get("module", "")
            # Only follow local imports (not stdlib/pypi)
            if module.startswith(".") or module.startswith("/"):
                mod_path = resolve_import(module, resolved)
                if mod_path and mod_path not in visited:
                    queue.append((mod_path, depth + 1))
            elif imp.get("type") == "from":
                # Check if it's a local module via sys.path
                for sp in analysis.get("sys_path_additions", []):
                    candidate = Path(sp) / f"{module.replace('.', '/')}.py"
                    if candidate.exists():
                        queue.append((str(candidate), depth + 1))

        # Queue file operations that reference scripts
        for fop in analysis.get("file_operations", []):
            fpath = fop.get("path", "")
            if fpath and fpath.endswith((".py", ".js", ".sh")) and fpath not in visited:
                queue.append((fpath, depth + 1))

        # Queue subprocess-called scripts
        for sub in analysis.get("subprocess_calls", []):
            cmd = sub.get("command", "")
            for sp in extract_script_paths(cmd):
                if sp not in visited:
                    queue.append((sp, depth + 1))

    return graph


def resolve_import(module: str, from_file: str) -> Optional[str]:
    """Try to resolve a Python import to a file path."""
    parent = Path(from_file).parent
    if module.startswith("."):
        # Relative import
        dots = len(module) - len(module.lstrip("."))
        mod_parts = module.lstrip(".").split(".")
        base = parent
        for _ in range(dots - 1):
            base = base.parent
        candidate = base / "/".join(mod_parts)
        for ext in [".py", "/__init__.py"]:
            full = Path(str(candidate) + ext)
            if full.exists():
                return str(full)
    else:
        # Absolute import — check common local locations
        parts = module.split(".")
        for search_dir in [parent, parent.parent, WORKSPACE]:
            candidate = search_dir / "/".join(parts)
            for ext in [".py", "/__init__.py"]:
                full = Path(str(candidate) + ext)
                if full.exists():
                    return str(full)
    return None


# ── Cron Analysis ───────────────────────────────────────────────────

def get_cron_jobs() -> list:
    """Get all cron jobs."""
    try:
        r = subprocess.run(
            ["openclaw", "cron", "list", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            # Retry via shell
            r = subprocess.run(
                "openclaw cron list --json",
                shell=True, capture_output=True, text=True, timeout=30,
            )
        if r.returncode == 0:
            return json.loads(r.stdout).get("jobs", [])
    except Exception:
        pass
    return []


def analyze_cron_deep(job: dict, max_depth: int) -> dict:
    """Deep-analyze a single cron job."""
    name = job.get("name", "")
    prompt = job.get("payload", {}).get("message", "")
    script_paths = extract_script_paths(prompt)

    result = {
        "name": name,
        "id": job.get("id", ""),
        "schedule": job.get("schedule", {}),
        "model": job.get("payload", {}).get("model", "default"),
        "target": job.get("sessionTarget", ""),
        "timeout": job.get("payload", {}).get("timeoutSeconds"),
        "prompt": prompt,
        "entry_scripts": script_paths,
        "dependency_graph": {},
        "summary": {
            "total_files": 0,
            "total_lines": 0,
            "max_depth_reached": 0,
            "all_imports": [],
            "all_env_vars": [],
            "all_network_calls": [],
            "all_file_operations": [],
            "all_subprocess_calls": [],
            "missing_files": [],
            "errors": [],
        },
    }

    # Trace dependencies for each entry script
    for script_path in script_paths:
        graph = trace_dependencies(script_path, max_depth)
        result["dependency_graph"].update(graph)

    # Also analyze any inline commands in the prompt that aren't script calls
    # (e.g., direct python -c or shell commands)
    inline_deps = analyze_with_regex(prompt)
    result["inline_commands"] = inline_deps

    # Build summary
    summary = result["summary"]
    for path, info in result["dependency_graph"].items():
        if info.get("skipped"):
            continue
        if not info.get("exists", False):
            summary["missing_files"].append(path)
            continue

        summary["total_files"] += 1
        summary["total_lines"] += info.get("line_count", 0)
        summary["max_depth_reached"] = max(
            summary["max_depth_reached"], info.get("depth", 0)
        )

        for imp in info.get("imports", []):
            mod = imp.get("module", "")
            if mod and mod not in summary["all_imports"]:
                summary["all_imports"].append(mod)

        for ev in info.get("env_vars", []):
            var = ev.get("variable", "")
            if var and var not in summary["all_env_vars"]:
                summary["all_env_vars"].append(var)

        for nc in info.get("network_calls", []):
            summary["all_network_calls"].append({
                "file": path,
                "function": nc.get("function", ""),
                "url": nc.get("url", ""),
            })

        for fo in info.get("file_operations", []):
            summary["all_file_operations"].append({
                "file": path,
                "function": fo.get("function", ""),
                "path": fo.get("path", ""),
                "mode": fo.get("mode", ""),
            })

        for sc in info.get("subprocess_calls", []):
            summary["all_subprocess_calls"].append({
                "file": path,
                "function": sc.get("function", ""),
                "command": sc.get("command", ""),
            })

        summary["errors"].extend(info.get("errors", []))

    return result


# ── Report Generation ───────────────────────────────────────────────

def format_deep_analysis(cron_analyses: list, new_modules: list) -> str:
    """Format the deep analysis into a readable document."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M CDT")
    lines = [
        "# Deep Dependency Analysis — Metacognition Migration",
        f"Generated: {ts}",
        f"Depth: up to {cron_analyses[0].get('_max_depth', 10) if cron_analyses else 10} layers",
        "",
        "---",
        "",
    ]

    for ca in cron_analyses:
        name = ca["name"]
        summary = ca["summary"]

        lines.extend([
            f"## Cron: `{name}`",
            "",
            f"- Schedule: {ca['schedule']}",
            f"- Model: {ca['model']}",
            f"- Timeout: {ca.get('timeout', '?')}s",
            f"- Entry scripts: {', '.join(ca['entry_scripts']) or 'none (prompt-only)'}",
            "",
            "### Dependency Summary",
            "",
            f"- Total files traced: {summary['total_files']}",
            f"- Total lines of code: {summary['total_lines']:,}",
            f"- Max depth reached: {summary['max_depth_reached']}",
            f"- Missing files: {len(summary['missing_files'])}",
            f"- Unique imports: {len(summary['all_imports'])}",
            f"- Environment variables: {len(summary['all_env_vars'])}",
            f"- Network calls: {len(summary['all_network_calls'])}",
            f"- File operations: {len(summary['all_file_operations'])}",
            f"- Subprocess calls: {len(summary['all_subprocess_calls'])}",
            "",
        ])

        # Dependency tree
        if ca["dependency_graph"]:
            lines.extend(["### Dependency Tree", "```"])
            # Sort by depth for tree display
            by_depth = sorted(
                ca["dependency_graph"].items(),
                key=lambda x: x[1].get("depth", 0),
            )
            for path, info in by_depth:
                depth = info.get("depth", 0)
                indent = "  " * depth
                if info.get("skipped"):
                    lines.append(f"{indent}⏭️  {path} ({info.get('reason', 'skipped')})")
                elif not info.get("exists", False):
                    lines.append(f"{indent}❌ {path} (NOT FOUND)")
                else:
                    lc = info.get("line_count", 0)
                    ftype = info.get("type", "?")
                    lines.append(f"{indent}📄 {path} ({lc} lines, {ftype})")
            lines.extend(["```", ""])

        # Imports
        if summary["all_imports"]:
            lines.extend(["### Imports (all layers)", ""])
            # Categorize: stdlib, third-party, local
            stdlib = []
            third_party = []
            local = []
            for mod in sorted(summary["all_imports"]):
                if mod.startswith(".") or mod.startswith("/"):
                    local.append(mod)
                elif _is_stdlib(mod):
                    stdlib.append(mod)
                else:
                    third_party.append(mod)
            if stdlib:
                lines.append(f"- **stdlib:** {', '.join(stdlib)}")
            if third_party:
                lines.append(f"- **third-party:** {', '.join(third_party)}")
            if local:
                lines.append(f"- **local:** {', '.join(local)}")
            lines.append("")

        # Environment variables
        if summary["all_env_vars"]:
            lines.extend(["### Environment Variables & Secrets", ""])
            for var in sorted(set(summary["all_env_vars"])):
                lines.append(f"- `{var}`")
            lines.append("")

        # Network calls
        if summary["all_network_calls"]:
            lines.extend(["### Network Calls", ""])
            for nc in summary["all_network_calls"]:
                lines.append(f"- `{nc['function']}` → `{nc['url']}` (in {Path(nc['file']).name})")
            lines.append("")

        # File I/O
        if summary["all_file_operations"]:
            lines.extend(["### File I/O", ""])
            for fo in summary["all_file_operations"]:
                mode = fo.get("mode", "")
                lines.append(f"- `{fo['path']}` ({fo['function']}, mode={mode}) (in {Path(fo['file']).name})")
            lines.append("")

        # Missing files (blockers)
        if summary["missing_files"]:
            lines.extend(["### ⚠️ Missing Dependencies", ""])
            for mf in summary["missing_files"]:
                lines.append(f"- ❌ `{mf}`")
            lines.append("")

        # Errors
        if summary["errors"]:
            lines.extend(["### Parse Errors", ""])
            for err in summary["errors"][:10]:
                lines.append(f"- {err}")
            lines.append("")

        # Prompt (for prompt-only crons)
        if not ca["entry_scripts"]:
            lines.extend([
                "### Prompt (no scripts — LLM-directed)",
                "```",
                ca["prompt"][:500],
                "```" if len(ca["prompt"]) <= 500 else "... (truncated)",
                "",
            ])

        lines.extend(["---", ""])

    # Coverage analysis
    lines.extend([
        "## Coverage Analysis — New Modules vs Existing Crons",
        "",
        "| Existing Cron | What It Does (from code analysis) | New Module Coverage | Gaps |",
        "|---|---|---|---|",
    ])

    for ca in cron_analyses:
        name = ca["name"]
        # Summarize what the cron actually does based on code analysis
        does = _summarize_cron_purpose(ca)
        coverage, gaps = _assess_coverage(ca, new_modules)
        lines.append(f"| {name} | {does[:60]} | {coverage} | {gaps} |")
    lines.append("")

    # Gotchas & patterns
    lines.extend([
        "## Gotchas & Patterns to Watch",
        "",
    ])

    all_gotchas = _detect_gotchas(cron_analyses)
    for g in all_gotchas:
        lines.append(f"- {g}")
    if not all_gotchas:
        lines.append("- None detected")
    lines.append("")

    return "\n".join(lines)


def _is_stdlib(module: str) -> bool:
    """Check if a module is Python stdlib."""
    stdlib_modules = {
        "os", "sys", "json", "re", "subprocess", "pathlib", "datetime",
        "argparse", "collections", "glob", "shutil", "time", "hashlib",
        "io", "functools", "itertools", "typing", "abc", "dataclasses",
        "contextlib", "textwrap", "copy", "math", "random", "string",
        "tempfile", "logging", "traceback", "inspect", "ast", "importlib",
        "unittest", "socket", "http", "urllib", "email", "xml", "csv",
        "sqlite3", "threading", "multiprocessing", "signal", "struct",
        "base64", "hmac", "secrets", "uuid", "enum", "statistics",
        "node:fs", "node:path", "node:os", "node:child_process",
        "node:crypto", "node:http", "node:https", "node:url",
    }
    root = module.split(".")[0]
    return root in stdlib_modules


def _summarize_cron_purpose(ca: dict) -> str:
    """Summarize what a cron does based on code analysis."""
    parts = []
    s = ca["summary"]

    if s["all_network_calls"]:
        apis = set(nc.get("url", "")[:30] for nc in s["all_network_calls"])
        parts.append(f"calls {len(apis)} API(s)")

    if s["all_file_operations"]:
        writes = [fo for fo in s["all_file_operations"] if "w" in fo.get("mode", "")]
        reads = [fo for fo in s["all_file_operations"] if "r" in fo.get("mode", "") or not fo.get("mode")]
        if writes:
            parts.append(f"writes {len(writes)} file(s)")
        if reads:
            parts.append(f"reads {len(reads)} file(s)")

    if s["all_subprocess_calls"]:
        parts.append(f"runs {len(s['all_subprocess_calls'])} subprocess(es)")

    if not parts:
        if not ca["entry_scripts"]:
            parts.append("prompt-only (no scripts)")
        else:
            parts.append(f"runs {', '.join(Path(s).name for s in ca['entry_scripts'])}")

    return "; ".join(parts)


def _assess_coverage(ca: dict, new_modules: list) -> tuple:
    """Assess how well new modules cover this cron's functionality."""
    name = ca["name"].lower()
    prompt = ca.get("prompt", "").lower()
    combined = f"{name} {prompt}"

    covered_by = []
    gaps = []

    for mod in new_modules:
        mod_name = mod.get("name", "").lower()
        mod_desc = mod.get("description", "").lower()

        # Check for functional overlap
        if any(kw in combined for kw in [mod_name, mod_name.replace("-", "_"), mod_name.replace("-", " ")]):
            covered_by.append(mod["name"])

    if covered_by:
        return ", ".join(covered_by), "—"
    else:
        # Identify what the cron does that no module covers
        if "self-audit" in combined or "self-reflection" in combined:
            gaps.append("self-audit checks (webhook, subscriptions, state files)")
        if "trello" in combined:
            gaps.append("Trello integration")
        if ca["summary"]["all_network_calls"]:
            gaps.append("External API calls")
        return "None", "; ".join(gaps) if gaps else "Needs review"


def _detect_gotchas(cron_analyses: list) -> list:
    """Detect common migration gotchas."""
    gotchas = []

    all_env_vars = set()
    all_network_urls = set()

    for ca in cron_analyses:
        s = ca["summary"]

        # Shared state files
        for fo in s["all_file_operations"]:
            fpath = fo.get("path", "")
            if "w" in fo.get("mode", "") and fpath:
                # Check if another cron reads this file
                for other in cron_analyses:
                    if other["name"] == ca["name"]:
                        continue
                    for ofo in other["summary"]["all_file_operations"]:
                        if ofo.get("path") == fpath and "r" in ofo.get("mode", ""):
                            gotchas.append(
                                f"⚠️ Shared state: `{ca['name']}` writes `{fpath}` "
                                f"which `{other['name']}` reads"
                            )

        # Missing dependencies
        if s["missing_files"]:
            gotchas.append(
                f"⚠️ `{ca['name']}` has {len(s['missing_files'])} missing file(s): "
                + ", ".join(s["missing_files"][:3])
            )

        # Heavy crons
        if s["total_lines"] > 1000:
            gotchas.append(
                f"ℹ️ `{ca['name']}` has {s['total_lines']:,} total lines across "
                f"{s['total_files']} files — substantial codebase"
            )

        for var in s["all_env_vars"]:
            all_env_vars.add(var)

        for nc in s["all_network_calls"]:
            all_network_urls.add(nc.get("url", "")[:40])

    # Auth dependencies
    secrets = [v for v in all_env_vars if any(
        kw in v.upper() for kw in ["KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "KEYRING"]
    )]
    if secrets:
        gotchas.append(f"🔐 Auth dependencies: {', '.join(sorted(secrets)[:5])}")

    return gotchas


# ── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deep dependency analyzer")
    parser.add_argument("--depth", type=int, default=10, help="Max recursion depth")
    parser.add_argument("--cron", help="Analyze specific cron by name")
    parser.add_argument("--script", help="Analyze a specific script path")
    parser.add_argument("--all", action="store_true", help="Analyze all crons")
    args = parser.parse_args()

    ANALYSES_DIR.mkdir(parents=True, exist_ok=True)

    # Load new module info for coverage analysis
    new_modules = []
    if MODULES_DIR.exists():
        module_descs = {}
        try:
            import yaml
            with open(SKILL_DIR / "modules.yaml") as f:
                module_descs = yaml.safe_load(f).get("modules", {})
        except Exception:
            pass

        for f in sorted(MODULES_DIR.glob("*.py")):
            new_modules.append({
                "name": f.stem,
                "description": module_descs.get(f.stem, {}).get("description", ""),
                "tier": module_descs.get(f.stem, {}).get("tier", "?"),
            })

    if args.script:
        # Single script analysis
        print(f"🔍 Analyzing script: {args.script} (depth={args.depth})")
        graph = trace_dependencies(args.script, args.depth)
        output = json.dumps(graph, indent=2, default=str)
        out_path = ANALYSES_DIR / f"script-analysis-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        out_path.write_text(output)
        print(output[:3000])
        print(f"\n📄 Full output: {out_path}")
        return

    # Cron analysis
    jobs = get_cron_jobs()
    if not jobs:
        print("⚠️  No cron jobs found. Use --script to analyze a script directly.")
        return

    if args.cron:
        jobs = [j for j in jobs if j.get("name") == args.cron]
        if not jobs:
            print(f"❌ Cron '{args.cron}' not found")
            sys.exit(1)

    print(f"🔍 Deep analyzing {len(jobs)} cron job(s) (depth={args.depth})...")

    cron_analyses = []
    for job in jobs:
        name = job.get("name", "?")
        print(f"  📋 {name}...")
        ca = analyze_cron_deep(job, args.depth)
        ca["_max_depth"] = args.depth
        cron_analyses.append(ca)
        s = ca["summary"]
        print(f"     {s['total_files']} files, {s['total_lines']:,} lines, "
              f"depth {s['max_depth_reached']}, "
              f"{len(s['missing_files'])} missing")

    # Generate report
    doc = format_deep_analysis(cron_analyses, new_modules)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    doc_path = ANALYSES_DIR / f"deep-analysis-{ts}.md"
    doc_path.write_text(doc)

    json_path = ANALYSES_DIR / f"deep-analysis-{ts}.json"
    json_path.write_text(json.dumps(cron_analyses, indent=2, default=str))

    print(f"\n📄 Analysis document: {doc_path}")
    print(f"📊 Raw data: {json_path}")


if __name__ == "__main__":
    main()
