"""
Phase 3 — Graph-Based Threat Mapping & PageRank Service.

Builds a heterogeneous knowledge graph of the threat landscape:

  Nodes:  Threats, ATT&CK Techniques, ATT&CK Groups, CVEs
  Edges:  threat→technique (mapping), technique→tactic (belongs),
          group→technique (uses), threat→CVE (has_cve)

Key capabilities:
* **PageRank** — identifies the most "connected" / critical threats
  and techniques in the assessment context.
* **Neighbourhood queries** — retrieve the N-hop neighbours of any node.
* **Path analysis** — find shortest attack paths between two nodes.
* **Centrality metrics** — degree, betweenness for prioritisation.
* **Serialisation** — export graph to JSON for frontend React-Flow rendering.

Uses ``networkx`` which is pure-Python and Lambda-friendly (~2 MB).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.models import (
    Assessment,
    AttackGroup,
    AttackTactic,
    AttackTechnique,
    Threat,
    ThreatAttackMapping,
)

logger = logging.getLogger(__name__)

# Node type constants
NT_THREAT = "threat"
NT_TECHNIQUE = "technique"
NT_TACTIC = "tactic"
NT_GROUP = "group"
NT_CVE = "cve"


class GraphService:
    """
    Builds and analyses a threat-intelligence knowledge graph.

    The graph is rebuilt per-request (or per-assessment) because the
    data set is modest (hundreds to low-thousands of nodes).  Caching
    the graph in-memory across requests would be a future optimisation.
    """

    def __init__(self) -> None:
        # Lazy import — networkx is not always available
        pass

    # ══════════════════════════════════════════════════════════════
    # GRAPH CONSTRUCTION
    # ══════════════════════════════════════════════════════════════

    def build_assessment_graph(
        self,
        db: Session,
        tenant_id: UUID,
        assessment_id: UUID,
    ) -> Dict[str, Any]:
        """
        Build a graph for a single assessment and return serialised JSON.

        Returns a dict with ``nodes``, ``edges``, ``pagerank``, and
        ``centrality`` sub-dicts ready for frontend consumption.
        """
        import networkx as nx  # type: ignore[import-untyped]

        G = nx.DiGraph()

        # ── Threats in this assessment ───────────────────────────
        threats = (
            db.query(Threat)
            .filter(Threat.assessment_id == assessment_id, Threat.tenant_id == tenant_id)
            .all()
        )
        if not threats:
            return {"nodes": [], "edges": [], "pagerank": {}, "centrality": {}, "stats": {}}

        threat_ids: Set[str] = set()
        technique_db_ids: Set[str] = set()

        for t in threats:
            tid = str(t.id)
            threat_ids.add(tid)
            G.add_node(
                tid,
                node_type=NT_THREAT,
                label=t.title,
                likelihood_score=int(t.likelihood_score or 0),  # type: ignore[arg-type]
                severity=t.severity,
                intel_enriched=bool(t.intel_enriched),
            )

            # CVE edges
            cve_ids = list(t.cve_ids or [])  # type: ignore[arg-type]
            for cve in cve_ids:
                cve_key = f"cve:{cve}"
                if not G.has_node(cve_key):
                    G.add_node(cve_key, node_type=NT_CVE, label=cve)
                G.add_edge(tid, cve_key, edge_type="has_cve")

        # ── ATT&CK Mappings ─────────────────────────────────────
        mappings = (
            db.query(ThreatAttackMapping, AttackTechnique)
            .join(AttackTechnique, ThreatAttackMapping.technique_id == AttackTechnique.id)
            .filter(ThreatAttackMapping.threat_id.in_([UUID(tid) for tid in threat_ids]))
            .all()
        )

        tactic_shortnames: Set[str] = set()

        for mapping, technique in mappings:
            tech_key = f"tech:{technique.mitre_id}"
            technique_db_ids.add(str(technique.id))

            if not G.has_node(tech_key):
                G.add_node(
                    tech_key,
                    node_type=NT_TECHNIQUE,
                    label=f"{technique.mitre_id} {technique.name}",
                    mitre_id=technique.mitre_id,
                    tactic=technique.tactic_shortname,
                    is_subtechnique=bool(technique.is_subtechnique),
                )

            G.add_edge(
                str(mapping.threat_id),
                tech_key,
                edge_type="uses_technique",
                confidence=int(mapping.confidence_score or 70),
            )

            # Technique → Tactic edge
            if technique.tactic_shortname:
                tac_key = f"tactic:{technique.tactic_shortname}"
                tactic_shortnames.add(str(technique.tactic_shortname))
                if not G.has_node(tac_key):
                    G.add_node(tac_key, node_type=NT_TACTIC, label=str(technique.tactic_shortname))
                G.add_edge(tech_key, tac_key, edge_type="belongs_to_tactic")

        # ── ATT&CK Groups that use these techniques ─────────────
        if technique_db_ids:
            tech_stix_ids: Dict[str, str] = {}
            tech_rows = (
                db.query(AttackTechnique.id, AttackTechnique.stix_id, AttackTechnique.mitre_id)
                .filter(AttackTechnique.id.in_([UUID(x) for x in technique_db_ids]))
                .all()
            )
            stix_to_mitre: Dict[str, str] = {}
            for tr in tech_rows:
                tech_stix_ids[str(tr.id)] = str(tr.stix_id)
                stix_to_mitre[str(tr.stix_id)] = str(tr.mitre_id)

            stix_id_set = set(tech_stix_ids.values())

            groups = db.query(AttackGroup).all()
            for group in groups:
                group_techniques = set(list(group.technique_ids or []))  # type: ignore[arg-type]
                shared = group_techniques & stix_id_set
                if shared:
                    grp_key = f"group:{group.name}"
                    if not G.has_node(grp_key):
                        G.add_node(
                            grp_key,
                            node_type=NT_GROUP,
                            label=group.name,
                            aliases=list(group.aliases or []),  # type: ignore[arg-type]
                        )
                    for stix_id in shared:
                        mitre_id = stix_to_mitre.get(stix_id)
                        if mitre_id:
                            tech_key = f"tech:{mitre_id}"
                            if G.has_node(tech_key):
                                G.add_edge(grp_key, tech_key, edge_type="uses_technique")

        # ── Compute analytics ────────────────────────────────────
        pagerank = nx.pagerank(G, alpha=0.85)
        try:
            betweenness = nx.betweenness_centrality(G)
        except Exception:
            betweenness = {}
        degree_cent = nx.degree_centrality(G)

        # ── Serialise ────────────────────────────────────────────
        nodes = []
        for node_id, data in G.nodes(data=True):
            nodes.append({
                "id": node_id,
                "type": data.get("node_type", "unknown"),
                "label": data.get("label", node_id),
                "pagerank": round(pagerank.get(node_id, 0), 6),
                "betweenness": round(betweenness.get(node_id, 0), 6),
                "degree": round(degree_cent.get(node_id, 0), 6),
                **{k: v for k, v in data.items() if k not in ("node_type", "label")},
            })

        edges = []
        for u, v, data in G.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "type": data.get("edge_type", "related"),
                **{k: v2 for k, v2 in data.items() if k != "edge_type"},
            })

        # Sort nodes by pagerank
        nodes.sort(key=lambda n: n["pagerank"], reverse=True)

        stats = {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "threat_count": len(threat_ids),
            "technique_count": sum(1 for n in nodes if n["type"] == NT_TECHNIQUE),
            "group_count": sum(1 for n in nodes if n["type"] == NT_GROUP),
            "cve_count": sum(1 for n in nodes if n["type"] == NT_CVE),
            "density": round(nx.density(G), 6),
            "is_connected": nx.is_weakly_connected(G) if G.number_of_nodes() > 0 else False,
        }

        return {
            "assessment_id": str(assessment_id),
            "nodes": nodes,
            "edges": edges,
            "pagerank": {k: round(v, 6) for k, v in sorted(pagerank.items(), key=lambda x: -x[1])[:20]},
            "stats": stats,
        }

    # ══════════════════════════════════════════════════════════════
    # NEIGHBOURHOOD QUERIES
    # ══════════════════════════════════════════════════════════════

    def threat_neighbourhood(
        self,
        db: Session,
        tenant_id: UUID,
        threat_id: UUID,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Return the N-hop neighbourhood around a single threat.
        """
        import networkx as nx  # type: ignore[import-untyped]

        threat = (
            db.query(Threat)
            .filter(Threat.id == threat_id, Threat.tenant_id == tenant_id)
            .first()
        )
        if not threat:
            return {"error": f"Threat {threat_id} not found"}

        # Build full assessment graph first
        full = self.build_assessment_graph(db, tenant_id, threat.assessment_id)  # type: ignore[arg-type]

        # Reconstruct networkx graph
        G = nx.DiGraph()
        for n in full["nodes"]:
            G.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
        for e in full["edges"]:
            G.add_edge(e["source"], e["target"], **{k: v for k, v in e.items() if k not in ("source", "target")})

        # BFS out from the threat node
        root = str(threat_id)
        if root not in G:
            return {"error": "Threat not in graph"}

        # Undirected neighbourhood
        ug = G.to_undirected()
        neighbourhood_nodes = set()
        try:
            subgraph_nodes = nx.single_source_shortest_path_length(ug, root, cutoff=depth)
            neighbourhood_nodes = set(subgraph_nodes.keys())
        except nx.NodeNotFound:
            neighbourhood_nodes = {root}

        # Filter nodes/edges
        nodes = [n for n in full["nodes"] if n["id"] in neighbourhood_nodes]
        edges = [e for e in full["edges"]
                 if e["source"] in neighbourhood_nodes and e["target"] in neighbourhood_nodes]

        return {
            "threat_id": str(threat_id),
            "depth": depth,
            "nodes": nodes,
            "edges": edges,
            "stats": {"node_count": len(nodes), "edge_count": len(edges)},
        }

    # ══════════════════════════════════════════════════════════════
    # PATH ANALYSIS
    # ══════════════════════════════════════════════════════════════

    def shortest_path(
        self,
        db: Session,
        tenant_id: UUID,
        assessment_id: UUID,
        source_node: str,
        target_node: str,
    ) -> Dict[str, Any]:
        """Find shortest path between two nodes in the assessment graph."""
        import networkx as nx  # type: ignore[import-untyped]

        full = self.build_assessment_graph(db, tenant_id, assessment_id)

        G = nx.DiGraph()
        for n in full["nodes"]:
            G.add_node(n["id"])
        for e in full["edges"]:
            G.add_edge(e["source"], e["target"])

        ug = G.to_undirected()

        try:
            path = nx.shortest_path(ug, source_node, target_node)
            path_nodes = [n for n in full["nodes"] if n["id"] in path]
            return {
                "path": path,
                "length": len(path) - 1,
                "nodes": path_nodes,
            }
        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            return {"error": str(e), "path": [], "length": -1}

    # ══════════════════════════════════════════════════════════════
    # CRITICAL NODE ANALYSIS
    # ══════════════════════════════════════════════════════════════

    def critical_nodes(
        self,
        db: Session,
        tenant_id: UUID,
        assessment_id: UUID,
        top_n: int = 10,
    ) -> Dict[str, Any]:
        """
        Identify the most critical nodes by combined PageRank + betweenness.
        """
        full = self.build_assessment_graph(db, tenant_id, assessment_id)
        if not full["nodes"]:
            return {"critical_nodes": [], "assessment_id": str(assessment_id)}

        # Composite score: 0.6 * normalised_pagerank + 0.4 * normalised_betweenness
        max_pr = max(n["pagerank"] for n in full["nodes"]) or 1
        max_bt = max(n["betweenness"] for n in full["nodes"]) or 1

        scored = []
        for n in full["nodes"]:
            norm_pr = n["pagerank"] / max_pr
            norm_bt = n["betweenness"] / max_bt
            composite = 0.6 * norm_pr + 0.4 * norm_bt
            scored.append({
                **n,
                "composite_score": round(composite, 4),
            })

        scored.sort(key=lambda x: x["composite_score"], reverse=True)

        return {
            "assessment_id": str(assessment_id),
            "critical_nodes": scored[:top_n],
            "total_nodes": len(scored),
        }
