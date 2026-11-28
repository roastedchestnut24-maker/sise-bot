"""실시간 경매정보가 어떤 항목을 주는지 확인합니다 (등급·크기·포장·산지 포함 여부).

  python -m sise.probe [날짜]   # 날짜를 비우면 오늘(한국 시간)
"""
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

from . import api

KST = timezone(timedelta(hours=9))


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.now(KST).strftime("%Y-%m-%d")
    print(f"조회일: {day} (서울가락 110001)")
    body = api._get(api.REALTIME_URL, {"cond[trd_clcln_ymd::EQ]": day, "cond[whsl_mrkt_cd::EQ]": "110001",
                                       "pageNo": 1, "numOfRows": 200})
    print("전체 건수:", body.get("totalCount"))
    items = api._items(body)
    print(f"받은 줄 수: {len(items)}")
    if not items:
        print(json.dumps(body, ensure_ascii=False)[:1500])
        return
    print("항목 이름:", sorted(items[0].keys()))
    for r in items[:3]:
        print(json.dumps(r, ensure_ascii=False))
    for k in sorted(items[0].keys()):
        if any(x in k for x in ("grd", "sz", "pkg", "plor", "unit", "time", "hr", "tm", "corp")):
            print(f"  {k}: {Counter(str(r.get(k)) for r in items).most_common(6)}")


if __name__ == "__main__":
    main()
