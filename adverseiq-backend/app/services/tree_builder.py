import logging
from typing import Any

logger = logging.getLogger(__name__)

# Node and edge type constants
NODE_PATIENT = "patientNode"
NODE_HYPOTHESIS = "hypothesisNode"
NODE_MECHANISM = "mechanismNode"
NODE_REJECTED = "rejectedNode"


def _confidence_color(confidence: float, status: str) -> str:
    if status == "rejected":
        return "#6B7280"  # gray-500
    if confidence >= 70:
        return "#16A34A"  # green-600
    if confidence >= 40:
        return "#D97706"  # amber-600
    return "#6B7280"  # gray-500


class TreeBuilder:
    def build(self, hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Convert K2 hypothesis array into React Flow nodes and edges.
        Returns {"nodes": [...], "edges": [...], "pruned_hypotheses": [...]}.
        """
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        if not hypotheses:
            return {"nodes": [], "edges": [], "pruned_hypotheses": []}

        # Root patient node — centered at top
        root_id = "patient-root"
        nodes.append(
            {
                "id": root_id,
                "type": NODE_PATIENT,
                "data": {"label": "Patient Case"},
                "position": {"x": 0, "y": 0},
            }
        )

        # Layout: spread hypotheses horizontally
        # Pruning: skip confidence < 15
        visible = [h for h in hypotheses if h.get("confidence", 0) >= 15]
        pruned = [h for h in hypotheses if h.get("confidence", 0) < 15]

        total_width = len(visible) * 280
        start_x = -(total_width / 2) + 140  # center around root

        for i, hyp in enumerate(visible):
            hyp_id = hyp.get("id", f"H{i+1}")
            confidence = float(hyp.get("confidence", 0))
            status = hyp.get("status", "possible")

            color = _confidence_color(confidence, status)
            x = start_x + i * 280
            y = 200  # hypothesis row

            # Hypothesis node
            node_type = NODE_REJECTED if status == "rejected" else NODE_HYPOTHESIS
            nodes.append(
                {
                    "id": hyp_id,
                    "type": node_type,
                    "data": {
                        "label": hyp_id,
                        "confidence": confidence,
                        "description": hyp.get("description", ""),
                        "mechanism": hyp.get("mechanism", ""),
                        "status": status,
                        "color": color,
                        "evidence_source": hyp.get("evidence_source", "mechanism"),
                        "supporting_evidence": hyp.get("supporting_evidence", []),
                        "rejecting_evidence": hyp.get("rejecting_evidence", []),
                    },
                    "position": {"x": x, "y": y},
                }
            )

            # Edge from root to hypothesis
            edge_style: dict[str, Any] = {}
            animated = status in ("supported", "possible")

            if status == "rejected":
                edge_style = {"stroke": "#6B7280", "strokeDasharray": "5,5"}
                animated = False
            elif status == "supported":
                edge_style = {"stroke": color, "strokeWidth": 2}

            edges.append(
                {
                    "id": f"e-root-{hyp_id}",
                    "source": root_id,
                    "target": hyp_id,
                    "animated": animated,
                    "style": edge_style,
                }
            )

            # Mechanism node — only for non-rejected hypotheses
            if status != "rejected" and hyp.get("mechanism"):
                mech_id = f"mech-{hyp_id}"

                nodes.append(
                    {
                        "id": mech_id,
                        "type": NODE_MECHANISM,
                        "data": {
                            "label": "Mechanism",
                            "mechanism": hyp.get("mechanism", ""),
                            "source": hyp.get("evidence_source", "mechanism"),
                        },
                        "position": {"x": x, "y": y + 180},
                    }
                )

                edges.append(
                    {
                        "id": f"e-{hyp_id}-{mech_id}",
                        "source": hyp_id,
                        "target": mech_id,
                        "animated": False,
                        "style": {
                            "stroke": "#60A5FA",  # blue-400
                            "strokeDasharray": "4,4",
                        },
                    }
                )

        return {
            "nodes": nodes,
            "edges": edges,
            "pruned_hypotheses": pruned,
        }


tree_builder = TreeBuilder()