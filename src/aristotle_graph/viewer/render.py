from __future__ import annotations

import json
from html import escape
from typing import Any

from aristotle_graph.annotations.models import ConceptAnnotation, RelationAnnotation
from aristotle_graph.viewer.load import ViewerDataset

_KIND_COLORS = {
    "virtue": "#2a9d8f",
    "vice": "#e76f51",
    "domain": "#457b9d",
    "principle": "#8d99ae",
    "state": "#3d5a80",
    "faculty": "#6d597a",
    "passion": "#f4a261",
    "process": "#90be6d",
    "action": "#577590",
    "person": "#264653",
    "condition": "#b56576",
}

_EDGE_COLORS = {
    "approved": "#34506b",
    "candidate": "#9aa5b1",
}

_GRAPH_CLICK_BRIDGE = """
if (typeof network !== "undefined") {
    const emitConceptNavigation = function(params) {
        if (!params || !Array.isArray(params.nodes) || params.nodes.length === 0) {
            return;
        }
        window.parent.postMessage(
            { type: "avg-node-click", conceptId: String(params.nodes[0]) },
            "*"
        );
    };
    network.on("click", function(params) {
        emitConceptNavigation(params);
    });
    network.on("doubleClick", function(params) {
        emitConceptNavigation(params);
    });
    network.on("selectNode", function(params) {
        emitConceptNavigation(params);
    });
    network.on("hoverNode", function() {
        if (network.canvas && network.canvas.body && network.canvas.body.container) {
            network.canvas.body.container.style.cursor = "pointer";
        }
    });
    network.on("blurNode", function() {
        if (network.canvas && network.canvas.body && network.canvas.body.container) {
            network.canvas.body.container.style.cursor = "default";
        }
    });
}
"""


def viewer_shell_css() -> str:
    return """
<style>
:root {
    --avg-bg: #f6efe2;
    --avg-bg-soft: #fcf8f0;
    --avg-ink: #18324e;
    --avg-ink-strong: #10253b;
    --avg-muted: #5f6f80;
    --avg-border: #d8cab2;
    --avg-border-strong: #b99870;
    --avg-panel: rgba(255, 252, 246, 0.95);
    --avg-panel-soft: rgba(248, 241, 230, 0.94);
    --avg-panel-strong: rgba(255, 255, 253, 0.98);
    --avg-accent: #8f5a34;
    --avg-accent-strong: #754524;
    --avg-accent-soft: rgba(143, 90, 52, 0.12);
    --avg-shadow: 0 20px 42px rgba(21, 45, 70, 0.08);
    --avg-shadow-soft: 0 12px 28px rgba(21, 45, 70, 0.05);
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top, rgba(255, 255, 255, 0.56), transparent 34%),
        linear-gradient(180deg, #fbf6ec 0%, #f2e8d8 100%);
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, rgba(236, 242, 250, 0.98) 0%, rgba(229, 237, 247, 0.98) 100%);
    border-right: 1px solid #d4dce8;
}

[data-testid="stSidebar"] .block-container {
    padding-top: 1.15rem;
    padding-right: 1rem;
    padding-left: 1rem;
    padding-bottom: 2rem;
}

.block-container {
    max-width: 1240px;
    padding-top: 1.05rem;
    padding-right: 1.65rem;
    padding-bottom: 3rem;
    padding-left: 1.65rem;
}

.avg-hero {
    background:
        linear-gradient(135deg, rgba(255, 254, 250, 0.98), rgba(245, 235, 218, 0.98));
    border: 1px solid rgba(185, 157, 123, 0.7);
    border-radius: 30px;
    padding: 1.35rem 1.45rem 1.05rem 1.45rem;
    margin-bottom: 0.9rem;
    box-shadow: var(--avg-shadow-soft);
    overflow: visible;
}

.avg-kicker {
    color: var(--avg-accent);
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.45rem;
    line-height: 1.3;
    padding-top: 0.08rem;
    overflow: visible;
}

.avg-title {
    color: var(--avg-ink-strong);
    font-family: Georgia, serif;
    font-size: clamp(2.05rem, 3vw, 3.05rem);
    font-weight: 700;
    line-height: 1.16;
    margin-bottom: 0;
    padding-top: 0.04rem;
    overflow: visible;
}

.avg-copy {
    color: var(--avg-ink);
    font-size: 1rem;
    line-height: 1.55;
    margin-bottom: 0.9rem;
    max-width: 58rem;
}

.avg-chip-row,
.avg-legend-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
}

.avg-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.38rem 0.82rem;
    border-radius: 999px;
    border: 1px solid rgba(185, 157, 123, 0.66);
    background: rgba(255, 255, 255, 0.88);
    color: var(--avg-ink);
    font-size: 0.88rem;
}

.avg-section-heading {
    margin: 0.04rem 0 0.75rem 0;
}

.avg-section-heading h2,
.avg-section-heading h3 {
    color: var(--avg-ink-strong);
    font-family: Georgia, serif;
    line-height: 1.12;
    margin: 0 0 0.22rem 0;
}

.avg-section-heading p {
    color: var(--avg-muted);
    margin: 0;
    line-height: 1.5;
    max-width: 48rem;
}

.avg-card {
    border: 1px solid rgba(185, 157, 123, 0.72);
    border-radius: 22px;
    background: var(--avg-panel);
    padding: 1rem 1.08rem;
    height: 100%;
    box-shadow: var(--avg-shadow-soft);
}

.avg-card h3,
.avg-card h4 {
    color: var(--avg-ink-strong);
    font-family: Georgia, serif;
    margin: 0 0 0.35rem 0;
    line-height: 1.14;
}

.avg-card p {
    color: var(--avg-ink);
    line-height: 1.58;
    margin: 0;
}

.avg-card-kicker {
    color: var(--avg-accent);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}

.avg-soft-text,
.avg-helper,
.avg-filter-summary {
    color: var(--avg-muted);
    font-size: 0.9rem;
    line-height: 1.5;
}

.avg-helper strong {
    color: var(--avg-ink-strong);
}

.avg-list {
    margin: 0.18rem 0 0 0;
    padding-left: 1.1rem;
    color: var(--avg-ink);
    line-height: 1.55;
}

.avg-list li {
    margin-bottom: 0.45rem;
}

.avg-stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(138px, 1fr));
    gap: 0.72rem;
    margin: 0.15rem 0 0.9rem 0;
}

.avg-stat-card {
    border: 1px solid rgba(185, 157, 123, 0.72);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.84);
    padding: 0.82rem 0.88rem;
    box-shadow: 0 10px 20px rgba(23, 49, 78, 0.03);
}

.avg-stat-value {
    color: var(--avg-ink-strong);
    font-family: Georgia, serif;
    font-size: 1.35rem;
    font-weight: 700;
    line-height: 1.1;
}

.avg-stat-label {
    color: var(--avg-muted);
    font-size: 0.8rem;
    margin-top: 0.18rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.avg-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin: 0.55rem 0 0.85rem 0;
}

.avg-meta-pill {
    display: inline-flex;
    align-items: center;
    padding: 0.33rem 0.66rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.84);
    border: 1px solid rgba(185, 157, 123, 0.62);
    color: var(--avg-ink);
    font-size: 0.84rem;
}

.avg-triad {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.65rem;
    margin: 0.45rem 0 0.9rem 0;
}

.avg-triad-cell {
    border: 1px solid rgba(185, 157, 123, 0.72);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.86);
    padding: 0.75rem 0.8rem;
}

.avg-triad-label {
    color: var(--avg-muted);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.2rem;
}

.avg-triad-value {
    color: var(--avg-ink);
    font-size: 0.98rem;
    line-height: 1.35;
}

.avg-pill-note {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    background: rgba(139, 90, 60, 0.12);
    color: var(--avg-accent-strong);
    font-size: 0.9rem;
    font-weight: 600;
}

.avg-context {
    border: 1px solid rgba(185, 157, 123, 0.78);
    border-radius: 24px;
    background:
        linear-gradient(135deg, rgba(255, 253, 248, 0.98), rgba(246, 239, 226, 0.98));
    padding: 1.05rem 1.12rem;
    box-shadow: var(--avg-shadow-soft);
}

.avg-context-title {
    color: var(--avg-ink-strong);
    font-family: Georgia, serif;
    font-size: 1.34rem;
    margin-bottom: 0.32rem;
    line-height: 1.12;
}

.avg-context p,
.avg-context-detail {
    color: var(--avg-ink);
    line-height: 1.55;
    margin: 0.18rem 0 0 0;
}

.avg-context-detail {
    color: var(--avg-muted);
}

.avg-prose-card {
    border: 1px solid rgba(185, 157, 123, 0.72);
    border-radius: 24px;
    background: rgba(255, 252, 246, 0.92);
    padding: 1.02rem 1.08rem;
    box-shadow: var(--avg-shadow-soft);
}

.avg-prose-card h3 {
    color: var(--avg-ink-strong);
    font-family: Georgia, serif;
    margin: 0 0 0.34rem 0;
    line-height: 1.14;
}

.avg-prose-card p {
    color: var(--avg-ink);
    line-height: 1.72;
    margin: 0.32rem 0 0 0;
}

.avg-rank-list {
    display: grid;
    gap: 0.5rem;
}

.avg-rank-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
    padding: 0.75rem 0.82rem;
    border-radius: 16px;
    border: 1px solid rgba(185, 157, 123, 0.62);
    background: rgba(255, 255, 255, 0.82);
}

.avg-rank-label {
    color: var(--avg-ink);
    font-weight: 600;
    line-height: 1.4;
}

.avg-rank-value {
    color: var(--avg-muted);
    white-space: nowrap;
    font-size: 0.88rem;
}

.avg-steps {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.72rem;
    margin: 0.2rem 0 0.85rem 0;
}

.avg-step {
    border: 1px solid rgba(185, 157, 123, 0.66);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.8);
    padding: 0.8rem 0.88rem;
    box-shadow: 0 8px 18px rgba(23, 49, 78, 0.03);
}

.avg-step-number {
    color: var(--avg-accent);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.24rem;
}

.avg-step-text {
    color: var(--avg-ink);
    line-height: 1.48;
}

.avg-reading-panel {
    border: 1px solid rgba(185, 157, 123, 0.78);
    border-radius: 26px;
    background:
        linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(248, 242, 232, 0.98));
    padding: 1.08rem 1.18rem 1.22rem;
    box-shadow: var(--avg-shadow-soft);
}

.avg-reading-title {
    color: var(--avg-ink-strong);
    font-family: Georgia, serif;
    font-size: 1.42rem;
    margin-bottom: 0.25rem;
    line-height: 1.14;
}

.avg-reading-meta {
    color: var(--avg-muted);
    font-size: 0.85rem;
    margin-bottom: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.avg-reading-lead {
    color: var(--avg-muted);
    line-height: 1.55;
    margin-bottom: 0.9rem;
}

.avg-reading-text {
    color: var(--avg-ink-strong);
    font-family: Georgia, serif;
    font-size: 1.03rem;
    line-height: 1.95;
    white-space: pre-wrap;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 252, 246, 0.86);
    border: 1px solid rgba(185, 157, 123, 0.7) !important;
    border-radius: 22px !important;
    box-shadow: var(--avg-shadow-soft);
}

[data-testid="stExpander"] {
    background: rgba(255, 252, 246, 0.8);
    border: 1px solid rgba(185, 157, 123, 0.7);
    border-radius: 18px;
}

[data-testid="stExpander"] details summary p {
    color: var(--avg-ink-strong);
    font-weight: 600;
}

div.stButton > button,
div[data-testid="stPopover"] > button,
div[data-testid="stDownloadButton"] > button {
    border-radius: 999px;
    border: 1px solid var(--avg-border-strong);
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(250, 243, 232, 0.98));
    color: var(--avg-ink-strong);
    min-height: 2.8rem;
    font-weight: 600;
    box-shadow: 0 8px 16px rgba(23, 49, 78, 0.04);
    transition:
        transform 0.12s ease,
        box-shadow 0.12s ease,
        border-color 0.12s ease;
}

div.stButton > button:hover,
div[data-testid="stPopover"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover {
    border-color: var(--avg-accent);
    color: var(--avg-ink-strong);
    transform: translateY(-1px);
    box-shadow: 0 12px 20px rgba(23, 49, 78, 0.06);
}

div.stButton > button[kind="primary"],
div[data-testid="stDownloadButton"] > button[kind="primary"] {
    background: linear-gradient(180deg, #9d6940 0%, #7c4a29 100%);
    color: #fffaf5;
    border-color: #744624;
}

div.stButton > button[kind="primary"]:hover,
div[data-testid="stDownloadButton"] > button[kind="primary"]:hover {
    color: #fffaf5;
}

div.stButton > button:focus-visible,
div[data-testid="stPopover"] > button:focus-visible,
div[data-testid="stDownloadButton"] > button:focus-visible {
    outline: 2px solid rgba(143, 90, 52, 0.32);
    outline-offset: 1px;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    border-radius: 16px !important;
    border-color: rgba(185, 157, 123, 0.88) !important;
    background: rgba(255, 253, 248, 0.96) !important;
}

[data-baseweb="select"] span,
[data-baseweb="input"] input {
    color: var(--avg-ink-strong) !important;
}

div[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.82);
    border: 1px solid rgba(185, 157, 123, 0.72);
    border-radius: 18px;
    padding: 0.42rem 0.5rem;
}

[data-testid="stRadio"] [role="radiogroup"] {
    gap: 0.45rem;
    flex-wrap: wrap;
}

[data-testid="stRadio"] [role="radiogroup"] > label {
    border: 1px solid rgba(185, 157, 123, 0.72);
    border-radius: 999px;
    padding: 0.24rem 0.72rem;
    background: rgba(255, 252, 246, 0.82);
    transition:
        border-color 0.12s ease,
        background 0.12s ease,
        box-shadow 0.12s ease;
}

[data-testid="stRadio"] [role="radiogroup"] > label:hover {
    border-color: rgba(143, 90, 52, 0.72);
}

[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
    background: rgba(143, 90, 52, 0.12);
    border-color: rgba(143, 90, 52, 0.88);
    box-shadow: inset 0 0 0 1px rgba(143, 90, 52, 0.12);
}

[data-testid="stToggle"] label p {
    color: var(--avg-ink);
}

.avg-kind-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.35rem 0.7rem;
    margin: 0 0.45rem 0.45rem 0;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.84);
    border: 1px solid rgba(185, 157, 123, 0.72);
    color: var(--avg-ink-strong);
    font-size: 0.9rem;
}

.avg-kind-dot {
    width: 0.8rem;
    height: 0.8rem;
    border-radius: 999px;
    display: inline-block;
}

@media (max-width: 900px) {
    .avg-title {
        font-size: 1.95rem;
    }

    .block-container {
        padding-right: 1rem;
        padding-left: 1rem;
    }

    .avg-stat-grid,
    .avg-triad,
    .avg-steps {
        grid-template-columns: 1fr;
    }

    .avg-hero {
        border-radius: 24px;
        padding: 1rem 1rem 0.92rem 1rem;
    }

    .avg-card,
    .avg-context,
    .avg-reading-panel,
    .avg-prose-card {
        border-radius: 18px;
    }
}
</style>
"""


def _chip_html(text: str) -> str:
    return f"<span class='avg-chip'>{escape(text)}</span>"


def hero_html(*, title: str, subtitle: str | None, chips: list[str]) -> str:
    subtitle_html = (
        f"<div class='avg-copy'>{escape(subtitle)}</div>" if subtitle else ""
    )
    chip_row_html = (
        f"<div class='avg-chip-row'>{''.join(_chip_html(chip) for chip in chips)}</div>"
        if chips
        else ""
    )
    return (
        "<div class='avg-hero'>"
        "<div class='avg-kicker'>Nicomachean Ethics</div>"
        f"<div class='avg-title'>{escape(title)}</div>"
        f"{subtitle_html}"
        f"{chip_row_html}"
        "</div>"
    )


def section_heading_html(*, title: str, body: str, level: int = 2) -> str:
    safe_level = 2 if level not in {2, 3} else level
    return (
        "<div class='avg-section-heading'>"
        f"<h{safe_level}>{escape(title)}</h{safe_level}>"
        f"<p>{escape(body)}</p>"
        "</div>"
    )


def simple_card_html(
    *,
    title: str,
    body: str,
    eyebrow: str | None = None,
) -> str:
    eyebrow_html = (
        f"<div class='avg-card-kicker'>{escape(eyebrow)}</div>" if eyebrow is not None else ""
    )
    return (
        "<div class='avg-card'>"
        f"{eyebrow_html}"
        f"<h3>{escape(title)}</h3>"
        f"<p>{escape(body)}</p>"
        "</div>"
    )


def stat_grid_html(items: list[tuple[str, str]]) -> str:
    cards = []
    for label, value in items:
        cards.append(
            "<div class='avg-stat-card'>"
            f"<div class='avg-stat-value'>{escape(value)}</div>"
            f"<div class='avg-stat-label'>{escape(label)}</div>"
            "</div>"
        )
    return "<div class='avg-stat-grid'>" + "".join(cards) + "</div>"


def bullet_list_html(items: list[str]) -> str:
    rows = [f"<li>{escape(item)}</li>" for item in items]
    return "<ul class='avg-list'>" + "".join(rows) + "</ul>"


def meta_pills_html(items: list[str]) -> str:
    if not items:
        return ""
    pills = "".join(f"<span class='avg-meta-pill'>{escape(item)}</span>" for item in items)
    return f"<div class='avg-meta-row'>{pills}</div>"


def prose_panel_html(*, title: str, body: str, eyebrow: str | None = None) -> str:
    eyebrow_html = (
        f"<div class='avg-card-kicker'>{escape(eyebrow)}</div>" if eyebrow is not None else ""
    )
    paragraphs = [
        f"<p>{escape(paragraph)}</p>"
        for paragraph in body.split("\n\n")
        if paragraph.strip()
    ]
    return (
        "<div class='avg-prose-card'>"
        f"{eyebrow_html}"
        f"<h3>{escape(title)}</h3>"
        f"{''.join(paragraphs)}"
        "</div>"
    )


def ranking_rows_html(items: list[tuple[str, str]]) -> str:
    if not items:
        return ""
    rows = []
    for label, value in items:
        rows.append(
            "<div class='avg-rank-row'>"
            f"<div class='avg-rank-label'>{escape(label)}</div>"
            f"<div class='avg-rank-value'>{escape(value)}</div>"
            "</div>"
        )
    return "<div class='avg-rank-list'>" + "".join(rows) + "</div>"


def reading_panel_html(
    *,
    meta: str,
    text: str,
    title: str | None = None,
    lead: str | None = None,
) -> str:
    title_html = f"<div class='avg-reading-title'>{escape(title)}</div>" if title else ""
    lead_html = f"<div class='avg-reading-lead'>{escape(lead)}</div>" if lead else ""
    return (
        "<div class='avg-reading-panel'>"
        f"{title_html}"
        f"<div class='avg-reading-meta'>{escape(meta)}</div>"
        f"{lead_html}"
        f"<div class='avg-reading-text'>{escape(text)}</div>"
        "</div>"
    )


def step_cards_html(steps: list[str]) -> str:
    cards = []
    for index, step in enumerate(steps, start=1):
        cards.append(
            "<div class='avg-step'>"
            f"<div class='avg-step-number'>Step {index}</div>"
            f"<div class='avg-step-text'>{escape(step)}</div>"
            "</div>"
        )
    return "<div class='avg-steps'>" + "".join(cards) + "</div>"


def intro_markdown() -> str:
    return (
        "Move between Aristotle's structure in Book II and the passages that support each claim."
    )


def kind_color(kind: str) -> str:
    return _KIND_COLORS.get(kind, "#6c757d")


def edge_color(review_status: str) -> str:
    return _EDGE_COLORS.get(review_status, "#9aa5b1")


def _join_labels(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def _target_labels(
    concept_id: str,
    dataset: ViewerDataset,
    relation_type: str,
) -> list[str]:
    labels: list[str] = []
    for relation in dataset.outgoing_relations.get(concept_id, ()):
        if relation.relation_type != relation_type:
            continue
        labels.append(dataset.concept_index[relation.target_id].primary_label)
    return sorted(labels, key=str.lower)


def _incoming_roles(concept: ConceptAnnotation, dataset: ViewerDataset) -> list[str]:
    roles: list[str] = []
    for relation in dataset.incoming_relations.get(concept.id, ()):
        source_label = dataset.concept_index[relation.source_id].primary_label
        if relation.relation_type == "has_excess":
            roles.append(f"the excess opposed to {source_label}")
        elif relation.relation_type == "has_deficiency":
            roles.append(f"the deficiency opposed to {source_label}")
        elif relation.relation_type == "concerns":
            roles.append(f"the domain for {source_label}")
        elif relation.relation_type == "is_a":
            roles.append(f"a broader category for {source_label}")
        elif relation.relation_type == "determined_by":
            roles.append(f"something that helps determine {source_label}")
    return roles


def concept_triad_data(
    concept: ConceptAnnotation,
    dataset: ViewerDataset,
) -> dict[str, str] | None:
    deficiency_labels = _target_labels(concept.id, dataset, "has_deficiency")
    excess_labels = _target_labels(concept.id, dataset, "has_excess")
    concern_labels = _target_labels(concept.id, dataset, "concerns")
    if not deficiency_labels or not excess_labels:
        return None
    return {
        "deficiency": _join_labels(deficiency_labels),
        "virtue": concept.primary_label,
        "excess": _join_labels(excess_labels),
        "domain": _join_labels(concern_labels) if concern_labels else "No explicit domain",
    }


def triad_strip_html(concept: ConceptAnnotation, dataset: ViewerDataset) -> str:
    triad = concept_triad_data(concept, dataset)
    if triad is None:
        return ""
    cells = [
        ("Deficiency", triad["deficiency"]),
        ("Virtue", triad["virtue"]),
        ("Excess", triad["excess"]),
        ("Domain", triad["domain"]),
    ]
    html_cells = []
    for label, value in cells:
        html_cells.append(
            "<div class='avg-triad-cell'>"
            f"<div class='avg-triad-label'>{escape(label)}</div>"
            f"<div class='avg-triad-value'>{escape(value)}</div>"
            "</div>"
        )
    return "<div class='avg-triad'>" + "".join(html_cells) + "</div>"


def concept_role_line(concept: ConceptAnnotation, dataset: ViewerDataset) -> str:
    triad = concept_triad_data(concept, dataset)
    if triad is not None:
        return (
            f"Book II presents {concept.primary_label} as the mean between "
            f"{triad['deficiency']} and {triad['excess']} in the sphere of {triad['domain']}."
        )

    if concept.id == "moral-virtue":
        return (
            "A central Book II claim about character: moral virtue is formed by habit and "
            "revealed through pleasure and pain."
        )
    if concept.id == "ethical-mean":
        return "A guiding Book II claim about how virtue avoids deficiency and excess."
    if concept.id == "state-of-character":
        return "A stable condition Book II distinguishes from passing feelings or capacities."
    if concept.id == "virtuous-action":
        return "A practical Book II test for when an action truly counts as virtuous."
    if concept.kind == "domain":
        return (
            "The sphere of feeling or action in which Book II places a virtue and its extremes."
        )
    if concept.kind == "vice":
        return "One of the opposed extremes Book II sets around a virtue."
    if concept.kind == "process":
        return "A process Book II uses to explain how character is formed."

    return concept.description


def concept_story_markdown(concept: ConceptAnnotation, dataset: ViewerDataset) -> str:
    label = concept.primary_label
    triad = concept_triad_data(concept, dataset)
    concern_labels = _target_labels(concept.id, dataset, "concerns")
    is_a_labels = _target_labels(concept.id, dataset, "is_a")
    formed_by_labels = _target_labels(concept.id, dataset, "formed_by")
    requires_labels = _target_labels(concept.id, dataset, "requires")
    determined_by_labels = _target_labels(concept.id, dataset, "determined_by")
    contrasted_with_labels = _target_labels(concept.id, dataset, "contrasted_with")
    opposed_to_labels = _target_labels(concept.id, dataset, "opposed_to")

    sentences: list[str] = []
    if triad is not None:
        sentences.append(
            f"Book II presents {label} as the mean between {triad['deficiency']} "
            f"and {triad['excess']} in the sphere of {triad['domain']}."
        )
        sentences.append(
            f"This lets you read {label} as more than an isolated label: the graph keeps "
            "together the virtue, its deficiency, its excess, and the domain in which "
            "Aristotle judges them."
        )
    elif concept.id == "moral-virtue":
        sentences.append(
            "Book II uses moral virtue to explain how character is formed rather than simply "
            "described."
        )
        if formed_by_labels:
            sentences.append(f"It is formed by {_join_labels(formed_by_labels)}.")
        if concern_labels:
            sentences.append(
                f"It is closely tied to {_join_labels(concern_labels)}, because those are part "
                "of how Aristotle tells whether character has been shaped well or badly."
            )
        if is_a_labels:
            sentences.append(
                f"Aristotle also treats it as {_join_labels(is_a_labels)}, "
                "not as a passing feeling."
            )
        if contrasted_with_labels:
            sentences.append(
                f"The graph also keeps it distinct from {_join_labels(contrasted_with_labels)}."
            )
    elif concept.id == "ethical-mean":
        sentences.append(
            "The mean is Book II's core pattern for ethical judgment: not any middle whatsoever, "
            "but the fitting point between opposed failures."
        )
        if contrasted_with_labels:
            sentences.append(
                f"Book II contrasts the mean with {_join_labels(contrasted_with_labels)}."
            )
        if determined_by_labels:
            sentences.append(
                "It is determined by rational principle and the man of practical wisdom."
            )
    elif concept.id == "state-of-character":
        sentences.append(
            "Book II needs this idea because virtue is supposed to be a stable way of being, "
            "not a momentary feeling."
        )
        if contrasted_with_labels:
            sentences.append(
                f"Book II identifies {label} by contrasting it with "
                f"{_join_labels(contrasted_with_labels)}."
            )
        if incoming_roles := _incoming_roles(concept, dataset):
            sentences.append(
                f"In this graph, it functions as {_join_labels(incoming_roles)}."
            )
    elif concept.id == "virtuous-action":
        if requires_labels:
            sentences.append(
                f"Book II uses {label} to mark what must be present in action: "
                f"{_join_labels(requires_labels)}."
            )
    elif concept.id == "habituation":
        sentences.append(
            "Habituation is the practical route by which Book II says character is acquired."
        )
        if incoming_roles := _incoming_roles(concept, dataset):
            sentences.append(
                f"In this graph it appears as {_join_labels(incoming_roles)}, which is why it "
                "matters for the formation of virtue."
            )
    elif concern_labels:
        sentences.append(
            f"Book II treats {label} in the sphere of {_join_labels(concern_labels)}."
        )

    if is_a_labels and concept.id != "moral-virtue":
        sentences.append(f"Aristotle classifies {label} as {_join_labels(is_a_labels)}.")
    if formed_by_labels and concept.id != "moral-virtue":
        sentences.append(f"{label.capitalize()} is formed by {_join_labels(formed_by_labels)}.")
    if requires_labels and concept.id != "virtuous-action":
        sentences.append(f"{label.capitalize()} requires {_join_labels(requires_labels)}.")
    if determined_by_labels and concept.id != "ethical-mean":
        sentences.append(
            f"{label.capitalize()} is determined by {_join_labels(determined_by_labels)}."
        )
    if contrasted_with_labels and concept.id not in {
        "moral-virtue",
        "ethical-mean",
        "state-of-character",
    }:
        sentences.append(
            f"Book II contrasts {label} with {_join_labels(contrasted_with_labels)}."
        )
    if opposed_to_labels:
        sentences.append(f"{label.capitalize()} is opposed to {_join_labels(opposed_to_labels)}.")

    incoming_roles = _incoming_roles(concept, dataset)
    if not sentences and incoming_roles:
        sentences.append(f"In the graph, {label} appears as {_join_labels(incoming_roles)}.")

    if not sentences:
        sentences.append(concept.description)

    return "\n\n".join(sentences)


def relation_card_headline(
    relation: RelationAnnotation,
    dataset: ViewerDataset,
    *,
    focal_concept_id: str,
) -> str:
    is_outgoing = relation.source_id == focal_concept_id
    other_concept_id = relation.target_id if is_outgoing else relation.source_id
    other_label = dataset.concept_index[other_concept_id].primary_label
    relation_label = relation.relation_type
    if is_outgoing:
        mapping = {
            "concerns": f"This concept concerns {other_label}.",
            "has_deficiency": f"Its deficiency is {other_label}.",
            "has_excess": f"Its excess is {other_label}.",
            "formed_by": f"It is formed by {other_label}.",
            "is_a": f"Aristotle treats it as {other_label}.",
            "requires": f"It requires {other_label}.",
            "determined_by": f"It is determined by {other_label}.",
            "relative_to": f"It is relative to {other_label}.",
            "opposed_to": f"It is opposed to {other_label}.",
            "contrasted_with": f"Book II contrasts it with {other_label}.",
        }
        return mapping.get(relation_label, f"It relates to {other_label} by {relation_label}.")
    mapping = {
        "concerns": f"It serves as the domain for {other_label}.",
        "has_deficiency": f"It appears here as the deficiency opposed to {other_label}.",
        "has_excess": f"It appears here as the excess opposed to {other_label}.",
        "formed_by": f"It helps form {other_label}.",
        "is_a": f"It is the broader class Aristotle uses for {other_label}.",
        "requires": f"{other_label} requires it.",
        "determined_by": f"It helps determine {other_label}.",
        "relative_to": f"{other_label} is treated as relative to it.",
        "opposed_to": f"{other_label} is opposed to it in Book II.",
        "contrasted_with": f"{other_label} is contrasted with it in Book II.",
    }
    return mapping.get(relation_label, f"{other_label} relates to it by {relation_label}.")


def relation_sentence(
    relation: RelationAnnotation,
    dataset: ViewerDataset,
) -> str:
    source_label = dataset.concept_index[relation.source_id].primary_label
    target_label = dataset.concept_index[relation.target_id].primary_label
    return f"{source_label} {relation.relation_type.replace('_', ' ')} {target_label}"


def selected_concept_context_markdown(
    concept: ConceptAnnotation | None,
    dataset: ViewerDataset,
) -> str:
    if concept is None:
        return (
            "Select a concept in the current view to see how it sits inside the larger Book II map."
        )
    return (
        f"**{concept.primary_label}**\n\n"
        f"{concept_role_line(concept, dataset)}"
    )


def relation_rows(
    relations: list[RelationAnnotation],
    dataset: ViewerDataset,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relation in relations:
        rows.append(
            {
                "relation_type": relation.relation_type,
                "source": dataset.concept_index[relation.source_id].primary_label,
                "target": dataset.concept_index[relation.target_id].primary_label,
                "assertion_tier": relation.assertion_tier,
                "evidence_passage_ids": ", ".join(
                    evidence.passage_id for evidence in relation.evidence
                ),
            }
        )
    return rows


def concept_summary_rows(
    concepts: list[ConceptAnnotation],
) -> list[dict[str, Any]]:
    return [
        {
            "label": concept.primary_label,
            "kind": concept.kind,
            "assertion_tier": concept.assertion_tier,
            "sections": ", ".join(str(section) for section in concept.sections),
        }
        for concept in concepts
    ]


def evidence_rows(
    concept: ConceptAnnotation,
    dataset: ViewerDataset,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for evidence in concept.evidence:
        passage = dataset.passage_index[evidence.passage_id]
        rows.append(
            {
                "citation": passage.citation_label,
                "passage_id": evidence.passage_id,
                "support_type": evidence.support_type,
                "note": evidence.note,
                "quote_excerpt": evidence.quote_excerpt or "",
            }
        )
    return rows


def passage_relation_rows(
    relations: tuple[RelationAnnotation, ...],
    dataset: ViewerDataset,
) -> list[dict[str, str]]:
    return [
        {
            "relation_type": relation.relation_type,
            "source": dataset.concept_index[relation.source_id].primary_label,
            "target": dataset.concept_index[relation.target_id].primary_label,
            "assertion_tier": relation.assertion_tier,
        }
        for relation in relations
    ]


def concept_detail_rows(concept: ConceptAnnotation) -> list[dict[str, str]]:
    return [
        {"field": "id", "value": concept.id},
        {"field": "kind", "value": concept.kind},
        {"field": "assertion tier", "value": concept.assertion_tier},
        {"field": "sections", "value": ", ".join(str(section) for section in concept.sections)},
        {"field": "source labels", "value": ", ".join(concept.source_labels)},
        {"field": "aliases", "value": ", ".join(concept.aliases) if concept.aliases else "None"},
    ]


def passage_preview(text: str, *, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def kind_legend_html(kinds: list[str]) -> str:
    chips = []
    for kind in kinds:
        chips.append(
            "<span class='avg-kind-chip'>"
            f"<span class='avg-kind-dot' style='background:{kind_color(kind)};'></span>"
            f"{escape(kind.replace('-', ' ').title())}</span>"
        )
    return "".join(chips)


def _inject_graph_click_bridge(html: str) -> str:
    if "avg-node-click" in html:
        return html
    marker = "return network;"
    if marker not in html:
        return html
    return html.replace(marker, f"{_GRAPH_CLICK_BRIDGE}\n\n                  {marker}", 1)


def edge_font_options(*, is_overall_map: bool) -> dict[str, Any]:
    return {
        "size": 9 if is_overall_map else 10,
        "align": "horizontal",
        "face": "Georgia, serif",
        "strokeWidth": 0,
        "color": "#223047",
        "background": "rgba(255, 250, 241, 0.96)",
        "vadjust": -12 if is_overall_map else -7,
    }


def build_graph_html(
    nodes: list[ConceptAnnotation],
    relations: list[RelationAnnotation],
    *,
    center_concept_id: str | None,
    highlight_concept_id: str | None = None,
    graph_mode: str = "ego",
    show_edge_labels: bool = True,
    height: str = "540px",
) -> str:
    try:
        from pyvis.network import Network
    except ModuleNotFoundError:
        return (
            "<div style='padding:1rem;border:1px solid #ddd;border-radius:8px;'>"
            "Install the viewer extra to render the graph view: "
            "<code>pip install -e \".[viewer]\"</code>."
            "</div>"
        )

    is_overall_map = graph_mode == "overall"
    network = Network(
        height=height,
        width="100%",
        directed=True,
        notebook=False,
        neighborhood_highlight=is_overall_map,
        select_menu=is_overall_map,
        filter_menu=is_overall_map,
        bgcolor="#fbf8f2" if is_overall_map else "#ffffff",
        font_color="#1f2f44",
        cdn_resources="in_line",
    )
    if is_overall_map:
        network.barnes_hut(
            gravity=-4200,
            central_gravity=0.22,
            spring_length=145,
            spring_strength=0.04,
            damping=0.2,
            overlap=0.15,
        )
    else:
        network.barnes_hut(
            gravity=-3000,
            central_gravity=0.26,
            spring_length=120,
            spring_strength=0.05,
            damping=0.18,
            overlap=0.1,
        )

    degree_counts: dict[str, int] = {}
    for relation in relations:
        degree_counts[relation.source_id] = degree_counts.get(relation.source_id, 0) + 1
        degree_counts[relation.target_id] = degree_counts.get(relation.target_id, 0) + 1
    max_degree = max(degree_counts.values(), default=1)
    emphasized_concept_id = highlight_concept_id or center_concept_id

    for concept in nodes:
        degree = degree_counts.get(concept.id, 0)
        degree_ratio = degree / max_degree if max_degree else 0
        size = 18 + (16 * degree_ratio)
        if concept.id == center_concept_id:
            size += 12
        elif concept.id == emphasized_concept_id:
            size += 7
        tooltip = escape(
            "\n".join(
                [
                    f"Label: {concept.primary_label}",
                    f"Kind: {concept.kind}",
                    f"Tier: {concept.assertion_tier}",
                    f"Degree: {degree}",
                    f"Sections: {', '.join(str(section) for section in concept.sections)}",
                    f"Evidence count: {len(concept.evidence)}",
                    f"Description: {concept.description}",
                ]
            )
        ).replace("\n", "<br>")
        network.add_node(
            concept.id,
            label=concept.primary_label,
            title=tooltip,
            group=concept.kind,
            color={
                "background": kind_color(concept.kind),
                "border": "#1f2f44" if concept.review_status == "approved" else "#c98b4a",
                "highlight": {
                    "background": kind_color(concept.kind),
                    "border": "#0b1824",
                },
            },
            size=size,
            borderWidth=(
                4
                if concept.id == center_concept_id
                else 2.5 if concept.id == emphasized_concept_id else 1.5
            ),
            borderWidthSelected=5,
            font={
                "face": "Georgia, serif",
                "size": 17 if is_overall_map else 15,
                "color": "#16324f",
                "strokeWidth": 4,
                "strokeColor": "#fbf8f2" if is_overall_map else "#ffffff",
            },
            mass=1 + degree_ratio,
        )

    for relation in relations:
        relation_label = relation.relation_type.replace("_", " ")
        tooltip = escape(
            "\n".join(
                [
                    f"Relation: {relation_label}",
                    f"Tier: {relation.assertion_tier}",
                    "Evidence: "
                    + ", ".join(evidence.passage_id for evidence in relation.evidence),
                ]
            )
        ).replace("\n", "<br>")
        network.add_edge(
            relation.source_id,
            relation.target_id,
            label=relation_label if show_edge_labels else "",
            title=tooltip,
            arrows="to",
            color=edge_color(relation.review_status),
            dashes=relation.review_status != "approved",
            width=2.4 if relation.review_status == "approved" else 1.8,
        )

    options = {
        "interaction": {
            "hover": True,
            "navigationButtons": True,
            "keyboard": {"enabled": True, "bindToWindow": False},
            "tooltipDelay": 110,
            "multiselect": is_overall_map,
            "selectConnectedEdges": False,
        },
        "layout": {"improvedLayout": True},
        "physics": {
            "stabilization": {
                "enabled": True,
                "iterations": 420 if is_overall_map else 220,
                "fit": True,
            },
        },
        "nodes": {
            "shape": "dot",
            "shadow": {"enabled": is_overall_map, "size": 10, "x": 0, "y": 3},
        },
        "edges": {
            "smooth": {
                "enabled": True,
                "type": "dynamic" if is_overall_map else "continuous",
                "roundness": 0.28 if is_overall_map else 0.18,
            },
            "font": edge_font_options(is_overall_map=is_overall_map),
            "labelHighlightBold": False,
            "widthConstraint": {"maximum": 64 if is_overall_map else 84},
        },
    }
    network.set_options(json.dumps(options))
    return _inject_graph_click_bridge(network.generate_html())
