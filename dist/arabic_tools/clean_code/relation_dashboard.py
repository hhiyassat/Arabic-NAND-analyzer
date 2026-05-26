"""relation_dashboard.py — جَلسة 21: dashboard مَرئيّ لِلـ RelationGraph.

يُولِّد ملفّ HTML قائِم بِذاته يَعرض RelationGraph لِنَصّ كَامِل.
يُستَخدِم D3.js force-directed graph (CDN) — لا dependencies مَحَلّيَّة.

الِاستخدام:
    python relation_dashboard.py "نَصّ..."
    python relation_dashboard.py 1:1
    python relation_dashboard.py --out /path/to/out.html "نَصّ..."

العَناصِر:
  • كُلّ EntityNode = دائِرَة بِلَون حَسَب word_class
  • كُلّ Relation = سَهم بِنَصّ يُبَيِّن اسم العَلاقَة
  • inter-clause relations = أَسهُم خاصَّة بَين clauses
  • ضَمائر مَع referent = أَسهُم مُتَقَطِّعَة
"""

from __future__ import annotations

import argparse
import json
import sys
import re
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from text_graph_assembler import TextGraphAssembler, TextGraph


CONTRACT_NAME = "RelationDashboard:v1"

# ---------------------------------------------------------------------------
# Ayah lookup (يَدعَم تَمرير 1:1 أَو نَصّ مُباشَر)
# ---------------------------------------------------------------------------

_AYAH_REF = re.compile(r"^\s*(\d+)\s*[:.\-]\s*(\d+)\s*$")


def _find_quran_path() -> Path | None:
    for p in [
        Path("/Users/husseinhiyassat/fractal/hussein/data/quran-uthmani-with-pause-mark.txt"),
        _HERE.parent / "data" / "quran-uthmani-with-pause-mark.txt",
        Path("/sessions/nice-epic-cannon/mnt/hussein/data/quran-uthmani-with-pause-mark.txt"),
    ]:
        if p.exists():
            return p
    return None


def _resolve(arg: str) -> tuple[str, str]:
    m = _AYAH_REF.match(arg)
    if m:
        s, a = m.group(1), m.group(2)
        path = _find_quran_path()
        if path and path.exists():
            prefix = f"{s}|{a}|"
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(prefix):
                        return line[len(prefix):].rstrip("\n"), f"quran:{s}:{a}"
        raise ValueError(f"لَم تُوجَد الآية {s}:{a}")
    return arg, "inline_text"


# ---------------------------------------------------------------------------
# Color map لِـ word_class
# ---------------------------------------------------------------------------

_WC_COLORS = {
    "FIIL": "#d97706",            # برتقاليّ — فِعل
    "ISM_MUARAB": "#2563eb",      # أَزرَق — اسم مُعرَب
    "ISM_MABNI": "#7c3aed",       # بَنَفسَجيّ — اسم مَبني
    "HARF": "#6b7280",            # رَماديّ — حَرف
    "AALAM": "#059669",           # أَخضَر — عَلَم
    "JAMID": "#0891b2",           # سَماويّ — جامِد
    "SINGULAR_TERM": "#dc2626",   # أَحمَر — لَفظ مُنفَرِد
    "JALALAH": "#dc2626",         # legacy
    "UNKNOWN": "#9ca3af",
}


# ---------------------------------------------------------------------------
# HTML generator
# ---------------------------------------------------------------------------

def render_dashboard(tg: TextGraph, source_label: str = "") -> str:
    """يُولِّد HTML قائِم بِذاتِه لِـ TextGraph."""
    # nodes + edges في JSON
    d3_nodes = []
    for nid, node in tg.nodes.items():
        d3_nodes.append({
            "id": nid,
            "surface": node.surface,
            "root": node.root,
            "wazn": node.wazn,
            "word_class": node.word_class,
            "role_phrase": node.role_phrase,
            "color": _WC_COLORS.get(node.word_class, _WC_COLORS["UNKNOWN"]),
            "is_singular_term": node.is_singular_term,
        })
    d3_links = []
    for r in tg.intra_relations:
        if r.target_id == "—":
            continue  # anchor-only edges تُعرَض كَ ring around node
        d3_links.append({
            "source": r.source_id,
            "target": r.target_id,
            "name": r.name,
            "kind_type": r.kind_type,
            "operator": r.operator,
            "source_of_claim": r.source_of_claim,
        })
    # pronoun references → dashed edges
    for pref in tg.pronoun_references:
        if pref.referent_token_idx and pref.host_token_idx:
            d3_links.append({
                "source": str(pref.host_token_idx),
                "target": str(pref.referent_token_idx),
                "name": f"ضَمير «{pref.clitic}»",
                "kind_type": "pronoun_ref",
                "operator": None,
                "source_of_claim": pref.source_of_claim,
                "dashed": True,
            })
    # inter-clause: نُمَثِّلها كَ box في الـ HTML أَسفَل الـ graph

    inter_html_rows = []
    for r in tg.inter_clause_relations:
        inter_html_rows.append(
            f"<tr><td>{r.name}</td><td>{r.kind_type}</td>"
            f"<td>«{r.trigger or ''}»</td>"
            f"<td>الجُملة {r.source_clause_idx} ← الجُملة {r.target_clause_idx}</td></tr>"
        )

    pronoun_html_rows = []
    for pref in tg.pronoun_references:
        ref_disp = pref.referent_surface or "—"
        pronoun_html_rows.append(
            f"<tr><td>«{pref.clitic}»</td><td>{pref.host_surface}</td>"
            f"<td>{ref_disp}</td><td>{pref.gender}/{pref.number}/{pref.person}</td></tr>"
        )

    clause_html_rows = []
    for i, c in enumerate(tg.clauses_text):
        clause_html_rows.append(f"<tr><td>{i}</td><td>{c}</td></tr>")

    data_json = json.dumps({"nodes": d3_nodes, "links": d3_links}, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>RelationGraph — {source_label or 'تَحليل نَصّ'}</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<style>
  body {{ font-family: -apple-system, "Segoe UI", "Tahoma", Arial, sans-serif;
         background: #fafafa; margin: 0; padding: 24px; }}
  h1 {{ color: #1f2937; font-size: 22px; margin: 0 0 8px; }}
  .subtitle {{ color: #6b7280; margin-bottom: 16px; font-size: 14px; }}
  .source {{ background: #fff; padding: 12px 18px; border-radius: 8px;
             border: 1px solid #e5e7eb; margin-bottom: 16px; font-size: 18px;
             line-height: 1.8; }}
  #graph {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
            margin-bottom: 18px; }}
  .node circle {{ stroke: #fff; stroke-width: 2px; cursor: pointer; }}
  .node text {{ fill: #111827; font-size: 13px; pointer-events: none; }}
  .link {{ stroke: #9ca3af; stroke-opacity: 0.7; fill: none; }}
  .link.dashed {{ stroke-dasharray: 4 3; stroke: #dc2626; }}
  .link-label {{ font-size: 11px; fill: #374151; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff;
           border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 16px; }}
  th, td {{ padding: 8px 12px; text-align: right; border-bottom: 1px solid #f3f4f6; }}
  th {{ background: #f9fafb; color: #374151; font-weight: 600; }}
  h2 {{ font-size: 16px; color: #374151; margin: 18px 0 8px; }}
  .legend {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; font-size: 12px; }}
  .legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
  .legend i {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
</style>
</head>
<body>

<h1>تَحليل العَلاقات (RelationGraph) — Phase C</h1>
<div class="subtitle">المَصدَر: {source_label or 'نَصّ مُباشَر'} · العَقد: {tg.contract}</div>

<div class="source">{tg.source_text}</div>

<div class="legend">
  <span><i style="background:#d97706"></i> فِعل (FIIL)</span>
  <span><i style="background:#2563eb"></i> اسم مُعرَب</span>
  <span><i style="background:#7c3aed"></i> اسم مَبني</span>
  <span><i style="background:#6b7280"></i> حَرف</span>
  <span><i style="background:#059669"></i> عَلَم</span>
  <span><i style="background:#0891b2"></i> جامِد</span>
  <span><i style="background:#dc2626"></i> لَفظ مُنفَرِد</span>
</div>

<svg id="graph" width="100%" height="500"></svg>

<h2>الجُمَل ({len(tg.clauses_text)})</h2>
<table>
  <tr><th style="width:60px">#</th><th>النَّصّ</th></tr>
  {''.join(clause_html_rows)}
</table>

<h2>عَلاقات بَين الجُمَل ({len(tg.inter_clause_relations)})</h2>
<table>
  <tr><th>الِاسم</th><th>النَّوع</th><th>المُحَفِّز</th><th>الِاتِّجاه</th></tr>
  {''.join(inter_html_rows) or '<tr><td colspan="4" style="color:#9ca3af">لا عَلاقات بَين الجُمَل</td></tr>'}
</table>

<h2>إِحالات الضَّمائر ({len(tg.pronoun_references)})</h2>
<table>
  <tr><th>الضَّمير</th><th>المُضيف</th><th>المُحَلّ</th><th>الجِنس/العَدد/الشَّخص</th></tr>
  {''.join(pronoun_html_rows) or '<tr><td colspan="4" style="color:#9ca3af">لا ضَمائر مُكتَشَفَة</td></tr>'}
</table>

<script>
const data = {data_json};

const width = document.getElementById('graph').clientWidth;
const height = 500;
const svg = d3.select("#graph");

const sim = d3.forceSimulation(data.nodes)
  .force("link", d3.forceLink(data.links).id(d => d.id).distance(110))
  .force("charge", d3.forceManyBody().strength(-380))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collide", d3.forceCollide(40));

// Arrow markers
svg.append("defs").selectAll("marker")
  .data(["end"])
  .enter().append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 28)
    .attr("refY", 0)
    .attr("markerWidth", 8)
    .attr("markerHeight", 8)
    .attr("orient", "auto")
  .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#9ca3af");

const link = svg.append("g")
  .selectAll("path")
  .data(data.links)
  .enter().append("path")
    .attr("class", d => "link" + (d.dashed ? " dashed" : ""))
    .attr("marker-end", "url(#arrow)");

const linkLabel = svg.append("g")
  .selectAll("text")
  .data(data.links)
  .enter().append("text")
    .attr("class", "link-label")
    .attr("text-anchor", "middle")
    .text(d => d.name);

const node = svg.append("g")
  .selectAll("g")
  .data(data.nodes)
  .enter().append("g")
    .attr("class", "node")
    .call(d3.drag()
      .on("start", (e, d) => {{ if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
      .on("drag",  (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
      .on("end",   (e, d) => {{ if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }}));

node.append("circle")
  .attr("r", 22)
  .attr("fill", d => d.color);

node.append("text")
  .attr("dy", 4)
  .attr("text-anchor", "middle")
  .text(d => d.surface);

node.append("title")
  .text(d => `${{d.surface}}\\n${{d.word_class}} · root=${{d.root}} · wazn=${{d.wazn}}\\nرول: ${{d.role_phrase}}`);

sim.on("tick", () => {{
  link.attr("d", d => {{
    const x1 = d.source.x, y1 = d.source.y, x2 = d.target.x, y2 = d.target.y;
    return `M${{x1}},${{y1}} L${{x2}},${{y2}}`;
  }});
  linkLabel
    .attr("x", d => (d.source.x + d.target.x) / 2)
    .attr("y", d => (d.source.y + d.target.y) / 2 - 4);
  node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
}});
</script>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="dashboard مَرئيّ لِلـ RelationGraph")
    ap.add_argument("input", help="نَصّ، أَو رَقم آية (1:1)")
    ap.add_argument("--out", default=None, help="مَسار ملفّ الـ HTML الخارِج")
    args = ap.parse_args()

    text, source_label = _resolve(args.input)
    asm = TextGraphAssembler()
    tg = asm.assemble(text)
    html = render_dashboard(tg, source_label=source_label)

    out = Path(args.out) if args.out else _HERE.parent / "outputs" / "relation_dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"كُتِبَ: {out}")
    print(f"  عُقَد: {len(tg.nodes)}  ·  عَلاقات: {len(tg.intra_relations)}  ·  "
          f"بَين الجُمَل: {len(tg.inter_clause_relations)}  ·  ضَمائر: {len(tg.pronoun_references)}")


if __name__ == "__main__":
    main()
