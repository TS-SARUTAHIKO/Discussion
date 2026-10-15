"""テーマ体系 YAML から、樹形図で見る HTML を作る。

使い方: python3 theme/build_tree.py theme/kenpo.yaml theme/kenpo_tree.html
"""
import json
import sys
from pathlib import Path

import yaml


def main():
    src, out = sys.argv[1], sys.argv[2]
    items = yaml.safe_load(Path(src).read_text(encoding="utf-8")) or []
    template = (Path(__file__).parent / "tree_template.html").read_text(encoding="utf-8")
    data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    Path(out).write_text(template.replace("/*DATA*/[]", data), encoding="utf-8")
    print(f"{out} を作成（テーマ {len(items)} 件）")


if __name__ == "__main__":
    main()
