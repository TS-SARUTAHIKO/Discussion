"""テーマ体系 YAML が手引きの規則を守っているかを確かめる。

使い方: python3 theme/check_theme.py theme/kenpo.yaml [ほかの YAML ...]
複数のファイルを渡すと、まとめて1つの体系として確かめる（科目をまたぐ親・関連のため）。
"""
import re
import sys

import yaml

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KEYS = {"id", "name", "kind", "parents", "aliases", "related", "memo"}


def load(paths):
    items = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            items.extend(yaml.safe_load(f) or [])
    return items


def check(items):
    errors = []
    by_id = {}
    for t in items:
        tid = t.get("id")
        if not tid or not ID_RE.match(tid):
            errors.append(f"ID の形が不正: {tid!r}")
        if tid in by_id:
            errors.append(f"ID が重複: {tid}")
        by_id[tid] = t
        if set(t) - KEYS:
            errors.append(f"{tid}: 未知のキー {sorted(set(t) - KEYS)}")
        if t.get("kind") not in ("structure", "issue"):
            errors.append(f"{tid}: kind が不正 {t.get('kind')!r}")

    names = {}
    for t in items:
        for n in [t.get("name")] + list(t.get("aliases") or []):
            if n in names and names[n] != t["id"]:
                errors.append(f"名前・エイリアスが重複: {n}（{names[n]} と {t['id']}）")
            names[n] = t["id"]

    for t in items:
        tid, parents = t["id"], t.get("parents") or []
        for p in parents:
            if p not in by_id:
                errors.append(f"{tid}: 親 {p} が存在しない")
        for r in t.get("related") or []:
            if r not in by_id:
                errors.append(f"{tid}: 関連 {r} が存在しない")
            elif r in parents:
                errors.append(f"{tid}: 関連 {r} は親でもある")
        if len(parents) != len(set(parents)):
            errors.append(f"{tid}: 親が重複")
        if t["kind"] == "structure":
            for p in parents:
                if p in by_id and by_id[p]["kind"] != "structure":
                    errors.append(f"{tid}: 構造エリアの親 {p} が論点になっている")
        else:
            if not parents:
                errors.append(f"{tid}: 論点に親がない")
            kinds = {by_id[p]["kind"] for p in parents if p in by_id}
            if kinds == {"issue"} and len(parents) > 1:
                errors.append(f"{tid}: 論点の第2・3段は親を1つだけ持つ")
            if len(kinds) > 1:
                errors.append(f"{tid}: 親に構造と論点が混ざっている")

    def issue_depth(tid, seen=()):
        t = by_id[tid]
        if tid in seen:
            errors.append(f"{tid}: 親子が循環している")
            return 0
        ps = [p for p in t.get("parents") or [] if p in by_id]
        if ps and by_id[ps[0]]["kind"] == "issue":
            return issue_depth(ps[0], seen + (tid,)) + 1
        return 1

    for t in items:
        if t["kind"] == "issue" and issue_depth(t["id"]) > 3:
            errors.append(f"{t['id']}: 論点エリアが3段を超えている")

    # 構造エリアの循環
    def walk(tid, stack):
        if tid in stack:
            errors.append(f"構造エリアが循環: {' > '.join(stack + [tid])}")
            return
        for p in by_id[tid].get("parents") or []:
            if p in by_id and by_id[p]["kind"] == "structure":
                walk(p, stack + [tid])

    for t in items:
        if t["kind"] == "structure":
            walk(t["id"], [])

    return errors


def main():
    items = load(sys.argv[1:])
    errors = sorted(set(check(items)))
    n_s = sum(t["kind"] == "structure" for t in items)
    multi = [t for t in items if len(t.get("parents") or []) > 1]
    print(f"テーマ {len(items)} 件（構造 {n_s}・論点 {len(items) - n_s}）、複数の親 {len(multi)} 件")
    for e in errors:
        print("NG:", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
