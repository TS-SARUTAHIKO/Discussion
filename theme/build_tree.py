"""テーマ体系 YAML から、樹形図で見る HTML を作る。

使い方:
  python3 theme/build_tree.py theme/keiho.yaml theme/keiho_tree.html --ref theme/kenpo.yaml

--ref に渡した YAML（ほかの科目）は樹形図には出さず、関連の名前を表示するためだけに使う。
ページの題名は「<最上位のテーマの名前>テーマ樹形図」になる。
"""
import argparse
import json
from pathlib import Path

import yaml


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


def root_name(items):
    return next(t["name"] for t in items if not t.get("parents"))


def to_js(items):
    return json.dumps(items, ensure_ascii=False).replace("</", "<\\/")


def flow_html(items):
    """next（次の段階）があれば、手続の流れ図（Mermaid）を作る。なければ空文字。"""
    by_id = {t["id"]: t for t in items}
    edges = [(t["id"], n) for t in items for n in t.get("next") or []]
    if not edges:
        return ""
    root = next(t["id"] for t in items if not t.get("parents"))
    top = {t["id"] for t in items if root in (t.get("parents") or [])}
    big = [(a, b) for a, b in edges if a in top and b in top]
    small = [(a, b) for a, b in edges if (a, b) not in big]
    nid = {tid: f"n{i}" for i, tid in enumerate(by_id)}

    def top_of(tid):
        # 最初の親をたどって、大きな段階（最上位の直下）を探す
        seen = set()
        while tid not in top and tid not in seen:
            seen.add(tid)
            ps = by_id[tid].get("parents") or []
            if not ps:
                break
            tid = ps[0]
        return tid

    def node(tid):
        return f'{nid[tid]}["{by_id[tid]["name"]}"]'

    def diagram(es, group):
        lines = ["flowchart TD"]
        if group:
            # 細かい段階は、それが属する大きな段階ごとにまとめる
            groups = {}
            loose = []
            for tid in dict.fromkeys(x for e in es for x in e):
                owner = top_of(tid)
                if owner == tid:
                    loose.append(tid)
                else:
                    groups.setdefault(owner, []).append(tid)
            lines += [f"  {node(m)}" for m in loose]
            for owner, members in groups.items():
                lines.append(f'  subgraph g{nid[owner]}["{by_id[owner]["name"]}"]')
                lines += [f"    {node(m)}" for m in members]
                lines.append("  end")
        lines += [f"  {node(a)} --> {node(b)}" for a, b in es]
        return '<div class="flow-box"><pre class="mermaid">\n' + "\n".join(lines) + "\n</pre></div>"

    parts = ['<details class="flow" open><summary>手続の流れ</summary>',
             "<p>next（次の段階）でつないだ構造エリアの流れ。タグ付けと集計は下の樹形図（親子関係）で行う。</p>"]
    if big:
        parts += ["<h3>大きな流れ</h3>", diagram(big, False)]
    if small:
        parts += ["<h3>細かい流れ</h3>", diagram(small, True)]
    parts.append("</details>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--ref", nargs="*", default=[])
    args = ap.parse_args()

    items = load(args.src)
    ref = []
    for path in args.ref:
        other = load(path)
        label = root_name(other)
        ref += [{"id": t["id"], "name": t["name"], "related": t.get("related") or [], "_from": label} for t in other]

    template = (Path(__file__).parent / "tree_template.html").read_text(encoding="utf-8")
    html = (template.replace("__TITLE__", f"{root_name(items)}テーマ樹形図")
            .replace("/*DATA*/[]", to_js(items))
            .replace("/*REF*/[]", to_js(ref))
            .replace("<!--FLOW-->", flow_html(items)))
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"{args.out} を作成（テーマ {len(items)} 件、参照 {len(ref)} 件）")


if __name__ == "__main__":
    main()
