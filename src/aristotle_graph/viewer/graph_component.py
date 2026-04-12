from __future__ import annotations

import importlib
from functools import cache
from hashlib import sha1
from typing import Any

_COMPONENT_HTML = "<div id='avg-graph-component-root'></div>"

_COMPONENT_CSS = """
:host {
    display: block;
    width: 100%;
}

#avg-graph-component-root {
    width: 100%;
}

.avg-graph-frame {
    width: 100%;
    border: none;
    border-radius: 16px;
    background: transparent;
}
"""

_COMPONENT_JS = """
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    let root = parentElement.querySelector("#avg-graph-component-root");
    if (!root) {
        root = document.createElement("div");
        root.id = "avg-graph-component-root";
        parentElement.appendChild(root);
    }

    let frame = root.querySelector("iframe");
    if (!frame) {
        frame = document.createElement("iframe");
        frame.className = "avg-graph-frame";
        frame.setAttribute("sandbox", "allow-scripts allow-same-origin");
        root.appendChild(frame);
    }

    frame.style.height = data?.height ?? "560px";
    const nextHash = String(data?.graphHash ?? "");
    if (frame.dataset.graphHash !== nextHash) {
        frame.srcdoc = data?.graphHtml ?? "";
        frame.dataset.graphHash = nextHash;
    }

    const handleMessage = (event) => {
        if (event.source !== frame.contentWindow) {
            return;
        }
        const payload = event.data;
        if (!payload || payload.type !== "avg-node-click") {
            return;
        }
        if (typeof payload.conceptId !== "string" || !payload.conceptId) {
            return;
        }
        setTriggerValue("clicked", {
            conceptId: payload.conceptId,
            token: Date.now(),
        });
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
}
"""


@cache
def _graph_component() -> Any:
    components = importlib.import_module("streamlit.components.v2")
    return components.component(
        "avg_clickable_graph",
        html=_COMPONENT_HTML,
        css=_COMPONENT_CSS,
        js=_COMPONENT_JS,
        isolate_styles=False,
    )


def render_clickable_graph(
    *,
    graph_html: str,
    height: str,
    key: str,
) -> str | None:
    graph_hash = sha1(graph_html.encode("utf-8")).hexdigest()
    result = _graph_component()(
        key=key,
        data={
            "graphHtml": graph_html,
            "graphHash": graph_hash,
            "height": height,
        },
        default={"clicked": None},
        on_clicked_change=lambda: None,
    )
    clicked = getattr(result, "clicked", None)
    if isinstance(clicked, dict):
        concept_id = clicked.get("conceptId")
        if isinstance(concept_id, str) and concept_id:
            return concept_id
    if not isinstance(clicked, str) or not clicked:
        return None
    return clicked
