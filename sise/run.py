"""매일 실행되는 본체.

  python -m sise.run build            # 데이터 받기 → 보고서와 카드 이미지 만들기
  python -m sise.run send             # 만들어 둔 보고서를 카톡으로 보내기
  python -m sise.run build --demo     # API 없이 예시 데이터로 화면만 확인
  python -m sise.run auth-url         # 카카오 로그인 주소 출력 (처음 한 번)
  python -m sise.run exchange CODE    # 로그인 후 받은 code 로 토큰 발급 (처음 한 번)
"""
import argparse
import json
import random
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from . import analyze, render
from .config import ITEMS

ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "data" / "history"
KST = timezone(timedelta(hours=9))


def ymd(d):
    return d.strftime("%Y-%m-%d")


def load_hist(day):
    p = HIST / f"{day}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_hist(day, summary):
    HIST.mkdir(parents=True, exist_ok=True)
    (HIST / f"{day}.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")


def fetch_day(day, markets):
    """그날 데이터가 있으면 요약을 저장하고 돌려줍니다. 없으면 None (휴장일이거나 아직 정산 전)."""
    cached = load_hist(day)
    if cached is not None:
        return cached or None
    from . import api
    print(f"- {day} 데이터 받는 중…")
    rows = api.sale_day(day, markets)
    if not rows:
        # 사흘 이상 지난 날만 '휴장일'로 기록해 다시 받지 않습니다. 최근 날은 정산이 늦게 올라올 수 있어요.
        if datetime.strptime(day, "%Y-%m-%d").date() <= datetime.now(KST).date() - timedelta(days=3):
            save_hist(day, {})
        return None
    (ROOT / "data" / "catalog.json").write_text(
        json.dumps(analyze.catalog(rows), ensure_ascii=False, indent=1), encoding="utf-8")
    s = analyze.summarize(rows)
    save_hist(day, s)
    return s


def trading_days(start, markets, need, max_back=14):
    """start 부터 거꾸로 데이터 있는 날을 need 개 찾습니다."""
    found = []
    d = start
    for _ in range(max_back):
        s = fetch_day(ymd(d), markets)
        if s:
            found.append((ymd(d), s))
            if len(found) >= need:
                break
        d -= timedelta(days=1)
    return found


def demo_history():
    """API 없이 화면을 확인하기 위한 예시 데이터 (8일치)."""
    rnd = random.Random(7)
    base_price = {"배추": 1240, "무": 945, "양배추": 1225, "대파": 2350, "양파": 1450, "감자": 1925, "당근": 1485,
                  "오이": 3400, "애호박": 2400, "청양고추": 5800, "사과": 4650, "배": 3470, "감귤": 2560,
                  "단감": 2430, "딸기": 18000, "토마토": 3720, "밤": 4550, "고사리": 41500, "매실": 3000}
    markets = ["가락", "강서", "구리", "대구북부", "광주각화", "부산엄궁", "대전오정", "인천삼산"]
    days, out = [], []
    d = date(2026, 11, 27)
    while len(days) < 8:
        if d.weekday() != 6:
            days.append(d)
        d -= timedelta(days=1)
    days.reverse()
    walk = {k: 1.0 for k in base_price}
    for i, day in enumerate(days):
        s = {}
        for item in ITEMS:
            n = item["name"]
            if n == "매실":
                continue  # 제철이 아님 → '거래 없음' 표시 확인용
            walk[n] *= 1 + rnd.uniform(-0.06, 0.07)
            if i == len(days) - 1 and n in ("딸기", "오이"):
                walk[n] *= 1.12
            if i == len(days) - 1 and n == "청양고추":
                walk[n] *= 0.88
            pk = base_price[n] * walk[n]
            grades = {"특": {"per_kg": pk, "kg": 40000 * rnd.uniform(.5, 1.5)},
                      "상": {"per_kg": pk * 0.82, "kg": 60000 * rnd.uniform(.5, 1.5)},
                      "보통": {"per_kg": pk * 0.63, "kg": 30000 * rnd.uniform(.5, 1.5)},
                      "하": {"per_kg": pk * 0.45, "kg": 8000 * rnd.uniform(.5, 1.5)}}
            mk = {}
            for g, v in grades.items():
                mk[g] = {m: {"per_kg": v["per_kg"] * rnd.uniform(.86, 1.14), "kg": v["kg"] * rnd.uniform(.02, .4)}
                         for m in markets}
            s[n] = {"grades": grades, "markets": mk}
        out.append((ymd(day), s))
    return out


def build(demo=False, day=None):
    if demo:
        hist = demo_history()
    else:
        from . import api
        start = datetime.strptime(day, "%Y-%m-%d").date() if day else datetime.now(KST).date()
        markets = api.markets(ymd(start - timedelta(days=1)))
        if not markets:
            sys.exit("도매시장 목록을 받지 못했어요. 인증키와 활용신청(실시간 경매정보)을 확인해 주세요.")
        print(f"도매시장 {len(markets)}곳")
        hist = trading_days(start, markets, need=7)
        hist.reverse()
    if not hist:
        sys.exit("최근 2주 동안 정산 데이터를 찾지 못했어요. 정산정보 API 활용신청이 승인됐는지, 인증키(Decoding)가 맞는지 확인해 주세요.")
    today_ymd, today = hist[-1]
    prev = hist[-2][1] if len(hist) > 1 else None
    report = analyze.build(today_ymd, today, prev, hist)
    png = render.write_all(report, png=True)
    urls = render.public_urls(report)
    ups = [f"{c['name']} {render.chg_text(c['chg'])}" for c in report["ups"][:2]]
    downs = [f"{c['name']} {render.chg_text(c['chg'])}" for c in report["downs"][:1]]
    latest = {
        "ymd": today_ymd,
        "title": f"{render.date_label(today_ymd)} 농산물 시세",
        "description": f"오른 품목 {report['up_count']} · 내린 품목 {report['down_count']}\n"
                       + ", ".join(ups + downs),
        "card_url": urls["card"],
        "report_url": urls["report"],
    }
    (render.DOCS / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"보고서 완성: {today_ymd} · 품목 {report['item_count']}개 · 카드 {png}")
    return latest


def send():
    from . import kakao
    latest = json.loads((render.DOCS / "latest.json").read_text(encoding="utf-8"))
    # GitHub Pages 에 새 이미지가 올라갈 때까지 최대 6분 기다립니다
    ok = False
    for _ in range(36):
        try:
            if requests.head(latest["card_url"], timeout=10).status_code == 200:
                ok = True
                break
        except requests.RequestException:
            pass
        time.sleep(10)
    if not ok:
        print("카드 이미지가 아직 공개되지 않아 글자로만 보냅니다.")
    kakao.send_report(latest, latest["card_url"], latest["report_url"], image_ok=ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "send", "auth-url", "exchange"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--date")
    a = ap.parse_args()
    if a.cmd == "build":
        build(demo=a.demo, day=a.date)
    elif a.cmd == "send":
        send()
    elif a.cmd == "auth-url":
        from . import kakao
        print(kakao.authorize_url())
    elif a.cmd == "exchange":
        from . import kakao
        kakao.exchange_code(a.arg or "")


if __name__ == "__main__":
    main()
