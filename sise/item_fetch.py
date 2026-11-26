"""한 품목의 정산 원자료를 기간으로 모읍니다 (예: 매실 5~7월).

  python -m sise.item_fetch 매실 2026-05-01 2026-07-31

결과: data/items/<품목>.csv  (거래 한 줄 = 시장·법인·품종·등급·크기·포장·물량·금액)
"""
import csv
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from . import api

ROOT = Path(__file__).resolve().parent.parent
COLS = ["trd_clcln_ymd", "whsl_mrkt_nm", "corp_nm", "gds_mclsf_cd", "gds_mclsf_nm", "gds_sclsf_nm", "grd_nm", "sz_nm",
        "unit_qty", "unit_nm", "unit_tot_qty", "totprc", "avgprc", "lwprc", "hgprc", "plor_nm"]


def _try(params, cols):
    try:
        return api._paged(api.SALE_URL, {**params, "selectable": ",".join(cols)})
    except api.ApiError as e:
        return e


def find_code(name, markets):
    """품목 중분류 코드를 찾습니다: 제철 날짜의 큰 시장 자료에서 이름으로 찾아요."""
    for day in ["2026-06-10", "2026-06-17", "2025-06-11"]:
        for m in markets[:6]:
            rows = _try({"cond[trd_clcln_ymd::EQ]": day, "cond[whsl_mrkt_cd::EQ]": m["code"]},
                        ["gds_mclsf_cd", "gds_mclsf_nm"])
            if isinstance(rows, Exception):
                print("  !", e_msg(rows))
                continue
            for r in rows:
                if (r.get("gds_mclsf_nm") or "").strip() == name:
                    return r.get("gds_mclsf_cd")
    return None


def e_msg(e):
    return str(e)[:160]


def main():
    name, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
    markets = api.markets(start)
    code = find_code(name, markets)
    print(f"{name} 코드: {code}", flush=True)
    if not code:
        sys.exit("품목 코드를 찾지 못했어요.")
    d0 = datetime.strptime(start, "%Y-%m-%d").date()
    d1 = datetime.strptime(end, "%Y-%m-%d").date()
    days = [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]
    cols = list(COLS)
    probe = _try({"cond[trd_clcln_ymd::EQ]": days[len(days) // 2], "cond[whsl_mrkt_cd::EQ]": markets[0]["code"],
                  "cond[gds_mclsf_cd::EQ]": code}, cols)
    for extra in ["plor_nm", "corp_nm", "sz_nm"]:
        if isinstance(probe, Exception) and extra in cols:
            cols.remove(extra)
            probe = _try({"cond[trd_clcln_ymd::EQ]": days[len(days) // 2], "cond[whsl_mrkt_cd::EQ]": markets[0]["code"],
                          "cond[gds_mclsf_cd::EQ]": code}, cols)
    if isinstance(probe, Exception):
        sys.exit(f"조회 실패: {e_msg(probe)}")
    print("받을 항목:", ",".join(cols), flush=True)

    jobs = [(d, m) for d in days for m in markets]

    def one(job):
        d, m = job
        r = _try({"cond[trd_clcln_ymd::EQ]": d, "cond[whsl_mrkt_cd::EQ]": m["code"], "cond[gds_mclsf_cd::EQ]": code}, cols)
        return [] if isinstance(r, Exception) else r

    out = ROOT / "data" / "items" / f"{name}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", newline="", encoding="utf-8-sig") as f, ThreadPoolExecutor(8) as ex:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for i, rows in enumerate(ex.map(one, jobs)):
            for r in rows:
                if (r.get("gds_mclsf_nm") or name).strip() == name:
                    w.writerow(r)
                    n += 1
            if i % 320 == 0:
                print(f"- {jobs[i][0]} 까지 확인 · {n}줄", flush=True)
    print(f"완료: {out} · {n}줄")


if __name__ == "__main__":
    main()
