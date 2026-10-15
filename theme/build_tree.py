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
            .replace("/*REF*/[]", to_js(ref)))
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"{args.out} を作成（テーマ {len(items)} 件、参照 {len(ref)} 件）")


if __name__ == "__main__":
    main()
