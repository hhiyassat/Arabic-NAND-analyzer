"""meaning_dashboard.py — Dashboard HTML لِـ MeaningGraph.

يُنتِج صَفحَة HTML تَفاعُليَّة تَعرِض الـ graph بِـ:
  • العُقَد كَ دَوائِر مُلَوَّنَة بِالـ ProofKind
  • الرَّوابِط كَ أَسهُم
  • التَّناقُضات بارِزَة بِالأَحمَر
  • إِحصاءات + entropy

CLI:
  python3 meaning_dashboard.py "نَصّ" -o out.html
  python3 meaning_dashboard.py --verse 1:5 -o out.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from meaning_assembler import MeaningAssembler
from meaning_graph import MeaningGraph

_HERE = Path(__file__).resolve().parent


HTML_TEMPLATE = """<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="UTF-8">
  <title>MeaningGraph — {title}</title>
  <style>
    body {{
      font-family: 'Amiri', 'Scheherazade', serif;
      background: #1e1e1e;
      color: #e8e8e8;
      padding: 20px;
      margin: 0;
    }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    h1 {{ color: #d4af37; border-bottom: 2px solid #d4af37; padding-bottom: 10px; }}
    .text-box {{
      background: #2d2d2d; padding: 15px; border-radius: 8px;
      margin: 10px 0; font-size: 1.4em; line-height: 2;
    }}
    .stats {{
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
      margin: 20px 0;
    }}
    .stat-card {{
      background: #2d2d2d; padding: 15px; border-radius: 8px;
      border-right: 4px solid #d4af37;
    }}
    .stat-label {{ color: #999; font-size: 0.9em; }}
    .stat-value {{ font-size: 2em; color: #d4af37; font-weight: bold; }}
    .stat-value.warn {{ color: #ff6b6b; }}
    .stat-value.ok {{ color: #51cf66; }}
    .layer {{
      background: #2d2d2d; padding: 15px; border-radius: 8px;
      margin: 15px 0;
    }}
    .layer h2 {{ color: #d4af37; margin-top: 0; }}
    .node, .edge {{
      background: #3a3a3a; padding: 8px 12px; border-radius: 6px;
      margin: 5px 0; display: inline-block; margin-right: 5px;
    }}
    .node.entity {{ border-right: 4px solid #74b9ff; }}
    .node.event {{ border-right: 4px solid #fdcb6e; }}
    .node.transformation {{ border-right: 4px solid #fd79a8; }}
    .node.construction {{ border-right: 4px solid #a29bfe; }}
    .proof-certificate {{ color: #51cf66; }}
    .proof-hypothesis {{ color: #ffd43b; }}
    .proof-zero {{ color: #ff6b6b; }}
    .edge-list {{ list-style: none; padding: 0; }}
    .edge-list li {{
      background: #3a3a3a; padding: 8px 12px; border-radius: 6px;
      margin: 4px 0;
    }}
    .contradiction {{
      background: #4a2727; padding: 12px; border-radius: 6px;
      border-right: 4px solid #ff6b6b; margin: 5px 0;
    }}
    code {{ background: #1a1a1a; padding: 2px 6px; border-radius: 4px; color: #74b9ff; }}
    .small {{ font-size: 0.85em; color: #999; }}
    details summary {{ cursor: pointer; padding: 5px; }}
  </style>
</head>
<body>
<div class="container">
  <h1>🧠 MeaningGraph — شَبَكَة المَعنى</h1>

  <div class="text-box" dir="rtl">{text}</div>

  <div class="stats">
    <div class="stat-card">
      <div class="stat-label">العُقَد (Nodes)</div>
      <div class="stat-value">{nodes}</div>
      <div class="small">{cert_nodes} Certificates ، {hyp_nodes} Hypotheses</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">الرَّوابِط (Edges)</div>
      <div class="stat-value">{edges}</div>
      <div class="small">{cert_edges} Certificates ، {hyp_edges} Hypotheses</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">التَّغطيَة</div>
      <div class="stat-value {cov_class}">{coverage}%</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">الـ Entropy (الغُموض)</div>
      <div class="stat-value {ent_class}">{entropy}</div>
      <div class="small">{consistency_text}</div>
    </div>
  </div>

  <div class="layer">
    <h2>📍 العُقَد ({nodes})</h2>
    {nodes_html}
  </div>

  <div class="layer">
    <h2>🔗 الرَّوابِط ({edges})</h2>
    <ul class="edge-list">
      {edges_html}
    </ul>
  </div>

  {contradictions_section}

  <div class="layer">
    <h2>📦 JSON الكامِل</h2>
    <details>
      <summary>عَرض الـ JSON</summary>
      <pre>{full_json}</pre>
    </details>
  </div>

  <div class="small" style="margin-top: 30px; text-align: center;">
    مَعمار المَعنى العَرَبيّ — Phase F (MeaningGraph) | MC v2 Compliant
  </div>
</div>
</body>
</html>
"""


def render_node_html(n) -> str:
    """يَعرِض node كَ HTML."""
    sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}.get(n.proof_kind, "·")
    cls = f"node {n.node_type}"
    proof_cls = f"proof-{n.proof_kind.lower()}"
    return (
        f'<div class="{cls}">'
        f'<span class="{proof_cls}">{sym}</span> '
        f'<b>{n.surface}</b> '
        f'<code>{n.node_type}</code> '
        f'<span class="small">[{n.node_id}]</span>'
        f'</div>'
    )


def render_edge_html(e) -> str:
    sym = {"Certificate": "✓", "Hypothesis": "?", "Zero": "✗"}.get(e.proof_kind, "·")
    proof_cls = f"proof-{e.proof_kind.lower()}"
    op = f' <code>{e.operator}</code>' if e.operator else ""
    blockers_str = ""
    if e.blockers:
        blockers_str = f' <span class="small">⚠ {"; ".join(e.blockers)}</span>'
    return (
        f'<li>'
        f'<span class="{proof_cls}">{sym}</span> '
        f'<code>{e.edge_type}</code>{op} : '
        f'<b>{e.source}</b> → <b>{e.target}</b>'
        f'{blockers_str}'
        f'</li>'
    )


def render_dashboard(graph: MeaningGraph) -> str:
    s = graph.stats()
    nodes_html = "".join(render_node_html(n) for n in graph.nodes) or "<i>لا عُقَد</i>"
    edges_html = "".join(render_edge_html(e) for e in graph.edges) or "<li><i>لا رَوابِط</i></li>"

    cov = s["coverage_pct"]
    cov_class = "ok" if cov >= 80 else ("warn" if cov < 50 else "")
    ent = s["entropy"]
    ent_class = "ok" if ent == 0 else ("warn" if ent > 3 else "")
    cons = "✅ مُتَّسِق" if s["is_consistent"] else f"⚠ {s['contradictions']} تَناقُضات"

    contradictions_section = ""
    if graph.contradictions:
        cont_html = "".join(
            f'<div class="contradiction">'
            f'<b>[{c.severity}]</b> {c.description}'
            f'</div>'
            for c in graph.contradictions
        )
        contradictions_section = f'<div class="layer"><h2>⚠ التَّناقُضات</h2>{cont_html}</div>'

    return HTML_TEMPLATE.format(
        title=graph.text[:50],
        text=graph.text,
        nodes=s["nodes"],
        edges=s["edges"],
        cert_nodes=s["certificate_nodes"],
        hyp_nodes=s["hypothesis_nodes"],
        cert_edges=s["certificate_edges"],
        hyp_edges=s["hypothesis_edges"],
        coverage=cov,
        cov_class=cov_class,
        entropy=ent,
        ent_class=ent_class,
        consistency_text=cons,
        nodes_html=nodes_html,
        edges_html=edges_html,
        contradictions_section=contradictions_section,
        full_json=json.dumps(graph.to_dict(), ensure_ascii=False, indent=2),
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("text", nargs="?")
    p.add_argument("--verse", help="آيَة (سُورة:آية)")
    p.add_argument("-o", "--output", default="meaning_dashboard.html")
    args = p.parse_args()

    if args.verse:
        verses_path = _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt"
        surah, ayah = args.verse.split(":")
        text = None
        with open(verses_path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 3 and parts[0] == str(int(surah)) and parts[1] == str(int(ayah)):
                    text = parts[2]
                    break
        if not text:
            print(f"⚠ لَم نَجِد {args.verse}")
            sys.exit(1)
    elif args.text:
        text = args.text
    else:
        p.print_help()
        sys.exit(1)

    ma = MeaningAssembler()
    graph = ma.assemble(text)
    html = render_dashboard(graph)
    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    print(f"✓ Dashboard مَحفوظ في {out.resolve()}")
    print(f"  العُقَد: {graph.total_nodes} | الرَّوابِط: {graph.total_edges}")


if __name__ == "__main__":
    main()
