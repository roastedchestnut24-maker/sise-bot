"""매실(또는 다른 품목) 한 철의 원자료를 통째로 모읍니다.

  python -m sise.maesil 2026-05            # 그 달 매일, 모든 시장의 매실 거래 원자료 → data/maesil/raw-2026-05.csv

품목 이름으로 걸러 달라고 API에 요청하고, 그 조건이 안 먹히면 하루치를 다 받아서 여기서 거릅니다.
"""
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from . import api

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "maesil"
MID = "매실"


def month_days(ym):
    y, m = map(int, ym.split("-"))
    d = date(y, m, 1)
    while d.month == m:
        yield d.strftime("%Y-%m-%d")
        d += timedelta(days=1)


def main():
    ym = sys.argv[1]
    mid = sys.argv[2] if len(sys.argv) > 2 else MID
    markets = json.loads((ROOT / "data" / "markets.json").read_text(encoding="utf-8"))
    use_filter = True
    rows, cols = [], []
    for day in month_days(ym):
        n0 = len(rows)
        for m in markets:
            base = {"cond[trd_clcln_ymd::EQ]": day, "cond[whsl_mrkt_cd::EQ]": m["code"]}
            got = None
            if use_filter:
                try:
                    got = api._paged(api.SALE_URL, {**base, "cond[gds_mclsf_nm::EQ]": mid})
                    if any((r.get("gds_mclsf_nm") or "").strip() != mid for r in got):
                        print("  (품목 조건이 적용되지 않아 하루치를 받아 거릅니다)", flush=True)
                        use_filter = False
                except api.ApiError as e:
                    print(f"  (품목 조건 없이 받습니다: {e})", flush=True)
                    use_filter = False
                    got = None
            if got is None or not use_filter:
                try:
                    got = got if got is not None else api._paged(api.SALE_URL, base)
                except api.ApiError as e:
                    print(f"  ! {m['name']} {day}: {e}", flush=True)
                    got = []
            for r in got:
                if (r.get("gds_mclsf_nm") or "").strip() == mid:
                    rows.append(r)
                    for k in r:
                        if k not in cols:
                            cols.append(k)
        print(f"- {day}: {mid} {len(rows) - n0}건", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"raw-{ym}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols or ["trd_clcln_ymd"])
        w.writeheader()
        w.writerows(rows)
    print(f"저장: {path} ({len(rows)}건)")


if __name__ == "__main__":
    main()
