"""Read-only repository inventory and source statistics."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".next", ".env"}
MAX_FILE_BYTES = 1024 * 1024
LANGUAGES = {
    ".py": "Python", ".pyi": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".java": "Java", ".go": "Go", ".rs": "Rust",
    ".c": "C", ".h": "C/C++", ".cpp": "C++", ".hpp": "C++", ".cs": "C#", ".php": "PHP",
    ".rb": "Ruby", ".swift": "Swift", ".kt": "Kotlin", ".scala": "Scala", ".sh": "Shell",
    ".bash": "Shell", ".sql": "SQL", ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".vue": "Vue", ".svelte": "Svelte", ".xml": "XML", ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML", ".json": "JSON", ".md": "Markdown", ".rst": "reStructuredText",
    ".r": "R", ".R": "R", ".dart": "Dart", ".lua": "Lua", ".pl": "Perl", ".ex": "Elixir",
    ".exs": "Elixir", ".hs": "Haskell", ".proto": "Protocol Buffers", ". Dockerfile": "Dockerfile",
}
COMMENT_PREFIXES = {"Python": ("#",), "Ruby": ("#",), "Shell": ("#",), "YAML": ("#",), "TOML": ("#",), "R": ("#",), "SQL": ("--",), "Lua": ("--",), "HTML": ("<!--",), "XML": ("<!--",), "CSS": ("/*",), "SCSS": ("//", "/*"), "JavaScript": ("//", "/*"), "TypeScript": ("//", "/*"), "Go": ("//", "/*"), "Rust": ("//", "/*"), "Java": ("//", "/*"), "C": ("//", "/*"), "C++": ("//", "/*"), "C/C++": ("//", "/*"), "C#": ("//", "/*"), "PHP": ("//", "#", "/*"), "Kotlin": ("//", "/*"), "Swift": ("//", "/*")}


def validate_root(root: str | Path) -> Path:
    path = Path(root).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")
    return path


def scan_repository(root: str | Path) -> dict[str, Any]:
    """Walk a repository without executing or modifying its contents."""
    base = validate_root(root)
    records: list[dict[str, Any]] = []
    totals = {"code": 0, "comments": 0, "blank": 0, "size": 0}
    for current, dirs, names in os.walk(base, topdown=True, onerror=lambda _e: None):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".env"))
        for name in sorted(names):
            if name == ".env" or name.startswith(".env."):
                continue
            path = Path(current) / name
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                size = path.stat().st_size
                if size > MAX_FILE_BYTES:
                    continue
                with path.open("rb") as stream:
                    sample = stream.read(8192)
                    if b"\0" in sample:
                        continue
                    data = sample + stream.read()
                text = data.decode("utf-8-sig", errors="replace")
            except (OSError, PermissionError):
                continue
            rel = path.relative_to(base).as_posix()
            ext = path.suffix
            language = LANGUAGES.get(ext, "Other")
            lines = text.splitlines()
            prefixes = COMMENT_PREFIXES.get(language, ())
            blank = sum(1 for line in lines if not line.strip())
            comments = sum(1 for line in lines if line.strip().startswith(prefixes)) if prefixes else 0
            code = len(lines) - blank - comments
            records.append({"path": rel, "name": name, "directory": "/".join(Path(rel).parts[:-1]) or ".", "extension": ext, "language": language, "size_bytes": size, "lines": len(lines), "code_lines": code, "comment_lines": comments, "blank_lines": blank, "depth": len(Path(rel).parts) - 1, "empty": size == 0})
            totals["code"] += code
            totals["comments"] += comments
            totals["blank"] += blank
            totals["size"] += size
    records.sort(key=lambda f: f["path"].lower())
    return {"root": str(base), "name": base.name or str(base), "files": records, "totals": totals, "file_count": len(records)}


def directory_summary(scan: dict[str, Any]) -> list[dict[str, Any]]:
    dirs: dict[str, dict[str, Any]] = {".": {"directory": ".", "files": 0, "size_bytes": 0, "depth": 0}}
    for file in scan["files"]:
        parts = Path(file["path"]).parts[:-1]
        for i in range(len(parts) + 1):
            key = "/".join(parts[:i]) or "."
            dirs.setdefault(key, {"directory": key, "files": 0, "size_bytes": 0, "depth": i})
        entry = dirs["/".join(parts) or "."]
        entry["files"] += 1
        entry["size_bytes"] += file["size_bytes"]
    return sorted(dirs.values(), key=lambda d: d["directory"].lower())
