"""Export scan and analysis results to portable formats."""
import csv
import io
import json
from datetime import datetime, timezone


def report(scan, analysis):
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "repository": {"name": scan["name"], "path": scan["root"]}, "metrics": {"files": scan["file_count"], "code_lines": scan["totals"]["code"], "comments": scan["totals"]["comments"], "blank_lines": scan["totals"]["blank"], "size_bytes": scan["totals"]["size"], "dependencies": len(analysis["dependencies"]), "todos_and_fixmes": analysis["todo_count"]}, "files": scan["files"], "dependencies": analysis["dependencies"], "findings": analysis["findings"], "python_imports": analysis["imports"]}


def json_export(scan, analysis):
    return json.dumps(report(scan, analysis), indent=2, ensure_ascii=False)


def csv_export(scan):
    out = io.StringIO(newline="")
    fields = ["path", "directory", "language", "extension", "size_bytes", "lines", "code_lines", "comment_lines", "blank_lines", "depth", "empty"]
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(scan["files"])
    return out.getvalue()


def markdown_export(scan, analysis):
    t = scan["totals"]
    rows = [f"# CODEBASE X-RAY: {scan['name']}", "", f"Scanned path: `{scan['root']}`", "", "## Overview", "", f"- Files: {scan['file_count']:,}", f"- Code lines: {t['code']:,}", f"- Repository size: {t['size']:,} bytes", f"- Dependencies: {len(analysis['dependencies']):,}", f"- TODO/FIXME markers: {analysis['todo_count']:,}", f"- Findings: {len(analysis['findings']):,}", "", "## Languages", ""]
    counts = {}
    for f in scan["files"]: counts[f["language"]] = counts.get(f["language"], 0) + 1
    rows += [f"- {lang}: {n} files" for lang, n in sorted(counts.items(), key=lambda x: -x[1])] or ["- No files found"]
    rows += ["", "## Dependencies", ""]
    rows += [f"- {d['name']} {d['version']} ({d['ecosystem']})" for d in analysis["dependencies"]] or ["- None detected"]
    rows += ["", "## Findings", ""]
    rows += [f"- **{x['type']}** — `{x['path']}`" + (f":{x['line']}" if x["line"] else "") + f" — {x['message']}" for x in analysis["findings"]] or ["- No findings detected"]
    rows += ["", "> These lightweight checks are informational and are not a comprehensive security audit.", ""]
    return "\n".join(rows)
