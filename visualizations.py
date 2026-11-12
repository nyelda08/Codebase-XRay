"""Plotly chart builders for repository scan data."""
from collections import Counter

import plotly.express as px
import plotly.graph_objects as go

COLORS = ["#60a5fa", "#a78bfa", "#34d399", "#fbbf24", "#f472b6", "#22d3ee", "#fb7185", "#818cf8"]
LAYOUT = dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=12, r=12, t=36, b=12), font=dict(family="Inter, sans-serif", color="#cbd5e1"))


def language_chart(files):
    counts = Counter(f["language"] for f in files if f["language"] != "Other")
    if not counts: return _empty("No recognized languages found")
    fig = px.pie(names=list(counts), values=list(counts.values()), hole=.68, color_discrete_sequence=COLORS)
    fig.update_traces(textposition="inside", textinfo="percent", hovertemplate="%{label}: %{value} files<extra></extra>")
    fig.update_layout(**LAYOUT, showlegend=True, legend=dict(orientation="h", y=-.12))
    return fig


def directory_chart(files):
    counts = Counter(f["directory"] for f in files)
    top = counts.most_common(12)
    if not top: return _empty("No files to chart")
    fig = px.bar(x=[n for _, n in top], y=[d for d, _ in top], orientation="h", color=[n for _, n in top], color_continuous_scale=[[0,"#334155"],[1,"#818cf8"]], labels={"x":"Files", "y":"Directory", "color":"Files"})
    fig.update_layout(**LAYOUT, yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
    return fig


def composition_chart(totals):
    vals = [totals["code"], totals["comments"], totals["blank"]]
    if not sum(vals): return _empty("No line data found")
    fig = go.Figure(go.Bar(x=["Code", "Comments", "Blank"], y=vals, marker_color=COLORS[:3], text=[f"{v:,}" for v in vals], textposition="auto"))
    fig.update_layout(**LAYOUT, showlegend=False, yaxis_title="Lines")
    return fig


def largest_chart(files):
    top = sorted(files, key=lambda f: f["size_bytes"], reverse=True)[:10]
    if not top: return _empty("No files to chart")
    fig = px.bar(x=[f["size_bytes"] / 1024 for f in top], y=[f["path"] for f in top], orientation="h", color_discrete_sequence=["#60a5fa"], labels={"x":"Size (KB)","y":"File"})
    fig.update_layout(**LAYOUT, yaxis=dict(autorange="reversed"), showlegend=False)
    return fig


def _empty(message):
    fig = go.Figure()
    fig.add_annotation(text=message, x=.5, y=.5, xref="paper", yref="paper", showarrow=False, font=dict(color="#94a3b8"))
    fig.update_layout(**LAYOUT, xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig
