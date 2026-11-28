"""오늘 경매 속보: 실시간 경매정보로 '내 품목'의 오늘 낙찰가를 아침에 카톡으로 보냅니다.

  python -m sise.flash build [--date 2026-11-28]   # 자료 받기 → docs/flash.html, docs/flash.json
  python -m sise.flash send  [--force]             # 카톡 보내기 (같은 날 두 번 보내지 않음)

실시간 경매정보에는 등급·크기가 없어서, 등급을 가리지 않은 kg당 평균입니다.
정확한 등급별 시세는 다음 날 아침 정식 보고서에서 확인하세요.
"""
import argparse
import html
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

from . import api
from .analyze import _match, _num
from .config import ITEMS, MY, SITE_URL

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SENT = ROOT / "data" / "flash_sent.json"
KST = timezone(timedelta(hours=9))
COLS = ("trd_clcln_ymd,whsl_mrkt_nm,gds_mclsf_nm,gds_sclsf_nm,corp_nm,corp_gds_vrty_nm,plor_nm,"
        "pkg_nm,unit_qty,unit_nm,qty,scsbd_prc,scsbd_dt,trd_se")


def _market_list():
    by_name = {m["name"]: m for m in api.markets(datetime.now(KST).strftime("%Y-%m-%d"))}
    return [by_name[n] for n in MY["markets"] if n in by_name]


def _count(day, code):
    body = api._get(api.REALTIME_URL, {"cond[trd_clcln_ymd::EQ]": day, "cond[whsl_mrkt_cd::EQ]": code,
                                       "pageNo": 1, "numOfRows": 1})
    return int(body.get("totalCount") or 0)


def _fetch(day, markets):
    def one(m):
        try:
            return api._paged(api.REALTIME_URL, {"cond[trd_clcln_ymd::EQ]": day, "cond[whsl_mrkt_cd::EQ]": m["code"],
                                                 "selectable": COLS}, max_pages=90)
        except api.ApiError as e:
            print(f"  ! {m['name']} {day}: {e}")
            return []
    with ThreadPoolExecutor(6) as ex:
        return [r for rows in ex.map(one, markets) for r in rows]


def _rows_for(item, rows):
    """품목에 맞는 kg 거래만, 낙찰가 0원과 단위가 이상한 줄은 뺍니다."""
    out = []
    for r in rows:
        if not _match(item, r) or (r.get("unit_nm") or "").strip() != "kg":
            continue
        each, n, prc = _num(r.get("unit_qty")), _num(r.get("qty")), _num(r.get("scsbd_prc"))
        if each <= 0 or n <= 0 or prc <= 0:
            continue
        out.append({**r, "_kg": each * n, "_won": prc * n, "_pk": prc / each})
    if len(out) >= 5:   # 단위 입력 실수로 보이는 줄(중앙값의 1/5 미만, 5배 초과)은 뺍니다
        mid = median(x["_pk"] for x in out)
        out = [x for x in out if mid / 5 <= x["_pk"] <= mid * 5]
    return out


def _agg(rows):
    kg = sum(r["_kg"] for r in rows)
    return {"pk": round(sum(r["_won"] for r in rows) / kg) if kg else None, "kg": round(kg), "n": len(rows)}


def _origin(r):
    return MY["origin"] in (r.get("plor_nm") or "")


def summarize(rows, prev_rows):
    items = {i["name"]: i for i in ITEMS}
    out = []
    for name in MY["items"]:
        item = items.get(name)
        if not item:
            continue
        rs, ps = _rows_for(item, rows), _rows_for(item, prev_rows)
        a, p = _agg(rs), _agg(ps)
        chg = round((a["pk"] / p["pk"] - 1) * 100, 1) if a["pk"] and p["pk"] else None
        mk = defaultdict(list)
        for r in rs:
            mk[r["whsl_mrkt_nm"]].append(r)
        markets = []
        for m in MY["markets"]:
            g = mk.get(m, [])
            if g:
                mine = [r for r in g if _origin(r)]
                markets.append({"name": m, **_agg(g), "mine": _agg(mine)["pk"] if mine else None})
        markets.sort(key=lambda x: -(x["pk"] or 0))
        mine = [r for r in rs if _origin(r)]
        recent = sorted(mine, key=lambda r: r.get("scsbd_dt") or "", reverse=True)[:10]
        out.append({
            "name": name, "unit_kg": item.get("unit_kg"), **a, "prev": p["pk"], "chg": chg,
            "mine": _agg(mine) if mine else None, "markets": markets,
            "last": max((r.get("scsbd_dt") or "" for r in rs), default="")[11:16],
            "recent": [{"t": (r.get("scsbd_dt") or "")[11:16], "m": r.get("whsl_mrkt_nm"), "c": r.get("corp_nm"),
                        "v": r.get("corp_gds_vrty_nm"), "each": _num(r.get("unit_qty")), "n": round(_num(r.get("qty"))),
                        "prc": round(_num(r.get("scsbd_prc"))), "pk": round(r["_pk"])} for r in recent],
        })
    return out


def _won(x):
    return f"{x:,.0f}원" if x else "-"


def _arrow(c):
    if c is None:
        return ""
    return f"▲{c:.1f}%" if c > 0 else (f"▼{abs(c):.1f}%" if c < 0 else "-0.0%")


def text_message(day, at, items):
    """카톡 글자 템플릿은 200자까지라 짧게 씁니다."""
    lines = [f"오늘 경매 속보 {day[5:].replace('-', '/')} {at} 기준 (kg당, 등급 무관)"]
    for it in items:
        if not it["pk"]:
            continue
        s = f"{it['name']} {_won(it['pk'])} {_arrow(it['chg'])}".rstrip()
        if it["mine"]:
            s += f" 하동 {it['mine']['pk']:,}"
        if len(it["markets"]) > 1:
            s += f" · 최고 {it['markets'][0]['name']}"
        lines.append(s)
    none = [it["name"] for it in items if not it["pk"]]
    if none:
        lines.append("거래 없음: " + "·".join(none))
    text = "\n".join(lines)
    while len(text) > 200 and len(lines) > 2:
        lines = [l.split(" · ")[0] for l in lines] if any(" · " in l for l in lines) else lines[:-1]
        text = "\n".join(lines)
    return text[:200]


CSS = """
body{margin:0;font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;font-size:17px;
 background:#f6f4ef;color:#222;line-height:1.5}
main{max-width:640px;margin:0 auto;padding:16px}
h1{font-size:22px;margin:4px 0}
.note{color:#666;font-size:15px}
.card{background:#fff;border-radius:14px;padding:14px 16px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.card h2{font-size:20px;margin:0 0 4px}
.price{font-size:26px;font-weight:700}
.up{color:#d33}.down{color:#1a6ad6}
.mine{background:#fff7e0;border-radius:10px;padding:8px 10px;margin:8px 0}
table{width:100%;border-collapse:collapse;font-size:15px;margin-top:6px}
th,td{padding:5px 4px;border-bottom:1px solid #eee;text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:#777;font-weight:500}
details summary{cursor:pointer;color:#555;margin-top:8px}
.none{color:#999}
"""


def page(day, at, prev_day, items):
    e = html.escape
    out = [f"<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>오늘 경매 속보 {day}</title><style>{CSS}</style></head><body><main>",
           f"<h1>오늘 경매 속보 · {day}</h1>",
           f"<p class='note'>{at} 기준 · 내 시장 {len(MY['markets'])}곳 · 등급을 가리지 않은 kg당 평균입니다. "
           f"실시간 경매정보에는 등급·크기가 나오지 않아요. 등락은 직전 경매일({prev_day}) 같은 시장 같은 방식 평균과 비교했어요. "
           f"등급별 정확한 시세는 내일 아침 정식 보고서에서 확인하세요.</p>"]
    for it in items:
        out.append("<div class='card'>")
        out.append(f"<h2>{e(it['name'])}</h2>")
        if not it["pk"]:
            out.append("<p class='none'>오늘 내 시장에서 아직 거래가 없어요.</p></div>")
            continue
        cls = "up" if (it["chg"] or 0) > 0 else ("down" if (it["chg"] or 0) < 0 else "")
        unit = f" · {it['unit_kg']}kg {_won(it['pk'] * it['unit_kg'])}" if it.get("unit_kg") else ""
        out.append(f"<div><span class='price'>{_won(it['pk'])}</span>/kg <span class='{cls}'>{_arrow(it['chg'])}</span>{unit}</div>")
        out.append(f"<div class='note'>물량 {it['kg']:,}kg · {it['n']}건 · 마지막 낙찰 {it['last'] or '-'}"
                   f"{' · 직전 ' + _won(it['prev']) if it['prev'] else ''}</div>")
        if it["mine"]:
            gap = round((it["mine"]["pk"] / it["pk"] - 1) * 100, 1)
            out.append(f"<div class='mine'>하동산 {_won(it['mine']['pk'])}/kg "
                       f"(평균보다 {'+' if gap >= 0 else ''}{gap}%) · {it['mine']['kg']:,}kg</div>")
        else:
            out.append("<div class='mine none'>오늘 하동산 거래는 아직 없어요.</div>")
        out.append("<table><tr><th>시장</th><th>kg당</th><th>물량</th><th>하동산</th></tr>")
        for m in it["markets"]:
            out.append(f"<tr><td>{e(m['name'])}</td><td>{_won(m['pk'])}</td><td>{m['kg']:,}kg</td>"
                       f"<td>{_won(m['mine'])}</td></tr>")
        out.append("</table>")
        if it["recent"]:
            out.append("<details><summary>하동산 최근 낙찰 보기</summary><table>"
                       "<tr><th>시각</th><th>시장·법인</th><th>포장</th><th>상자당</th><th>kg당</th></tr>")
            for r in it["recent"]:
                out.append(f"<tr><td>{r['t']}</td><td>{e(r['m'] or '')}<br><span class='note'>{e(r['c'] or '')} "
                           f"{e(r['v'] or '')}</span></td><td>{r['each']:g}kg×{r['n']}</td>"
                           f"<td>{_won(r['prc'])}</td><td>{_won(r['pk'])}</td></tr>")
            out.append("</table></details>")
        out.append("</div>")
    out.append("<p class='note'>자료: 한국농수산식품유통공사 실시간 경매정보 (공공데이터포털)</p></main></body></html>")
    return "".join(out)


def prev_trading_day(day, markets):
    d = datetime.strptime(day, "%Y-%m-%d").date()
    for back in range(1, 6):
        p = (d - timedelta(days=back)).isoformat()
        if _count(p, markets[0]["code"]) > 0:
            return p
    return None


def build(day=None):
    now = datetime.now(KST)
    day = day or now.strftime("%Y-%m-%d")
    markets = _market_list()
    rows = _fetch(day, markets)
    print(f"{day} 실시간 경매 {len(rows):,}줄")
    if not rows:
        print("오늘 경매 자료가 없어요 (휴장일일 수 있어요).")
        (DOCS / "flash.json").write_text(json.dumps({"day": day, "items": []}, ensure_ascii=False), encoding="utf-8")
        return None
    prev_day = prev_trading_day(day, markets)
    prev_rows = _fetch(prev_day, markets) if prev_day else []
    print(f"비교일 {prev_day} {len(prev_rows):,}줄")
    items = summarize(rows, prev_rows)
    at = now.strftime("%H:%M") if day == now.strftime("%Y-%m-%d") else "마감"
    DOCS.mkdir(exist_ok=True)
    (DOCS / "flash.html").write_text(page(day, at, prev_day, items), encoding="utf-8")
    data = {"day": day, "at": at, "prev_day": prev_day, "items": items, "text": text_message(day, at, items),
            "url": SITE_URL + "flash.html"}
    (DOCS / "flash.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(data["text"])
    return data


def send(force=False):
    from . import kakao
    data = json.loads((DOCS / "flash.json").read_text(encoding="utf-8"))
    if not data.get("items"):
        print("보낼 내용이 없어요.")
        return
    sent = json.loads(SENT.read_text(encoding="utf-8")) if SENT.exists() else []
    if data["day"] in sent and not force:
        print("오늘은 이미 보냈어요.")
        return
    kakao.send_text(data["text"], data["url"] + "?d=" + data["day"], "자세히 보기")
    SENT.write_text(json.dumps((sent + [data["day"]])[-60:], ensure_ascii=False), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "send"])
    ap.add_argument("--date")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.date)
    else:
        send(a.force)


if __name__ == "__main__":
    sys.exit(main())
