"""Dependency discovery and lightweight code health checks."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 1024 * 1024


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def analyze(scan: dict[str, Any]) -> dict[str, Any]:
    root = Path(scan["root"])
    findings: list[dict[str, Any]] = []
    hashes: dict[str, list[str]] = {}
    todo_count = 0
    filemap = {f["path"]: f for f in scan["files"]}
    module_paths = {}
    for f in scan["files"]:
        if f["language"] == "Python" and f["path"].endswith(".py"):
            rel = Path(f["path"])
            mod = ".".join(rel.with_suffix("").parts)
            if mod.endswith(".__init__"):
                mod = mod[:-9]
            module_paths[mod] = f["path"]
    modules = set(module_paths)
    imports = []
    for f in scan["files"]:
        path = root / Path(f["path"])
        if f["size_bytes"] == 0:
            findings.append({"type": "Empty file", "path": f["path"], "line": None, "message": "This source file is empty."})
        if f["size_bytes"] > 250_000:
            findings.append({"type": "Large file", "path": f["path"], "line": None, "message": f"File is {f['size_bytes']:,} bytes; consider splitting it."})
        content = _read(path)
        for line_no, line in enumerate(content.splitlines(), 1):
            for marker in ("TODO", "FIXME"):
                match = re.search(rf"\b{marker}\b", line, re.IGNORECASE)
                if match:
                    todo_count += 1
                    # Do not echo source text into a public dashboard; a TODO line
                    # can contain an accidental credential or other sensitive value.
                    findings.append({"type": marker, "path": f["path"], "line": line_no, "message": f"{marker} marker found."})
        if f["language"] == "Python" and f["path"].endswith(".py"):
            try:
                tree = ast.parse(content, filename=f["path"])
                for node in ast.walk(tree):
                    names = []
                    if isinstance(node, ast.Import):
                        names = [n.name for n in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        names = [node.module]
                    for name in names:
                        target = name
                        while target and target not in modules:
                            target = target.rpartition(".")[0]
                        if target:
                            imports.append({"source": f["path"], "target": module_paths[target], "module": name})
            except SyntaxError as exc:
                findings.append({"type": "Python syntax error", "path": f["path"], "line": exc.lineno, "message": (exc.msg or "Syntax error")[:180]})
        try:
            if f["size_bytes"] <= MAX_FILE_BYTES:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                hashes.setdefault(digest, []).append(f["path"])
        except OSError:
            pass
    for paths in hashes.values():
        if len(paths) > 1:
            for duplicate in paths[1:]:
                findings.append({"type": "Duplicate file", "path": duplicate, "line": None, "message": "Identical content also appears in: " + ", ".join(paths[:1])})
    dependencies = []
    seen = set()
    for f in scan["files"]:
        basename = Path(f["path"]).name.lower()
        path = root / Path(f["path"])
        try:
            if basename == "requirements.txt":
                for line in _read(path).splitlines():
                    line = line.split("#", 1)[0].strip()
                    if not line or line.startswith(("-", ".", "http:" , "https:")):
                        continue
                    m = re.match(r"([A-Za-z0-9_.-]+)\s*(?:\[[^]]+\])?\s*(===|==|~=|!=|<=|>=|<|>)?\s*([^;\s]+)?", line)
                    if m: dependencies.append((m.group(1), (m.group(2) or "") + (m.group(3) or ""), "Python"))
            elif basename == "pyproject.toml":
                obj = tomllib.loads(_read(path))
                groups = [obj.get("project", {}).get("dependencies", [])]
                groups += list(obj.get("project", {}).get("optional-dependencies", {}).values())
                groups += [obj.get("tool", {}).get("poetry", {}).get("dependencies", {})]
                for group in groups:
                    if isinstance(group, dict):
                        for name, version in group.items():
                            if name.lower() != "python": dependencies.append((name, str(version), "Python"))
                    else:
                        for item in group:
                            m = re.match(r"([A-Za-z0-9_.-]+)\s*(.*)", item)
                            if m: dependencies.append((m.group(1), m.group(2).strip(), "Python"))
            elif basename == "pipfile":
                obj = tomllib.loads(_read(path))
                for group in (obj.get("packages", {}), obj.get("dev-packages", {})):
                    dependencies.extend((n, str(v), "Python") for n, v in group.items())
            elif basename == "package.json":
                obj = json.loads(_read(path))
                for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
                    dependencies.extend((n, str(v), "Node.js") for n, v in obj.get(section, {}).items())
        except (OSError, ValueError, TypeError, tomllib.TOMLDecodeError, json.JSONDecodeError):
            continue
    unique_deps = []
    for name, version, ecosystem in dependencies:
        key = (name.lower(), ecosystem)
        if key not in seen:
            seen.add(key)
            unique_deps.append({"name": name, "version": version, "ecosystem": ecosystem})
    return {"findings": findings, "todo_count": todo_count, "dependencies": unique_deps, "imports": sorted(imports, key=lambda x: (x["source"], x["target"]))}
