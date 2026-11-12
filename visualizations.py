"""Plotly visualizations for repository scan results."""
from collections import Counter

import plotly.express as px
import plotly.graph_objects as go

COLORS = ["#2F81F7", "#3FB950", "#D29922", "#F85149", "#A371F7", "#39C5CF", "#8B949E", "#DB6D28"]
LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": {"l": 8, "r": 12, "t": 12, "b": 12},
    "font": {"family": "Inter, sans-serif", "color": "#8B949E", "size": 11},
    "colorway": COLORS,
}


def language_chart(files):
    counts = Counter(f["language"] for f in files if f["language"] != "Other")
    if not counts:
        return _empty("No recognized languages found")
    fig = px.pie(
        names=list(counts),
        values=list(counts.values()),
        hole=0.66,
        color_discrete_sequence=COLORS,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        marker={"line": {"color": "#0D1117", "width": 2}},
        hovertemplate="%{label}: %{value} files<extra></extra>",
    )
    fig.update_layout(
        **LAYOUT,
        showlegend=True,
        legend={"orientation": "h", "y": -0.12, "font": {"size": 10}},
    )
    return fig


def directory_chart(files):
    counts = Counter(f["directory"] for f in files)
    top = counts.most_common(10)
    if not top:
        return _empty("No files to chart")
    fig = px.bar(
        x=[n for _, n in top],
        y=[d for d, _ in top],
        orientation="h",
        color_discrete_sequence=["#2F81F7"],
        labels={"x": "Files", "y": "Directory"},
    )
    fig.update_traces(hovertemplate="%{y}: %{x} files<extra></extra>")
    fig.update_layout(
        **LAYOUT,
        yaxis={"autorange": "reversed", "gridcolor": "rgba(48,54,61,.35)"},
        xaxis={"gridcolor": "rgba(48,54,61,.55)", "rangemode": "tozero"},
        showlegend=False,
    )
    return fig


def composition_chart(totals):
    labels = ["Code", "Comments", "Blank"]
    values = [totals["code"], totals["comments"], totals["blank"]]
    if not sum(values):
        return _empty("No line data found")
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=["#2F81F7", "#3FB950", "#484F58"],
            marker_line_width=0,
            text=[f"{v:,}" for v in values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}: %{y:,} lines<extra></extra>",
        )
    )
    fig.update_layout(
        **LAYOUT,
        showlegend=False,
        yaxis_title="Lines",
        yaxis={"gridcolor": "rgba(48,54,61,.55)", "rangemode": "tozero"},
    )
    return fig


def largest_chart(files):
    top = sorted(files, key=lambda f: f["size_bytes"], reverse=True)[:10]
    if not top:
        return _empty("No files to chart")
    fig = px.bar(
        x=[f["size_bytes"] / 1024 for f in top],
        y=[f["path"] for f in top],
        orientation="h",
        color_discrete_sequence=["#2F81F7"],
        labels={"x": "Size (KB)", "y": "File"},
    )
    fig.update_traces(hovertemplate="%{y}<br>%{x:.1f} KB<extra></extra>")
    fig.update_layout(
        **LAYOUT,
        yaxis={"autorange": "reversed", "tickfont": {"family": "IBM Plex Mono, monospace", "size": 9}},
        xaxis={"gridcolor": "rgba(48,54,61,.55)", "rangemode": "tozero"},
        showlegend=False,
    )
    return fig


def import_graph(imports):
    """Show directed internal Python imports as a compact Sankey graph."""
    links = Counter((item["source"], item["target"]) for item in imports)
    nodes = sorted({node for pair in links for node in pair})
    if not nodes or not links:
        return _empty("No internal imports to show")
    positions = {name: index for index, name in enumerate(nodes)}
    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node={
                "label": nodes,
                "pad": 14,
                "thickness": 12,
                "line": {"color": "#30363D", "width": 1},
                "color": "#2F81F7",
                "hovertemplate": "%{label}<extra></extra>",
            },
            link={
                "source": [positions[source] for source, _ in links],
                "target": [positions[target] for _, target in links],
                "value": list(links.values()),
                "color": "rgba(47,129,247,.28)",
                "hovertemplate": "%{source.label} imports %{target.label}<extra></extra>",
            },
        )
    )
    fig.update_layout(**LAYOUT, height=max(300, min(620, 36 * len(nodes) + 100)))
    return fig


def _empty(message):
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"color": "#8B949E", "size": 12},
    )
    fig.update_layout(
        **LAYOUT,
        height=280,
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig
