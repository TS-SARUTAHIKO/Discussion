"""テーマ体系 YAML が手引きの規則を守っているかを確かめる。

使い方: python3 theme/check_theme.py theme/kenpo.yaml [ほかの YAML ...]
複数のファイルを渡すと、まとめて1つの体系として確かめる（科目をまたぐ親・関連のため）。

- kind: theory（学説）は論点の子として1段使うが、論点の「最大3段」には数えない。親は論点1つだけで、学説の下に子は置かない
- ref の行（ref と parents だけ）は、ほかの科目のテーマをこの科目の構造にも目印付きで出すための参照。テーマの数には入れない
- old_law（改正の年）は、法改正で変わった古い制度のテーマに付ける目印
"""
import re
import sys

import yaml

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KEYS = {"id", "name", "kind", "parents", "aliases", "related", "next", "old_law", "memo"}
REF_KEYS = {"ref", "parents", "memo"}


def load(paths):
    """テーマと ref の行を分けて読む。どちらにも、どのファイルから来たかを _file で付ける。"""
    items, refs = [], []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for t in yaml.safe_load(f) or []:
                (refs if "ref" in t else items).append({**t, "_file": path})
    return items, refs


def check(items, refs=()):
    errors = []
    by_id = {}
    for t in items:
        t = {k: v for k, v in t.items() if k != "_file"}
        tid = t.get("id")
        if not tid or not ID_RE.match(tid):
            errors.append(f"ID の形が不正: {tid!r}")
        if tid in by_id:
            errors.append(f"ID が重複: {tid}")
        by_id[tid] = t
        if set(t) - KEYS:
            errors.append(f"{tid}: 未知のキー {sorted(set(t) - KEYS)}")
        if t.get("kind") not in ("structure", "issue", "theory"):
            errors.append(f"{tid}: kind が不正 {t.get('kind')!r}")
        if "old_law" in t and not (isinstance(t["old_law"], int) and 1868 <= t["old_law"] <= 2100):
            errors.append(f"{tid}: old_law は改正の年（整数）で書く")
    by_id = {t["id"]: t for t in items if t.get("id")}

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
        for n in t.get("next") or []:
            if n not in by_id:
                errors.append(f"{tid}: 次の段階 {n} が存在しない")
            elif n == tid:
                errors.append(f"{tid}: 次の段階が自分自身")
            elif t["kind"] != "structure" or by_id[n]["kind"] != "structure":
                errors.append(f"{tid}: 次の段階（next）は構造エリアどうしだけに張る")
        if len(parents) != len(set(parents)):
            errors.append(f"{tid}: 親が重複")
        if t["kind"] == "structure":
            for p in parents:
                if p in by_id and by_id[p]["kind"] != "structure":
                    errors.append(f"{tid}: 構造エリアの親 {p} が論点になっている")
        elif t["kind"] == "theory":
            if len(parents) != 1 or (parents[0] in by_id and by_id[parents[0]]["kind"] != "issue"):
                errors.append(f"{tid}: 学説の親は論点1つだけ")
        else:
            if not parents:
                errors.append(f"{tid}: 論点に親がない")
            kinds = {by_id[p]["kind"] for p in parents if p in by_id}
            if kinds == {"issue"} and len(parents) > 1:
                errors.append(f"{tid}: 論点の第2・3段は親を1つだけ持つ")
            if len(kinds) > 1:
                errors.append(f"{tid}: 親に構造と論点が混ざっている")
            if "theory" in kinds:
                errors.append(f"{tid}: 学説の下に子を置かない")

    def issue_depth(tid, seen=()):
        t = by_id[tid]
        if t["kind"] == "theory":
            return 0
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

    # ref の行（ほかの科目のテーマを、この科目の構造にも出す）
    seen_refs = set()
    for r in refs:
        rid, parents = r["ref"], r.get("parents") or []
        if set(r) - REF_KEYS - {"_file"}:
            errors.append(f"ref {rid}: 未知のキー {sorted(set(r) - REF_KEYS - {'_file'})}")
        if rid not in by_id:
            errors.append(f"ref {rid}: 参照先が存在しない")
            continue
        if by_id[rid]["_file"] == r["_file"]:
            errors.append(f"ref {rid}: 同じ科目のテーマは参照にしない（親を足す）")
        if by_id[rid]["kind"] == "theory":
            errors.append(f"ref {rid}: 学説は参照にしない")
        if not parents:
            errors.append(f"ref {rid}: 親がない")
        for p in parents:
            if p not in by_id:
                errors.append(f"ref {rid}: 親 {p} が存在しない")
            elif by_id[p]["kind"] != "structure" or by_id[p]["_file"] != r["_file"]:
                errors.append(f"ref {rid}: 親 {p} は同じファイルの構造エリアにする")
        if (rid, r["_file"]) in seen_refs:
            errors.append(f"ref {rid}: 同じファイルで重複")
        seen_refs.add((rid, r["_file"]))

    return errors


def main():
    items, refs = load(sys.argv[1:])
    errors = sorted(set(check(items, refs)))
    count = {k: sum(t.get("kind") == k for t in items) for k in ("structure", "issue", "theory")}
    multi = [t for t in items if len(t.get("parents") or []) > 1]
    print(f"テーマ {len(items)} 件（構造 {count['structure']}・論点 {count['issue']}・学説 {count['theory']}）、"
          f"複数の親 {len(multi)} 件、参照 {len(refs)} 件")
    for e in errors:
        print("NG:", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
