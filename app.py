"""CODEBASE X-RAY — local repository analytics dashboard."""
from pathlib import Path
from html import escape
import sys

import streamlit as st

from analyzer import analyze
from exporters import csv_export, json_export, markdown_export
from github_scanner import scan_public_github
from scanner import directory_summary, scan_repository
from visualizations import composition_chart, directory_chart, language_chart, largest_chart

st.set_page_config(page_title="CODEBASE X-RAY", page_icon="⌕", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
.stApp { background: #0b0d12; color: #e5e7eb; font-family: 'Manrope', sans-serif; }
[data-testid="stSidebar"] { background: #10131b; border-right: 1px solid #222735; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#aab2c2; }
.hero { padding: 12px 0 18px; }
.eyebrow { color:#8b9bb7; font: 600 11px 'DM Mono',monospace; letter-spacing: .16em; text-transform:uppercase; }
.hero h1 { font: 800 clamp(26px,3vw,38px) 'Manrope',sans-serif; letter-spacing:-.045em; margin:7px 0 4px; color:#f8fafc; }
.hero p { color:#8994a8; margin:0; }
[data-testid="stMetric"] { background:linear-gradient(145deg,#141925,#11141c); border:1px solid #252c3a; padding:17px 18px; border-radius:13px; box-shadow:0 8px 22px #0002; }
[data-testid="stMetricLabel"] { color:#8e9ab0 !important; font-size:12px !important; }
[data-testid="stMetricValue"] { color:#f1f5f9 !important; font-weight:700; }
[data-testid="stVerticalBlock"] > div:has(> [data-testid="stPlotlyChart"]) { background:#11151e; border:1px solid #242b39; border-radius:14px; padding:10px 12px; }
.section-title { color:#e8edf6; font-size:17px; font-weight:700; margin:4px 0 12px; }
div.stButton > button, div.stDownloadButton > button { border-radius:9px; border:1px solid #30394b; background:#171d29; color:#dce5f5; font-weight:600; }
div.stButton > button[kind="primary"] { background:#5865d9; border-color:#6974eb; color:white; }
code { color:#a5b4fc !important; }
hr { border-color:#242a36 !important; }
</style>
""", unsafe_allow_html=True)


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


with st.sidebar:
    st.markdown("<div style='font:800 18px Manrope;color:#f8fafc;letter-spacing:-.04em'>⌕ &nbsp;CODEBASE<br><span style='color:#8c9aff'>X-RAY</span></div>", unsafe_allow_html=True)
    st.caption("LOCAL REPOSITORY INTELLIGENCE")
    st.divider()
    source_mode = st.radio("Scan source", ["Public GitHub repository", "Local folder"], index=0)
    if source_mode == "Public GitHub repository":
        source_value = st.text_input("GitHub repository URL", placeholder="https://github.com/owner/repository")
        st.caption("Public repositories only · source code is scanned temporarily on this server.")
    else:
        source_value = st.text_input("Repository path", value=st.session_state.get("repo_path", str(Path.cwd())), placeholder="C:/path/to/project")
    if st.button("↻  Scan repository", type="primary", use_container_width=True):
        if source_mode == "Local folder":
            st.session_state.repo_path = source_value
        cached_scan.clear()
        cached_github_scan.clear()
    st.markdown("<div style='height:12px'></div><div class='eyebrow'>WORKSPACE</div>", unsafe_allow_html=True)
    section = st.radio("Explore", ["Overview", "Architecture", "Files", "Dependencies", "Issues"], label_visibility="collapsed")
    st.divider()
    st.markdown("<div class='eyebrow'>EXPORT REPORT</div>", unsafe_allow_html=True)

try:
    if source_mode == "Public GitHub repository":
        if not source_value.strip():
            st.markdown("<div class='hero'><div class='eyebrow'>PUBLIC REPOSITORY SCANNER</div><h1>CODEBASE X-RAY</h1><p>Paste a public GitHub repository URL in the sidebar to explore its structure and code metrics.</p></div>", unsafe_allow_html=True)
            st.info("Example: https://github.com/streamlit/streamlit")
            st.stop()
        with st.spinner("Downloading and analyzing the public GitHub repository…"):
            scan, analysis = cached_github_scan(source_value)
    else:
        with st.spinner("Reading repository files…"):
            scan = cached_scan(source_value)
        analysis = analyze(scan)
except (ValueError, OSError) as exc:
    st.markdown("<div class='hero'><div class='eyebrow'>LOCAL CODE INTELLIGENCE</div><h1>CODEBASE X-RAY</h1><p>Understand the shape of your software at a glance.</p></div>", unsafe_allow_html=True)
    st.error(str(exc))
    st.info("Enter a valid local directory in the sidebar, then select **Scan repository**.")
    st.stop()

with st.sidebar:
    st.download_button("JSON analysis", json_export(scan, analysis), file_name=f"{scan['name']}-xray.json", mime="application/json", use_container_width=True)
    st.download_button("File statistics CSV", csv_export(scan), file_name=f"{scan['name']}-files.csv", mime="text/csv", use_container_width=True)
    st.download_button("Markdown summary", markdown_export(scan, analysis), file_name=f"{scan['name']}-summary.md", mime="text/markdown", use_container_width=True)
    st.caption("Read-only scan · no code execution")

st.markdown(f"<div class='hero'><div class='eyebrow'>LOCAL CODE INTELLIGENCE &nbsp; / &nbsp; {escape(section.upper())}</div><h1>{escape(scan['name'])}</h1><p>Repository overview · <code>{escape(scan['root'])}</code></p></div>", unsafe_allow_html=True)
st.caption(f"SCAN COMPLETE  ·  {scan['file_count']:,} files inspected  ·  Excludes generated and environment folders")
files, totals = scan["files"], scan["totals"]
dirs = directory_summary(scan)

if section == "Overview":
    metrics = st.columns(6)
    values = [("Files", f"{scan['file_count']:,}"), ("Lines of code", f"{totals['code']:,}"), ("Repository size", fmt_bytes(totals["size"])), ("Languages", str(len({f['language'] for f in files if f['language'] != 'Other'}))), ("Dependencies", f"{len(analysis['dependencies']):,}"), ("TODO / FIXME", f"{analysis['todo_count']:,}")]
    for col, (label, value) in zip(metrics, values): col.metric(label, value)
    a, b = st.columns(2)
    with a:
        st.markdown("<div class='section-title'>Language distribution</div>", unsafe_allow_html=True)
        st.plotly_chart(language_chart(files), use_container_width=True, config={"displayModeBar": False})
    with b:
        st.markdown("<div class='section-title'>Files by directory</div>", unsafe_allow_html=True)
        st.plotly_chart(directory_chart(files), use_container_width=True, config={"displayModeBar": False})
    a, b = st.columns(2)
    with a:
        st.markdown("<div class='section-title'>Code composition</div>", unsafe_allow_html=True)
        st.plotly_chart(composition_chart(totals), use_container_width=True, config={"displayModeBar": False})
    with b:
        st.markdown("<div class='section-title'>Largest files</div>", unsafe_allow_html=True)
        st.plotly_chart(largest_chart(files), use_container_width=True, config={"displayModeBar": False})
    st.markdown("<div class='section-title'>Recently surfaced findings</div>", unsafe_allow_html=True)
    if analysis["findings"]:
        st.dataframe(analysis["findings"][:8], hide_index=True, use_container_width=True)
    else: st.success("No findings from the configured lightweight checks.")
elif section == "Architecture":
    st.markdown("<div class='section-title'>Repository structure</div>", unsafe_allow_html=True)
    left, right = st.columns([1.15, .85])
    with left:
        query = st.text_input("Filter folders and files", placeholder="Search repository tree")
        for d in dirs:
            if query and query.lower() not in d["directory"].lower(): continue
            children = [f for f in files if f["directory"] == d["directory"] and (not query or query.lower() in f["path"].lower())]
            if d["directory"] == "." or children:
                with st.expander(f"📁 {d['directory']}  ·  {d['files']} files  ·  depth {d['depth']}", expanded=d["directory"] == "."):
                    st.dataframe([{ "File": f["name"], "Language": f["language"], "Lines": f["lines"], "Size": fmt_bytes(f["size_bytes"])} for f in children], hide_index=True, use_container_width=True, height=min(340, 40 + 35 * max(1,len(children))))
    with right:
        st.markdown("<div class='section-title'>Directory metrics</div>", unsafe_allow_html=True)
        st.dataframe([{ "Directory": d["directory"], "Files": d["files"], "Depth": d["depth"], "Size": fmt_bytes(d["size_bytes"])} for d in sorted(dirs,key=lambda x:x["files"],reverse=True)[:25]], hide_index=True, use_container_width=True)
        st.markdown("<div class='section-title'>Internal Python imports</div>", unsafe_allow_html=True)
        if analysis["imports"]: st.dataframe(analysis["imports"], hide_index=True, use_container_width=True)
        else: st.caption("No internal Python module imports detected.")
elif section == "Files":
    st.markdown("<div class='section-title'>File inventory</div>", unsafe_allow_html=True)
    query = st.text_input("Search file paths", placeholder="Filter by filename, folder, or language")
    filtered = [f for f in files if query.lower() in f["path"].lower() or query.lower() in f["language"].lower()] if query else files
    st.caption(f"Showing {len(filtered):,} of {len(files):,} files. Files over 1 MB and binary files are skipped.")
    st.dataframe([{ "Path":f["path"], "Language":f["language"], "Bytes":f["size_bytes"], "Lines":f["lines"], "Code":f["code_lines"], "Comments":f["comment_lines"], "Blank":f["blank_lines"], "Depth":f["depth"]} for f in filtered], hide_index=True, use_container_width=True, height=560)
elif section == "Dependencies":
    st.markdown("<div class='section-title'>Declared dependencies</div>", unsafe_allow_html=True)
    if analysis["dependencies"]:
        st.dataframe(analysis["dependencies"], hide_index=True, use_container_width=True)
        from collections import Counter
        st.bar_chart(Counter(d["ecosystem"] for d in analysis["dependencies"]))
    else: st.info("No dependencies found in requirements.txt, pyproject.toml, Pipfile, or package.json.")
    st.caption("Declarations are parsed from project files. Nothing is installed or executed.")
elif section == "Issues":
    st.markdown("<div class='section-title'>Lightweight code checks</div>", unsafe_allow_html=True)
    st.caption("Informational checks only; this is not a comprehensive security audit.")
    findings = analysis["findings"]
    if findings:
        kind = st.multiselect("Finding types", sorted({x["type"] for x in findings}), default=sorted({x["type"] for x in findings}))
        shown = [x for x in findings if x["type"] in kind]
        st.dataframe(shown, hide_index=True, use_container_width=True, height=560)
        st.caption(f"{len(shown)} findings")
    else: st.success("No findings from the configured lightweight checks.")

st.markdown("<hr><div style='color:#657187;font:11px DM Mono;padding:2px 0 10px'>CODEBASE X-RAY &nbsp;·&nbsp; PRIVATE LOCAL SCAN &nbsp;·&nbsp; READ ONLY</div>", unsafe_allow_html=True)
