"""Build two BLIND labeling sets from output/filter_results.csv (run run_filter.py first).

Usage: .venv/bin/python make_sheets.py

Set A (audit), drawn in this order, never choosing a posting twice:
  30 random REJECTED; 5 random KEPT (if fewer than 5 exist, all of them, and the shortfall
  is printed); 5 random close calls (close_call true: score 4 or 5, no exclusion,
  description present). KEPT is drawn before close calls (decision 2026-11-25, when the
  v1 filter kept only 4 postings) so no KEPT posting is lost to the close-call draw.
Set B (held-out): 30 random postings from all postings not in set A.

Every draw uses one random.Random(SEED) over pools sorted by (provider, board, id), so the
sets do not depend on file order. Rows are then shuffled so the sheet order does not reveal
why a row was sampled. Key files hold why_sampled but no filter decision, score or rules;
label files hold blank verdicts. An existing label file with any verdict is never overwritten.
"""

import csv
import random

from src import config as cfg

KEY_COLUMNS = ["id", "provider", "board", "why_sampled"]
LABEL_COLUMNS = ["id", "provider", "my_verdict", "my_reason"]


def _key(row) -> tuple[str, str, str]:
    return (row["provider"], row["board"], row["id"])


def _draw(rng, pool, n, chosen, why, label, allow_short=False):
    candidates = sorted((r for r in pool if _key(r) not in chosen), key=_key)
    if len(candidates) < n:
        if not allow_short:
            raise ValueError(f"{label}: need {n}, only {len(candidates)} available")
        n = len(candidates)
    picked = rng.sample(candidates, n)
    for r in picked:
        chosen.add(_key(r))
    return [(r, why) for r in picked]


def build_sets(rows, seed=cfg.SEED):
    """rows: dicts with provider, board, id, decision, close_call. Returns (set_a, set_b),
    each a list of key rows {id, provider, board, why_sampled}."""
    rng = random.Random(seed)
    chosen: set = set()
    rejected = [r for r in rows if r["decision"] == cfg.REJECTED]
    close = [r for r in rows if r["close_call"] == "true"]
    kept = [r for r in rows if r["decision"] == cfg.KEPT]

    set_a = (_draw(rng, rejected, cfg.SET_A_REJECTED, chosen, "random_rejected", "set A rejected")
             + _draw(rng, kept, cfg.SET_A_KEPT, chosen, "random_kept", "set A kept", allow_short=True)
             + _draw(rng, close, cfg.SET_A_CLOSE_CALLS, chosen, "close_call", "set A close calls"))
    set_b = _draw(rng, rows, cfg.SET_B_SIZE, chosen, "random_all_not_in_A", "set B")
    rng.shuffle(set_a)
    rng.shuffle(set_b)

    def as_key(pairs):
        return [{"id": r["id"], "provider": r["provider"], "board": r["board"], "why_sampled": why}
                for r, why in pairs]
    return as_key(set_a), as_key(set_b)


def _has_verdicts(path) -> bool:
    if not path.exists():
        return False
    with open(path, newline="", encoding="utf-8") as f:
        return any((row.get("my_verdict") or "").strip() for row in csv.DictReader(f))


def _write(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    results = cfg.PROJECT_ROOT / cfg.RESULTS_CSV
    if not results.exists():
        print(f"{cfg.RESULTS_CSV} not found; run run_filter.py first")
        return 1
    with open(results, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    labels_dir = cfg.PROJECT_ROOT / cfg.LABELS_DIR
    labels_dir.mkdir(exist_ok=True)
    sets = dict(zip("AB", build_sets(rows)))
    for name in sets:
        if _has_verdicts(labels_dir / f"set_{name}_labels.csv"):
            print(f"labels/set_{name}_labels.csv already has verdicts; not overwriting anything")
            return 1
    for name, key_rows in sets.items():
        _write(labels_dir / f"set_{name}_key.csv", KEY_COLUMNS, key_rows)
        _write(labels_dir / f"set_{name}_labels.csv", LABEL_COLUMNS,
               [{"id": r["id"], "provider": r["provider"], "my_verdict": "", "my_reason": ""}
                for r in key_rows])
        why = {}
        for r in key_rows:
            why[r["why_sampled"]] = why.get(r["why_sampled"], 0) + 1
        print(f"set {name}: {len(key_rows)} rows {why} -> labels/set_{name}_key.csv, labels/set_{name}_labels.csv")
    n_kept = sum(r["why_sampled"] == "random_kept" for r in sets["A"])
    if n_kept < cfg.SET_A_KEPT:
        print(f"shortfall: set A wanted {cfg.SET_A_KEPT} KEPT, only {n_kept} KEPT postings exist (all taken)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
