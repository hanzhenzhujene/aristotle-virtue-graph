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
    const graphChanged = frame.dataset.graphHash !== nextHash;
    if (graphChanged) {
        frame.srcdoc = data?.graphHtml ?? "";
        frame.dataset.graphHash = nextHash;
        frame.dataset.boundGraphHash = "";
    }

    const emitClickedConcept = (conceptId) => {
        setTriggerValue("clicked", {
            conceptId,
            token: Date.now(),
        });
    };

    const bindNetworkListeners = () => {
        let frameWindow = null;
        try {
            frameWindow = frame.contentWindow;
        } catch (error) {
            return false;
        }
        const network = frameWindow?.network;
        if (!network || typeof network.on !== "function") {
            return false;
        }
        if (network.__avgBoundGraphHash === nextHash) {
            return true;
        }

        const emitFromParams = (params) => {
            if (!params || !Array.isArray(params.nodes) || params.nodes.length === 0) {
                return;
            }
            const conceptId = String(params.nodes[0] ?? "");
            if (!conceptId) {
                return;
            }
            emitClickedConcept(conceptId);
        };

        network.on("click", emitFromParams);
        network.on("doubleClick", emitFromParams);
        network.on("selectNode", emitFromParams);
        network.on("hoverNode", () => {
            const container = network.canvas?.body?.container;
            if (container) {
                container.style.cursor = "pointer";
            }
        });
        network.on("blurNode", () => {
            const container = network.canvas?.body?.container;
            if (container) {
                container.style.cursor = "default";
            }
        });
        network.__avgBoundGraphHash = nextHash;
        frame.dataset.boundGraphHash = nextHash;
        return true;
    };

    const scheduleBinding = () => {
        let attempt = 0;
        const maxAttempts = 12;
        const tryBind = () => {
            if (bindNetworkListeners()) {
                return;
            }
            attempt += 1;
            if (attempt >= maxAttempts) {
                return;
            }
            window.setTimeout(tryBind, 80);
        };
        tryBind();
    };

    frame.onload = () => {
        frame.dataset.boundGraphHash = "";
        scheduleBinding();
    };

    if (!graphChanged && frame.dataset.boundGraphHash !== nextHash) {
        scheduleBinding();
    }
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
