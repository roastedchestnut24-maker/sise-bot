"""매일 실행되는 본체.

  python -m sise.run build            # 데이터 받기 → 보고서와 카드 이미지 만들기
  python -m sise.run send             # 만들어 둔 보고서를 카톡으로 보내기
  python -m sise.run build --demo     # API 없이 예시 데이터로 화면만 확인
  python -m sise.run auth-url         # 카카오 로그인 주소 출력 (처음 한 번)
  python -m sise.run exchange CODE    # 로그인 후 받은 code 로 토큰 발급 (처음 한 번)
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median

import requests

from . import analyze, render
from .config import ITEMS, SEND_DEADLINE_HOUR

ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "data" / "history"
KST = timezone(timedelta(hours=9))


def ymd(d):
    return d.strftime("%Y-%m-%d")


CACHE = ROOT / ".cache"          # 이번 실행 안에서만 쓰는 임시 보관 (커밋하지 않음)
SENT = ROOT / "data" / "sent.json"
TIMING = ROOT / "data" / "timing.csv"


def now_kst():
    return datetime.now(KST)


def load_hist(day):
    for base in (HIST, CACHE):
        p = base / f"{day}.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            if d == {} or d.get("_sig") == analyze.SIG:
                return d
    return None


def save_hist(day, summary):
    """이틀 넘게 지난 날만 영구 저장합니다. 최근 날은 정산이 계속 들어오고 있을 수 있어서 임시로만 둡니다."""
    old = datetime.strptime(day, "%Y-%m-%d").date() <= now_kst().date() - timedelta(days=2)
    base = HIST if old else CACHE
    base.mkdir(parents=True, exist_ok=True)
    (base / f"{day}.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")


def fetch_day(day, markets, fresh=False):
    """그날 데이터가 있으면 요약을 저장하고 돌려줍니다. 없으면 None (휴장일이거나 아직 정산 전)."""
    cached = None if fresh else load_hist(day)
    if cached is not None:
        return cached or None
    from . import api
    print(f"- {day} 데이터 받는 중…", flush=True)
    rows = api.sale_day(day, markets)
    if not rows:
        # 사흘 이상 지난 날만 '휴장일'로 기록해 다시 받지 않습니다. 최근 날은 정산이 늦게 올라올 수 있어요.
        if datetime.strptime(day, "%Y-%m-%d").date() <= now_kst().date() - timedelta(days=3):
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


def target_day():
    """보낼 날짜: 어제(한국 시간). 도매시장 정산은 그날 밤~다음 날 새벽까지 계속 올라와요."""
    return now_kst().date() - timedelta(days=1)


def completeness(day_s, history):
    """그날 정산이 얼마나 들어왔는지: 최근 거래일 대비 물량·시장 수."""
    ref = [s for _, s in history if s.get("_kg")]
    if not ref or not day_s:
        return None
    ref_kg = median(s["_kg"] for s in ref)
    ref_mk = median(s.get("_markets", 0) for s in ref)
    return {"kg_ratio": day_s.get("_kg", 0) / ref_kg if ref_kg else 0,
            "markets": day_s.get("_markets", 0), "ref_markets": ref_mk}


def check(force=False, day=None):
    """지금 보낼지 정합니다. GitHub Actions 출력(go=true/false)도 남깁니다."""
    from . import api
    t = datetime.strptime(day, "%Y-%m-%d").date() if day else target_day()
    t_ymd = ymd(t)
    now = now_kst()
    sent = json.loads(SENT.read_text(encoding="utf-8")) if SENT.exists() else {}
    go, why = False, ""
    if sent.get("ymd") == t_ymd and not force:
        why = f"{t_ymd} 보고서는 이미 보냈어요 ({sent.get('at')})."
    else:
        markets = api.markets(ymd(t - timedelta(days=1)))
        cur = fetch_day(t_ymd, markets, fresh=True)
        past = trading_days(t - timedelta(days=1), markets, need=6)
        c = completeness(cur, past)
        late = now.hour >= SEND_DEADLINE_HOUR
        if not cur:
            why = f"{t_ymd} 거래 기록이 아직 없어요" + (" (휴장일로 보고 오늘은 쉬어요)." if late else ". 다음 확인 때 다시 볼게요.")
        else:
            full = c and c["kg_ratio"] >= 0.75 and c["markets"] >= c["ref_markets"] - 1
            go = bool(full or late or force)
            why = (f"{t_ymd} 정산 {c['markets']}/{c['ref_markets']:.0f}개 시장 · 평소 물량의 {c['kg_ratio'] * 100:.0f}% → "
                   + ("보냅니다." if go else "아직 덜 들어왔어요. 다음 확인 때 다시 볼게요.")) if c else f"{t_ymd} 비교 기록이 없어 그대로 보냅니다."
            if not c:
                go = True
            TIMING.parent.mkdir(exist_ok=True)
            new = not TIMING.exists()
            with TIMING.open("a", encoding="utf-8") as f:
                if new:
                    f.write("확인시각,대상일,시장수,평소대비물량,보냄\n")
                f.write(f"{now:%Y-%m-%d %H:%M},{t_ymd},{c['markets'] if c else ''},"
                        f"{c['kg_ratio']:.2f},{'Y' if go else 'N'}\n" if c else f"{now:%Y-%m-%d %H:%M},{t_ymd},,,{'Y' if go else 'N'}\n")
    print(why, flush=True)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"go={'true' if go else 'false'}\nday={t_ymd}\n")
    return go, t_ymd


def mark_sent(day):
    SENT.write_text(json.dumps({"ymd": day, "at": f"{now_kst():%Y-%m-%d %H:%M}"}, ensure_ascii=False), encoding="utf-8")


def demo_history():
    """API 없이 화면을 확인하기 위한 예시 데이터 (8일치). 이상거래 예시도 몇 개 섞어 둡니다."""
    rnd = random.Random(7)
    markets = ["서울가락", "서울강서", "구리", "대구북부", "광주각화", "부산엄궁", "부산반여", "진주"]
    days, out = [], []
    d = date(2026, 11, 26)
    while len(days) < 8:
        if d.weekday() != 6:
            days.append(d)
        d -= timedelta(days=1)
    days.reverse()
    base_price = {i["name"]: rnd.uniform(900, 9000) for i in ITEMS}
    walk = {k: 1.0 for k in base_price}

    def g(pk, kg, n, pack):
        return {"per_kg": pk, "kg": kg, "n": n, "pack": pack,
                "corp": [["중앙청과", round(pk * 1.03), round(kg * .4)], ["동화청과", round(pk), round(kg * .3)], ["한국청과", round(pk * .96), round(kg * .2)]],
                "org": [["경남 하동군", round(pk * 1.08), round(kg * .3)], ["전남 광양시", round(pk), round(kg * .25)], ["전남 순천시", round(pk * .95), round(kg * .2)]]}

    for i, day in enumerate(days):
        last = i == len(days) - 1
        s = {"_sig": analyze.SIG, "_markets": 32, "_kg": 0}
        for item in ITEMS:
            n = item["name"]
            if n == "매실":
                continue  # 제철이 아님 → '거래 없음' 표시 확인용
            walk[n] *= 1 + rnd.uniform(-0.06, 0.07)
            if last and n in ("딸기", "오이"):
                walk[n] *= 1.12
            if last and n == "생고사리":
                walk[n] *= 1.35
            pk = base_price[n] * walk[n]
            pack = item.get("unit_kg") or rnd.choice([2, 4, 5, 10])
            vol = rnd.uniform(.3, 3)
            grades = {"특": g(pk, 40000 * vol, 60, pack), "상": g(pk * 0.82, 60000 * vol, 90, pack),
                      "중": g(pk * 0.63, 30000 * vol, 40, pack), "하": g(pk * 0.45, 8000 * vol, 12, pack)}
            if last and n == "사과":
                grades["하"] = g(pk * 1.3, 900, 2, pack)            # 거래 몇 건뿐인 역전
            if last and n == "단감":
                grades["하"] = g(pk * 1.1, 6000, 14, 2)              # 소포장 역전
            if last and n == "생고사리":
                for v in grades.values():
                    v["kg"] *= 0.4
            if last and n == "배추":
                grades[analyze.NO_GRADE] = g(pk * .9, 20000, 30, pack)
            mk = {}
            for gr, v in grades.items():
                mk[gr] = {m: g(v["per_kg"] * rnd.uniform(.86, 1.14), v["kg"] / len(markets) * rnd.uniform(.5, 1.5), 5, pack)
                          for m in markets}
            if last and n == "배":
                mk["특"]["광주각화"]["per_kg"] *= 2.2
                mk["특"]["광주각화"]["n"] = 2
            s[n] = {"pack": pack, "grades": grades, "markets": mk}
            if n in ("밤", "건고사리", "생고사리", "곶감", "대봉감"):
                s[n]["mine"] = {"all": {"per_kg": pk * 1.07, "kg": 3000 * vol},
                                "m": {"부산반여": {"per_kg": pk * 1.15, "kg": 1200}, "대구북부": {"per_kg": pk * 1.02, "kg": 900}}}
            s["_kg"] += sum(v["kg"] for v in grades.values())
        out.append((ymd(day), s))
    return out


def build(demo=False, day=None):
    if demo:
        hist = demo_history()
    else:
        from . import api
        start = datetime.strptime(day, "%Y-%m-%d").date() if day else target_day()
        markets = api.markets(ymd(start - timedelta(days=1)))
        if not markets:
            sys.exit("도매시장 목록을 받지 못했어요. 인증키와 활용신청(실시간 경매정보)을 확인해 주세요.")
        print(f"도매시장 {len(markets)}곳", flush=True)
        hist = trading_days(start, markets, need=7)
        hist.reverse()
    if not hist:
        sys.exit("최근 2주 동안 정산 데이터를 찾지 못했어요. 정산정보 API 활용신청이 승인됐는지, 인증키(Decoding)가 맞는지 확인해 주세요.")
    today_ymd, today = hist[-1]
    prev = hist[-2][1] if len(hist) > 1 else None
    last_year = None
    if not demo:
        # 1년 전 같은 요일(364일 전)의 반입량과 비교
        ly_day = datetime.strptime(today_ymd, "%Y-%m-%d").date() - timedelta(days=364)
        try:
            last_year = fetch_day(ymd(ly_day), markets)
        except Exception as e:  # 작년 자료가 없어도 보고서는 만듭니다
            print(f"  (작년 비교 자료 없음: {e})")
    report = analyze.build(today_ymd, today, prev, hist, last_year)
    png = render.write_all(report, png=True)
    urls = render.public_urls(report)
    ups = [f"{c['name']} {render.chg_text(c['chg'])}" for c in report["ups"][:2]]
    downs = [f"{c['name']} {render.chg_text(c['chg'])}" for c in report["downs"][:1]]
    mine_lines = []
    for m in report["mine"][:3]:
        line = f"{m['name']} {render.won(m['price'])}({m['unit_kg']:g}kg) {render.chg_text(m['chg'])}"
        if m["best"]:
            line += f" · {m['best']['market']} 최고"
        mine_lines.append(line)
    latest = {
        "ymd": today_ymd,
        "title": f"{render.date_label(today_ymd)} 농산물 시세",
        "description": ("\n".join(mine_lines) + "\n" if mine_lines else "")
                       + f"오른 품목 {report['up_count']} · 내린 품목 {report['down_count']}\n"
                       + ", ".join(ups + downs)
                       + (f"\n⚠ 이상거래 {len(report['flagged'])}건 분석" if report.get("flagged") else ""),
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
    ap.add_argument("cmd", choices=["check", "build", "send", "sent", "auth-url", "exchange"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--date")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.cmd == "check":
        check(force=a.force, day=a.date)
    elif a.cmd == "sent":
        mark_sent(a.arg)
    elif a.cmd == "build":
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
