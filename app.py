"""CODEBASE X-RAY — repository analysis dashboard."""
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from analyzer import analyze
from exporters import csv_export, json_export, markdown_export
from github_scanner import scan_public_github
from scanner import directory_summary, scan_repository
from visualizations import (
    composition_chart,
    directory_chart,
    import_graph,
    language_chart,
    largest_chart,
)


st.set_page_config(
    page_title="CODEBASE X-RAY",
    page_icon="⌕",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');
:root {
  --canvas: #0D1117; --surface: #161B22; --surface-raised: #1C2129;
  --border: #30363D; --text: #E6EDF3; --muted: #8B949E;
  --blue: #2F81F7; --green: #3FB950; --amber: #D29922; --red: #F85149;
  --mono: 'IBM Plex Mono', 'Cascadia Code', Consolas, monospace;
  --sans: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
html, body, [class*="css"], [data-testid="stAppViewContainer"] {
  font-family: var(--sans); color: var(--text);
}
.stApp { background: var(--canvas); }
[data-testid="stAppViewContainer"] > .main .block-container {
  max-width: 1580px; padding: 1.05rem 2rem 2.5rem;
}
[data-testid="stHeader"] { background: var(--canvas); }
[data-testid="stSidebar"] {
  background: var(--canvas); border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.05rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--muted); }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: var(--muted); }
[data-testid="stSidebar"] hr, hr { border-color: var(--border) !important; }
#MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; }
.brand { display:flex; align-items:center; padding:2px 2px 4px; }
.brand-name { color:var(--text); font-size:13px; font-weight:700; letter-spacing:.025em; }
.brand-caption { color:var(--muted); font:10px var(--mono); letter-spacing:.06em; margin-top:2px; }
.side-label { color:var(--muted); font:500 10px var(--mono); letter-spacing:.09em; text-transform:uppercase; margin:4px 0 6px; }
.repo-kicker { color:var(--muted); font:500 10px var(--mono); letter-spacing:.08em; text-transform:uppercase; margin-bottom:5px; }
.repo-title { color:var(--text); font-size:22px; line-height:1.2; font-weight:600; letter-spacing:-.025em; margin:0; }
.repo-path { color:var(--muted); font:12px var(--mono); overflow-wrap:anywhere; margin-top:5px; }
.scan-meta { color:var(--muted); font:11px var(--mono); margin-top:11px; }
.status { color:#7ee787; font:500 11px var(--mono); white-space:nowrap; }
.section-heading { color:var(--text); font-size:14px; font-weight:600; margin:2px 0 3px; }
.section-subtitle { color:var(--muted); font-size:11px; margin:0 0 10px; }
.mono { font-family:var(--mono); }
.file-path { font-family:var(--mono); font-size:12px; color:#c9d1d9; }
.panel-note { color:var(--muted); font:10px var(--mono); }
[data-testid="stMetric"] {
  min-height:84px; background:var(--surface); border:1px solid var(--border);
  border-radius:5px; padding:11px 13px;
}
[data-testid="stMetricLabel"] { color:var(--muted) !important; font-size:11px !important; }
[data-testid="stMetricValue"] { color:var(--text) !important; font:500 21px var(--mono) !important; }
[data-testid="stMetricDelta"] { font-size:10px !important; }
[data-testid="stPlotlyChart"] { border-radius:4px; }
[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:5px; overflow:hidden; }
div[data-testid="stVerticalBlock"] div[data-testid="stAlert"] { border-radius:5px; }
div.stButton > button, div.stDownloadButton > button {
  min-height:34px; border-radius:5px; border:1px solid var(--border);
  background:var(--surface); color:var(--text); font-weight:500;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
  border-color:#6e7681; color:#fff; background:var(--surface-raised);
}
div.stButton > button[kind="primary"] {
  background:#1f6feb; border-color:#1f6feb; color:#fff;
}
div.stButton > button[kind="primary"]:hover { background:#388bfd; border-color:#388bfd; }
[data-testid="stTextInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  background:var(--canvas); border-color:var(--border); border-radius:5px;
}
[data-testid="stRadio"] label p { font-size:12px; }
code { color:#79c0ff !important; background:#161b22 !important; font-family:var(--mono) !important; }
@media (max-width: 850px) {
  [data-testid="stAppViewContainer"] > .main .block-container { padding: .8rem 1rem 2rem; }
  .repo-title { font-size:19px; }
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def cached_scan(path: str):
    return scan_repository(path)


@st.cache_data(show_spinner=False, ttl=1800)
def cached_github_scan(url: str):
    return scan_public_github(url)


def fmt_bytes(value):
    units = ("B", "KB", "MB", "GB")
    number = float(value)
    for unit in units:
        if number < 1024 or unit == units[-1]:
            return f"{number:,.1f} {unit}" if unit != "B" else f"{int(number)} B"
        number /= 1024


def table(rows, *, height=410, column_config=None):
    """Render compact tables with code-oriented fields in a monospace face."""
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.info("No matching rows.")
        return
    mono_columns = [
        c for c in (
            "File name", "File", "Name", "Directory", "Package", "Version",
            "Language", "Lines", "Module", "Source", "Target", "Line",
        ) if c in frame
    ]
    styler = frame.style
    if mono_columns:
        styler = styler.set_properties(
            subset=mono_columns,
            **{"font-family": "IBM Plex Mono, Consolas, monospace", "font-size": "11px"},
        )
    if "Severity" in frame:
        severity_colors = {"Error": "#F85149", "Review": "#D29922", "Info": "#8B949E"}
        color_cells = lambda value: f"color: {severity_colors.get(value, '#8B949E')}; font-weight: 600"
        if hasattr(styler, "map"):
            styler = styler.map(color_cells, subset=["Severity"])
        else:
            styler = styler.applymap(color_cells, subset=["Severity"])
    st.dataframe(
        styler,
        hide_index=True,
        width="stretch",
        height=height,
        column_config=column_config or {},
    )


with st.sidebar:
    st.markdown(
        "<div class='brand'><div><div class='brand-name'>CODEBASE X-RAY</div><div class='brand-caption'>REPOSITORY ANALYSIS</div></div></div>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("<div class='side-label'>Repository</div>", unsafe_allow_html=True)
    source_mode = st.radio(
        "Repository source",
        ["Public GitHub", "Local folder"],
        index=0,
        label_visibility="collapsed",
    )
    if source_mode == "Public GitHub":
        source_value = st.text_input(
            "GitHub repository URL",
            placeholder="https://github.com/owner/repository",
            label_visibility="collapsed",
            key="github_url",
        )
        st.caption("Public repositories only. Source is scanned temporarily.")
    else:
        source_value = st.text_input(
            "Repository path",
            value=st.session_state.get("repo_path", str(Path.cwd())),
            placeholder="C:/path/to/project",
            label_visibility="collapsed",
            key="local_path",
        )
    st.divider()
    st.markdown("<div class='side-label'>Workspace</div>", unsafe_allow_html=True)
    section = st.radio(
        "Workspace navigation",
        ["Overview", "Architecture", "Files", "Dependencies", "Issues"],
        label_visibility="collapsed",
    )


if source_mode == "Public GitHub" and not source_value.strip():
    st.markdown(
        "<div class='repo-kicker'>Repository analysis</div><h1 class='repo-title'>CODEBASE X-RAY</h1>",
        unsafe_allow_html=True,
    )
    st.markdown("### Scan a public repository")
    st.write("Enter a GitHub repository URL in the sidebar to inspect its structure, dependencies, and code health.")
    st.code("https://github.com/owner/repository", language=None)
    st.stop()

try:
    if source_mode == "Public GitHub":
        with st.spinner("Downloading and analyzing repository…"):
            scan, analysis = cached_github_scan(source_value)
    else:
        with st.spinner("Reading repository files…"):
            scan = cached_scan(source_value)
        analysis = analyze(scan)
except (ValueError, OSError) as exc:
    st.error(str(exc))
    st.info("Check the repository URL or local path in the sidebar, then try again.")
    st.stop()

identity = f"{source_mode}:{source_value.strip()}"
rescan_was_requested = st.session_state.pop("rescan_requested", False)
if st.session_state.get("last_scan_identity") != identity or rescan_was_requested:
    st.session_state["last_scan_identity"] = identity
    st.session_state["last_scan_timestamp"] = datetime.now().astimezone()
last_scan = st.session_state.get("last_scan_timestamp", datetime.now().astimezone())

with st.sidebar:
    st.divider()
    st.markdown("<div class='side-label'>Export</div>", unsafe_allow_html=True)
    st.download_button(
        "Download JSON report",
        json_export(scan, analysis),
        file_name=f"{scan['name']}-xray.json",
        mime="application/json",
        width="stretch",
    )
    st.download_button(
        "Download file CSV",
        csv_export(scan),
        file_name=f"{scan['name']}-files.csv",
        mime="text/csv",
        width="stretch",
    )
    st.download_button(
        "Download Markdown summary",
        markdown_export(scan, analysis),
        file_name=f"{scan['name']}-summary.md",
        mime="text/markdown",
        width="stretch",
    )
    st.caption("Read-only analysis · repository code is never executed")

with st.container():
    head, action = st.columns([8, 1.15])
    with head:
        st.markdown(
            f"<div class='repo-kicker'>{escape(section)} / Repository</div>"
            f"<div class='repo-title'>{escape(scan['name'])}</div>"
            f"<div class='repo-path'>{escape(scan['root'])}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='scan-meta'>Last scan · {last_scan.strftime('%Y-%m-%d %H:%M %Z')} &nbsp;&nbsp; "
            f"·&nbsp;&nbsp; {scan['file_count']:,} files inspected</div>",
            unsafe_allow_html=True,
        )
    with action:
        st.markdown("<div class='status'>SCAN COMPLETE</div>", unsafe_allow_html=True)
        if st.button("Rescan", width="stretch", key="header_rescan"):
            st.session_state["rescan_requested"] = True
            cached_scan.clear()
            cached_github_scan.clear()
            st.rerun()
st.divider()

files, totals = scan["files"], scan["totals"]
dirs = directory_summary(scan)

if section == "Overview":
    metrics = st.columns(6, gap="small")
    values = [
        ("Files", f"{scan['file_count']:,}"),
        ("Lines of code", f"{totals['code']:,}"),
        ("Repository size", fmt_bytes(totals["size"])),
        ("Languages", str(len({f['language'] for f in files if f['language'] != 'Other'}))),
        ("Dependencies", f"{len(analysis['dependencies']):,}"),
        ("Issues found", f"{len(analysis['findings']):,}"),
    ]
    for col, (label, value) in zip(metrics, values):
        col.metric(label, value)

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("<div class='section-heading'>Language distribution</div><div class='section-subtitle'>Files by detected language</div>", unsafe_allow_html=True)
        st.plotly_chart(language_chart(files), width="stretch", config={"displayModeBar": False})
    with right:
        st.markdown("<div class='section-heading'>Code composition</div><div class='section-subtitle'>Estimated lines across the repository</div>", unsafe_allow_html=True)
        st.plotly_chart(composition_chart(totals), width="stretch", config={"displayModeBar": False})

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("<div class='section-heading'>Largest files</div><div class='section-subtitle'>Top ten by file size</div>", unsafe_allow_html=True)
        st.plotly_chart(largest_chart(files), width="stretch", config={"displayModeBar": False})
    with right:
        st.markdown("<div class='section-heading'>Directory breakdown</div><div class='section-subtitle'>Files in the busiest folders</div>", unsafe_allow_html=True)
        st.plotly_chart(directory_chart(files), width="stretch", config={"displayModeBar": False})

    st.markdown("<div class='section-heading'>Recent findings</div><div class='section-subtitle'>First eight findings from the current scan</div>", unsafe_allow_html=True)
    recent = analysis["findings"][:8]
    if recent:
        table(
            [{"Type": f["type"], "File": f["path"], "Line": f["line"] or "—", "Explanation": f["message"]} for f in recent],
            height=300,
        )
    else:
        st.success("No findings from the configured checks.")

elif section == "Files":
    st.markdown("<div class='section-heading'>File explorer</div><div class='section-subtitle'>Search, filter, and sort the scanned file inventory</div>", unsafe_allow_html=True)
    controls = st.columns([2.2, 1.2, 1.8], gap="small")
    with controls[0]:
        query = st.text_input("Search", placeholder="Search name or path", key="file_search")
    with controls[1]:
        languages = ["All languages"] + sorted({f["language"] for f in files})
        selected_language = st.selectbox("Language", languages, label_visibility="visible")
    with controls[2]:
        folders = ["All directories"] + sorted({f["directory"] for f in files})
        selected_folder = st.selectbox("Directory", folders, label_visibility="visible")
    filtered = [
        f for f in files
        if (not query or query.lower() in f["path"].lower())
        and (selected_language == "All languages" or f["language"] == selected_language)
        and (selected_folder == "All directories" or f["directory"] == selected_folder)
    ]
    st.caption(f"{len(filtered):,} of {len(files):,} files · files over 1 MB and binary files are excluded")
    rows = [{
        "File name": f["name"], "Language": f["language"], "Lines": f["lines"],
        "Size": fmt_bytes(f["size_bytes"]), "Directory": f["directory"],
    } for f in filtered]
    table(rows, height=610, column_config={
        "File name": st.column_config.TextColumn("File name", help="File in the scanned repository"),
        "Language": st.column_config.TextColumn("Language"),
        "Lines": st.column_config.NumberColumn("Lines", format="%d"),
        "Size": st.column_config.TextColumn("Size"),
        "Directory": st.column_config.TextColumn("Directory"),
    })

elif section == "Architecture":
    st.markdown("<div class='section-heading'>Architecture explorer</div><div class='section-subtitle'>Browse directories and inspect internal Python imports</div>", unsafe_allow_html=True)
    folder_names = [d["directory"] for d in dirs]
    controls = st.columns([2, 1], gap="small")
    with controls[0]:
        selected_dir = st.selectbox("Current directory", folder_names, index=0)
    selected_meta = next((d for d in dirs if d["directory"] == selected_dir), dirs[0])
    st.caption(f"{selected_meta['files']:,} files · depth {selected_meta['depth']} · {fmt_bytes(selected_meta['size_bytes'])}")
    direct_dirs = [
        d for d in dirs
        if d["directory"] != selected_dir
        and (d["directory"].rpartition("/")[0] or ".") == selected_dir
    ]
    direct_files = [f for f in files if f["directory"] == selected_dir]
    tree_rows = []
    for d in direct_dirs:
        tree_rows.append({"Kind": "DIR", "Name": "▸ " + Path(d["directory"]).name, "Directory": d["directory"], "Files": d["files"], "Lines": "—", "Size": fmt_bytes(d["size_bytes"])})
    for f in direct_files:
        tree_rows.append({"Kind": "FILE", "Name": f["name"], "Directory": f["directory"], "Files": "—", "Lines": f["lines"], "Size": fmt_bytes(f["size_bytes"])})
    tree_rows.sort(key=lambda row: (row["Kind"] != "DIR", row["Name"].lower()))
    table(tree_rows, height=330)

    busiest = sorted(dirs, key=lambda d: d["files"], reverse=True)[:8]
    st.markdown("<div class='section-heading'>Directory metrics</div>", unsafe_allow_html=True)
    table([{"Directory": d["directory"], "Files": d["files"], "Depth": d["depth"], "Size": fmt_bytes(d["size_bytes"])} for d in busiest], height=300)

    st.markdown("<div class='section-heading'>Internal Python imports</div><div class='section-subtitle'>Directed module relationships detected from import statements</div>", unsafe_allow_html=True)
    if analysis["imports"]:
        st.plotly_chart(import_graph(analysis["imports"]), width="stretch", config={"displayModeBar": False})
        with st.expander("View import relationships as a table"):
            table(analysis["imports"], height=320)
    else:
        st.info("No internal Python module imports were detected.")

elif section == "Dependencies":
    st.markdown("<div class='section-heading'>Declared dependencies</div><div class='section-subtitle'>Parsed from project manifests; packages are not installed</div>", unsafe_allow_html=True)
    deps = analysis["dependencies"]
    ecos = Counter(d["ecosystem"] for d in deps)
    a, b = st.columns([1, 2], gap="medium")
    with a:
        st.metric("Declared packages", f"{len(deps):,}")
        st.markdown("<div class='section-heading'>Ecosystems</div>", unsafe_allow_html=True)
        table([{"Ecosystem": name, "Packages": count} for name, count in ecos.most_common()], height=210)
    with b:
        table(
            [{"Package": d["name"], "Version": d["version"] or "Not pinned", "Ecosystem": d["ecosystem"]} for d in deps],
            height=470,
            column_config={
                "Package": st.column_config.TextColumn("Package"),
                "Version": st.column_config.TextColumn("Declared version"),
                "Ecosystem": st.column_config.TextColumn("Ecosystem"),
            },
        )
    if not deps:
        st.info("No dependencies found in requirements.txt, pyproject.toml, Pipfile, or package.json.")

elif section == "Issues":
    st.markdown("<div class='section-heading'>Code inspection</div><div class='section-subtitle'>Informational checks only; not a comprehensive security audit</div>", unsafe_allow_html=True)
    findings = analysis["findings"]
    by_type = Counter(f["type"] for f in findings)
    c1, c2, c3 = st.columns(3, gap="small")
    c1.metric("Findings", f"{len(findings):,}")
    c2.metric("TODO / FIXME", f"{analysis['todo_count']:,}")
    c3.metric("Python syntax errors", f"{by_type.get('Python syntax error', 0):,}")
    if findings:
        types = sorted(by_type)
        selected_types = st.multiselect("Finding types", types, default=types)
        filtered = [f for f in findings if f["type"] in selected_types]
        severity = {
            "Python syntax error": "Error",
            "Large file": "Review",
            "Empty file": "Review",
            "Duplicate file": "Review",
            "TODO": "Info",
            "FIXME": "Info",
        }
        table([
            {
                "Severity": severity.get(f["type"], "Info"),
                "Finding type": f["type"],
                "File": f["path"],
                "Line": f["line"] if f["line"] is not None else "—",
                "Explanation": f["message"],
            }
            for f in filtered
        ], height=560)
    else:
        st.success("No findings from the configured checks.")

st.markdown(
    "<hr><div class='panel-note'>CODEBASE X-RAY &nbsp;·&nbsp; READ-ONLY SCAN &nbsp;·&nbsp; NO REPOSITORY CODE EXECUTED</div>",
    unsafe_allow_html=True,
)
