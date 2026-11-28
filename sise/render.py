"""보고서 HTML(웹 리포트)과 카톡용 카드 이미지(800x800 PNG)를 만듭니다."""
import html
from datetime import datetime
from pathlib import Path

from .config import SITE_URL, CATS
from .analyze import josa

DOCS = Path(__file__).resolve().parent.parent / "docs"
UP, DOWN = "#C62828", "#1E5BB8"
WEEK = "월화수목금토일"

FONT = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap">'


def e(s):
    return html.escape(str(s))


def won(v):
    return f"{round(v / 100) * 100:,.0f}원"


def chg_text(c, space=True):
    if c is None:
        return "–"
    arrow = "▲" if c > 0 else ("▼" if c < 0 else "–")
    return f"{arrow}{' ' if space else ''}{abs(c):.1f}%"


def chg_color(c):
    if c is None or c == 0:
        return "#55524B"
    return UP if c > 0 else DOWN


def date_label(ymd, short=False):
    d = datetime.strptime(ymd, "%Y-%m-%d")
    if short:
        return f"{d.month}.{d.day} {WEEK[d.weekday()]}"
    return f"{d.month}월 {d.day}일({WEEK[d.weekday()]})"


def spec(c):
    return f"{c['base']} · {c['unit_kg']:g}kg"


def spark_svg(c):
    pts = [p for _, p in c["spark"]]
    if len(pts) < 2:
        return '<div class="nospark">기록이 쌓이면 7일 흐름이 보여요</div>'
    mn, mx = min(pts), max(pts)
    rng = (mx - mn) or 1
    n = len(pts)
    xy = [(4 + i * (116 / (n - 1)), 4 + (1 - (p - mn) / rng) * 32) for i, p in enumerate(pts)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    col = chg_color(c["chg"])
    label = f"{c['name']} 최근 {n}일 가격 흐름"
    return (f'<svg class="spark" viewBox="0 0 124 40" preserveAspectRatio="none" role="img" aria-label="{e(label)}">'
            f'<polyline points="{line}" fill="none" stroke="{col}" stroke-width="2" stroke-linejoin="round" '
            f'stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')


CSS = """
body{margin:0;background:#F4F2EC;font-family:'Noto Sans KR',sans-serif;color:#1C1B19;font-size:17px}
a{color:#2F6B3A}
.wrap{max-width:760px;margin:0 auto;padding:32px 16px 64px;display:flex;flex-direction:column;gap:16px}
h1{margin:0;font-size:32px;font-weight:900;line-height:1.25;letter-spacing:-.02em}
h2{margin:0;font-size:20px;font-weight:900}
.muted{color:#55524B}
.box{background:#fff;border-radius:20px;padding:24px;display:flex;flex-direction:column;gap:6px}
.dark{background:#1C1B19;color:#fff;border-radius:20px;padding:22px 24px}
.kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.kpi{background:#fff;border-radius:16px;padding:16px}
.kpi b{display:block;font-size:34px;font-weight:900}
.note{background:#fff;border:1px solid #DCD7CB;border-radius:16px;padding:16px 18px;font-size:15px;line-height:1.6}
.rank{display:grid;grid-template-columns:112px minmax(0,1fr) 72px;align-items:center;gap:10px;min-height:40px}
.rank .nm{display:flex;flex-direction:column;line-height:1.25}
.rank .nm span:first-child{font-size:15px;font-weight:700}
.rank .nm span:last-child{font-size:12px;color:#55524B}
.half{flex:1 1 0;display:flex;align-items:center;height:22px}
.half.l{justify-content:flex-end;border-right:1px solid #8A867C}
.tabs{display:flex;flex-wrap:wrap;gap:6px}
.tabs button{min-height:44px;min-width:56px;padding:0 16px;border-radius:999px;font:inherit;font-size:14px;font-weight:700;cursor:pointer;border:1px solid #CFCAC0;background:#fff;color:#1C1B19}
.tabs button[aria-pressed=true]{background:#1C1B19;color:#fff;border-color:#1C1B19}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;align-items:start}
.card{position:relative;isolation:isolate;overflow:hidden;background:#fff;border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:8px}
.card .art{position:absolute;z-index:-1;right:-18px;top:30px;width:136px;height:136px;opacity:.2;pointer-events:none}
.tag{align-self:flex-start;font-size:12px;font-weight:500;color:#2F4A28;background:#EEF4EC;border-radius:6px;padding:2px 8px}
.price{font-size:26px;font-weight:900}
.chip{font-size:14px;font-weight:700;border-radius:999px;padding:2px 10px;white-space:nowrap}
.spark{width:100%;height:44px}
.nospark{font-size:12px;color:#55524B;height:44px;display:flex;align-items:center}
.ladder{border-top:1px solid #ECE9E1;padding-top:10px;display:flex;flex-direction:column;gap:5px}
.lrow{display:grid;grid-template-columns:64px minmax(0,1fr) 78px;align-items:center;gap:8px;font-size:14px}
.track{height:10px;background:#F4F2EC;border-radius:5px;overflow:hidden}
.mrow{display:grid;grid-template-columns:64px minmax(0,1fr) 84px;align-items:center;gap:10px;font-size:15px;font-weight:700}
.mtrack{height:24px;background:#F4F2EC;border-radius:6px;overflow:hidden}
.lrow.flag span:first-child{color:#B26A00!important}
.alert{background:#FFF6E5;border:1px solid #F2D49B;border-radius:12px;padding:10px 12px;display:flex;flex-direction:column;gap:6px;font-size:12.5px;line-height:1.55}
.alert b{font-size:13px;color:#7A4A00}
.alert ul{margin:0;padding-left:16px}
.alist{display:flex;flex-direction:column;gap:10px}
.aitem{display:grid;grid-template-columns:92px minmax(0,1fr);gap:10px;font-size:14px;line-height:1.55;border-top:1px solid #ECE9E1;padding-top:10px}
.aitem:first-child{border-top:0;padding-top:0}
.kind{display:inline-block;font-size:11px;font-weight:700;border-radius:6px;padding:1px 6px;margin-right:6px;background:#FFE9C2;color:#7A4A00}
details summary{cursor:pointer;font-weight:700;font-size:14px;color:#2F6B3A;padding:8px 0;min-height:24px}
.warn{font-size:11px;font-weight:700;color:#7A4A00;background:#FFE9C2;border-radius:6px;padding:2px 6px;white-space:nowrap}
details.more{border-top:1px solid #ECE9E1;margin-top:2px}
details.more>summary{list-style:none;cursor:pointer;min-height:40px;display:flex;align-items:center;justify-content:space-between;font-size:13px;font-weight:700;color:#2F6B3A}
details.more>summary::-webkit-details-marker,details.sec>summary::-webkit-details-marker,details.note>summary::-webkit-details-marker{display:none}
details.more>summary::after{content:"펼치기 ▾";font-weight:500;color:#55524B}
details.more[open]>summary::after{content:"접기 ▴"}
.morebody{display:flex;flex-direction:column;gap:8px;padding-bottom:4px}
details.sec>summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;min-height:32px}
details.sec>summary::after{content:"접기 ▴";font-size:13px;color:#55524B;font-weight:500}
details.sec:not([open])>summary::after{content:"펼치기 ▾"}
details.note>summary{list-style:none;cursor:pointer;font-weight:700;min-height:24px}
details.note>summary::after{content:" ▾";color:#55524B}
.card.off{opacity:.7;padding:12px 16px;gap:2px}
.thin{font-size:11px;font-weight:700;color:#55524B;background:#ECE9E1;border-radius:6px;padding:2px 6px;white-space:nowrap}
.facts{border-top:1px solid #ECE9E1;padding-top:10px;display:flex;flex-direction:column;gap:6px;font-size:13.5px;line-height:1.5}
.facts b{font-size:13px}
.facts .row{display:flex;justify-content:space-between;gap:8px}
.mine{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.mcard{background:#fff;border:2px solid #2F6B3A;border-radius:18px;padding:18px;display:flex;flex-direction:column;gap:8px}
.mcard .nm{font-size:22px;font-weight:900}
.mcard .pr{font-size:32px;font-weight:900;line-height:1.1}
.mcard .best{background:#EEF4EC;border-radius:12px;padding:10px 12px;font-size:16px;line-height:1.55}
.mcard .org{font-size:15px;line-height:1.55}
.mcard .opts{display:flex;flex-direction:column;gap:3px;font-size:14px}
.mcard .opts div{display:flex;justify-content:space-between}
.ghost{min-height:40px;padding:0 14px;border-radius:999px;border:1px solid #CFCAC0;background:#fff;font:inherit;font-size:13px;font-weight:700;cursor:pointer}
footer{font-size:13px;line-height:1.7;color:#55524B;padding:8px 4px}
@media (max-width:480px){h1{font-size:26px}.kpi b{font-size:26px}}
"""


def _pct(v):
    return "–" if v is None else (f"+{v:.0f}%" if v >= 0 else f"{v:.0f}%")


def facts_html(c):
    rows = []
    if c.get("vol_prev") is not None or c.get("vol_ly") is not None:
        rows.append(f'<div><b>반입량(전체 등급)</b><br><span class="muted">전 거래일 대비 {_pct(c.get("vol_prev"))} · 작년 같은 요일 대비 {_pct(c.get("vol_ly"))}</span></div>')

    def lst(title, items):
        if not items:
            return ""
        body = " · ".join(f'{e(n)} {won(p)}' for n, p, _ in items)
        return f'<div><b>{title}</b><br><span class="muted">{body}</span></div>'
    rows.append(lst("품종별", c.get("vars")))
    rows.append(lst("물량 많은 법인", c.get("corps")))
    rows.append(lst("물량 많은 산지", c.get("orgs")))
    body = "".join(x for x in rows if x)
    return f'<div class="facts">{body}</div>' if body else ""


def mine_section(r):
    if not r.get("mine") and not r.get("mine_off"):
        return ""
    fee = r.get("fee") or 0
    cost = f"위탁수수료 {fee * 100:g}%" + (" · 운송비" if r.get("has_freight") else "")
    cards = []
    for m in r["mine"]:
        chip_bg = "#FDECEC" if (m["chg"] or 0) > 0 else ("#EAF0FA" if (m["chg"] or 0) < 0 else "#ECE9E1")
        best = ""
        if m["best"]:
            b = m["best"]
            best = (f'<div class="best">내 시장 중 <b>{e(josa(b["market"], "이", "가"))}</b> 가장 높아요 · {won(b["price"])}<br>'
                    f'<span class="muted" style="font-size:14px">{e(cost)} 빼면 약 <b>{won(b["net"])}</b> 손에 쥐어요</span></div>')
        org = ""
        o = m.get("origin")
        if o:
            sign = "+" if o["prem"] >= 0 else ""
            where = ", ".join(f'{e(x)} {won(p * m["unit_kg"])}' for x, p, _ in o["markets"])
            org = (f'<div class="org"><b>{e(r.get("my_origin") or "내 산지")}산</b> kg당 {won(o["per_kg"])} · 전국 평균보다 '
                   f'<b style="color:{UP if o["prem"] >= 0 else DOWN}">{sign}{o["prem"]:.0f}%</b> ({o["kg"] / 1000:.1f}톤)<br>'
                   f'<span class="muted" style="font-size:14px">{where} ({m["unit_kg"]:g}kg 환산)</span></div>')
        opts = "".join(f'<div><span>{e(x["market"])}</span><span>{won(x["price"])}</span></div>' for x in m["options"][1:])
        opts = f'<div class="opts muted">{opts}</div>' if opts else ""
        thin = '<span class="thin">물량 적음</span>' if m["thin"] else ""
        warn = '<span class="warn">⚠ 이상거래</span>' if m["notes"] else ""
        cards.append(
            f'<div class="mcard"><div style="display:flex;justify-content:space-between;align-items:center;gap:6px">'
            f'<span class="nm">{e(m["name"])}</span><span style="display:flex;gap:4px">{warn}{thin}</span></div>'
            f'<div class="tag">기준 {e(m["base"])} · {m["unit_kg"]:g}kg</div>'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline"><span class="pr">{won(m["price"])}</span>'
            f'<span class="chip" style="font-size:17px;background:{chip_bg};color:{chg_color(m["chg"])}">{chg_text(m["chg"])}</span></div>'
            f'{best}{org}{opts}</div>')
    off = (f'<div class="muted" style="font-size:14px">제철이 아니라 오늘 거래가 없는 내 품목: {e(", ".join(r["mine_off"]))}</div>'
           if r.get("mine_off") else "")
    return (f'<section style="display:flex;flex-direction:column;gap:10px"><h2>내 품목</h2>'
            f'<div class="mine">{"".join(cards)}</div>{off}'
            f'<div class="muted" style="font-size:13px">손에 쥐는 금액은 경락가에서 {e(cost)}를 뺀 추정이에요. 실제 정산서와 다를 수 있어요.</div></section>')


def report_html(r):
    maxabs = max([abs(c["chg"]) for c in r["ranked"]] or [1]) or 1
    def rank_row(c):
        w = abs(c["chg"]) / maxabs * 100
        neg = f'<div style="height:16px;border-radius:4px 0 0 4px;background:{DOWN};width:{w:.1f}%"></div>' if c["chg"] < 0 else ""
        pos = f'<div style="height:16px;border-radius:0 4px 4px 0;background:{UP};width:{w:.1f}%"></div>' if c["chg"] > 0 else ""
        return (
            f'<div class="rank"><div class="nm"><span>{e(c["name"])}</span><span>{e(spec(c))}</span></div>'
            f'<div style="display:flex"><div class="half l">{neg}</div><div class="half">{pos}</div></div>'
            f'<div style="font-size:15px;font-weight:700;text-align:right;color:{chg_color(c["chg"])}">{chg_text(c["chg"])}</div></div>')

    ranked = r["ranked"]
    if len(ranked) > 12:
        head = ranked[:5]
        tail = ranked[-5:]
        mid = ranked[5:-5]
        rank_html = ("".join(map(rank_row, head)) + '<div class="muted" style="text-align:center;font-size:13px">⋯</div>'
                     + "".join(map(rank_row, tail))
                     + f'<details><summary>가운데 {len(mid)}개 품목도 보기</summary>{"".join(map(rank_row, mid))}</details>')
    else:
        rank_html = "".join(map(rank_row, ranked))

    def alert_html(c):
        if not c.get("notes"):
            return ""
        items = "".join(f'<li><b>{e(n["title"])}</b><br>{"<br>".join(e(w) for w in n["why"])}</li>' for n in c["notes"])
        return f'<div class="alert"><b>⚠ 이상거래 분석</b><ul>{items}</ul></div>'

    cards = []
    for c in r["cards"]:
        art = f'<img class="art" src="art/{e(c["art"])}.svg" alt="" aria-hidden="true">'
        if c["missing"]:
            continue
        top = max(l["price"] for l in c["ladder"]) or 1
        ladder = "".join(
            f'<div class="lrow{" flag" if l["flag"] else ""}" title="거래 비중 {l["share"] * 100:.0f}%"><span style="font-weight:700;color:{"#2F6B3A" if l["base"] else "#55524B"}">{"⚠" if l["flag"] else ""}{e("미표기" if l["grade"] == "등급 미표기" else l["grade"])}</span>'
            f'<div class="track"><div style="height:10px;border-radius:5px;width:{l["price"] / top * 100:.0f}%;background:{"#2F6B3A" if l["base"] else "#B9CDB3"}"></div></div>'
            f'<span style="text-align:right;font-weight:{700 if l["base"] else 400}">{won(l["price"])}</span></div>'
            for l in c["ladder"])
        chip_bg = "#FDECEC" if (c["chg"] or 0) > 0 else ("#EAF0FA" if (c["chg"] or 0) < 0 else "#ECE9E1")
        hl = ""
        if c["hi"] and c["lo"]:
            hl = (f'<div style="display:flex;flex-direction:column;font-size:12px" class="muted">'
                  f'<span>주요 시장 최고 {e(c["hi"][0])} {won(c["hi"][1])}</span><span>주요 시장 최저 {e(c["lo"][0])} {won(c["lo"][1])}</span>'
                  f'<span style="font-size:11px">주요 시장: 기준 등급 물량 3% 이상인 곳. 기준가는 전체 시장 평균이라 범위를 벗어날 수 있어요</span></div>')
        badge = ('<span class="warn">⚠ 이상거래</span>' if c.get("notes") else "") + ('<span class="thin">물량 적음</span>' if c.get("thin") else "")
        facts = facts_html(c)
        cards.append(
            f'<article class="card" data-cat="{e(c["cat"])}">{art}'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:6px"><div style="font-size:17px;font-weight:900">{e(c["name"])}</div>'
            f'{badge}</div>'
            f'<div class="tag">기준 {e(spec(c))}</div>'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px"><div class="price">{won(c["price"])}</div>'
            f'<div class="chip" style="background:{chip_bg};color:{chg_color(c["chg"])}">{chg_text(c["chg"])}</div></div>'
            f'<div class="muted" style="font-size:13px;margin-top:-4px">kg당 {won(c["per_kg"])} · 거래 {c["volume_t"]:.1f}톤</div>'
            f'<details class="more"><summary>{"흐름·등급·이상거래 분석" if c.get("notes") else "흐름·등급별 가격"}</summary>'
            f'<div class="morebody">{spark_svg(c)}<div class="ladder"><div style="font-size:13px;font-weight:700">등급별 가격</div>{ladder}</div>{facts}{alert_html(c)}{hl}</div></details></article>')

    feat = ""
    f = r["featured"]
    if f and f["markets"]:
        top = max(p for _, p, _ in f["markets"])
        rows = "".join(
            f'<div class="mrow"><span>{e(m)}</span><div class="mtrack"><div style="height:24px;border-radius:6px;width:{p / top * 100:.1f}%;background:{"#2F6B3A" if i == 0 else "#A9C3A3"}"></div></div>'
            f'<span style="text-align:right">{won(p)}</span></div>' for i, (m, p, _) in enumerate(f["markets"]))
        gap = ""
        if len(f["markets"]) > 1:
            a, b = f["markets"][0], f["markets"][-1]
            gap = (f'<div style="font-size:14px;background:#EEF4EC;border-radius:12px;padding:12px 14px;margin-top:6px">'
                   f'{e(josa(a[0], "이", "가"))} {e(b[0])}보다 {f["unit_kg"]:g}kg당 <b>{won(a[1] - b[1])}</b> 높아요.</div>')
        feat = (f'<details class="box sec" open><summary><h2>시장별로 비교하면 · {e(f["name"])} {e(spec(f))}</h2></summary>'
                f'<div class="muted" style="font-size:14px;margin-bottom:6px">거래량이 많은 시장만 골랐어요. 출하할 시장을 고를 때 보세요.</div>{rows}{gap}</details>')

    alerts = ""
    if r.get("flagged"):
        rows = "".join(
            f'<div class="aitem"><b>{e(c["name"])}</b><div>' + "<br>".join(
                f'<span class="kind">{e(n["kind"])}</span>{e(n["title"])}' for n in c["notes"]) + '</div></div>'
            for c in r["flagged"])
        alerts = (f'<section class="box"><h2>이상거래 감지 {len(r["flagged"])}개 품목</h2>'
                  f'<div class="muted" style="font-size:14px;margin-bottom:8px">아래 등급이 더 비싸거나, 하루 20% 넘게 움직였거나, 한 시장만 값이 튄 경우예요. '
                  f'원인 분석은 각 품목 카드의 ⚠ 칸에 있어요.</div><div class="alist">{rows}</div></section>')
    tab_btns = '<button type="button" aria-pressed="true" data-f="전체">전체</button>' + "".join(
        f'<button type="button" aria-pressed="false" data-f="{e(cat)}">{e(cat)}</button>'
        for cat in CATS if any(c["cat"] == cat for c in r["cards"]))
    avg_col = chg_color(r["avg"])
    mine_html = mine_section(r)
    off_html = (f'<div class="muted" style="font-size:14px;padding:0 4px">제철이 아니라 오늘 거래가 없는 품목: {e(", ".join(r["off"]))}</div>'
                if r.get("off") else "")
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(date_label(r['ymd']))} 농산물 시세</title>{FONT}<style>{CSS}</style></head>
<body><div class="wrap">
<header style="display:flex;flex-direction:column;gap:6px;padding:8px 4px">
<span style="font-size:14px;font-weight:700;color:#2F6B3A">오늘의 시세</span>
<h1>{e(date_label(r['ymd']))} 농산물 시세</h1>
<div class="muted" style="font-size:15px">전국 공영도매시장 정산 가격 · 전 거래일 대비 · {r['item_count']}개 품목 · 품목별 기준 등급으로 비교</div>
</header>
{mine_html}
<section class="dark"><div style="font-size:14px;color:#D6D3CC">오늘 한 줄 요약</div>
<div style="font-size:20px;font-weight:700;line-height:1.5;margin-top:6px">{e(r['headline'])}</div></section>
<section class="kpis">
<div class="kpi"><span class="muted" style="font-size:14px">오른 품목</span><b style="color:{UP}">{r['up_count']}개</b></div>
<div class="kpi"><span class="muted" style="font-size:14px">내린 품목</span><b style="color:{DOWN}">{r['down_count']}개</b></div>
<div class="kpi"><span class="muted" style="font-size:14px">평균 등락</span><b style="color:{avg_col}">{chg_text(r['avg'], False)}</b></div>
</section>
<details class="note"><summary>이 보고서 보는 법</summary>
<div style="padding-top:8px"><b>등락은 품목마다 정한 기준 등급 하나로만 계산해요.</b><br>
여러 등급을 섞어 평균을 내면, 그날 좋은 등급이 많이 나왔을 뿐인데 값이 오른 것처럼 보이기 때문이에요.
가격은 포장 단위가 달라도 비교할 수 있게 kg당 가격으로 바꾼 뒤 기준 단위로 환산했어요.
카드의 ⚠ 표시는 등급 값이 거꾸로 됐거나 하루 25% 넘게 움직인 품목이에요. 카드를 펼치면 이유가 나와요.</div></details>
<details class="box sec" open><summary><h2>등락률 순위</h2></summary>
<div class="muted" style="font-size:14px;margin-bottom:10px">가운데 선 오른쪽은 오름, 왼쪽은 내림이에요. 기준 등급 거래가 1톤 미만인 품목({r.get('thin_count', 0)}개)은 값이 쉽게 튀어서 순위에서 뺐어요.</div>
{rank_html or '<div class="muted">전일 데이터가 쌓이면 표시돼요.</div>'}
</details>
<section style="display:flex;flex-direction:column;gap:12px">
<div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:10px;padding:8px 4px 0">
<h2>품목별 시세와 흐름</h2>
<div class="tabs" role="group" aria-label="품목 분류">
{tab_btns}
</div></div>
<div style="display:flex;justify-content:flex-end;padding:0 4px"><button type="button" id="toggleAll" class="ghost">모두 펼치기</button></div>
<div class="grid">{''.join(cards)}</div>
{off_html}
</section>
{feat}
<footer>출처: 한국농수산식품유통공사 전국 공영도매시장 정산정보 (공공데이터포털)<br>
도매시장 경락 가격이라 소매 가격과는 달라요. 전날 정산이 다 들어오면 아침에 자동으로 바뀝니다.</footer>
</div>
<script>
document.querySelectorAll('.tabs button').forEach(function(b){{b.addEventListener('click',function(){{
var f=b.dataset.f;document.querySelectorAll('.tabs button').forEach(function(x){{x.setAttribute('aria-pressed',x===b?'true':'false')}});
document.querySelectorAll('.card').forEach(function(c){{c.style.display=(f==='전체'||c.dataset.cat===f)?'':'none'}});}})}});
var tg=document.getElementById('toggleAll');tg.addEventListener('click',function(){{
var open=tg.textContent==='모두 펼치기';document.querySelectorAll('.card details.more').forEach(function(d){{d.open=open}});
tg.textContent=open?'모두 접기':'모두 펼치기';}});
</script></body></html>"""


def tone(c):
    if c is None:
        return "#ECE9E1", "#1C1B19"
    if c >= 10:
        return "#C62828", "#FFFFFF"
    if c >= 5:
        return "#E57373", "#1C1B19"
    if c > 0:
        return "#F6C9C9", "#1C1B19"
    if c == 0:
        return "#ECE9E1", "#1C1B19"
    if c > -5:
        return "#C9D9F2", "#1C1B19"
    if c > -10:
        return "#7FA3DC", "#1C1B19"
    return "#1E5BB8", "#FFFFFF"


def card_html(r):
    top = r["ranked"][0] if r["ranked"] and r["ranked"][0]["chg"] > 0 else None
    maxabs = max([abs(c["chg"]) for c in r["ranked"]] or [1]) or 1

    def rows(lst, col):
        out = []
        for c in lst[:3]:
            out.append(f'<div style="display:grid;grid-template-columns:84px 1fr 84px;align-items:center;gap:8px;font-size:17px">'
                       f'<b>{e(c["name"])}</b><div style="height:12px;background:#F4F2EC;border-radius:6px;overflow:hidden">'
                       f'<div style="height:12px;border-radius:6px;width:{abs(c["chg"]) / maxabs * 100:.0f}%;background:{col}"></div></div>'
                       f'<b style="text-align:right;color:{col}">{chg_text(c["chg"])}</b></div>')
        return "".join(out) or '<div style="font-size:15px;color:#55524B">해당 품목 없음</div>'

    mine = r.get("mine", [])[:3]
    shown = r.get("by_volume", [c for c in r["cards"] if not c["missing"]])[:12 if mine else 24]
    mine_rows = "".join(
        f'<div style="display:grid;grid-template-columns:150px 1fr auto;align-items:center;gap:12px;padding:8px 0;border-top:{"0" if i == 0 else "1px solid #ECE9E1"}">'
        f'<div><div style="font-size:26px;font-weight:900;line-height:1.1">{e(m["name"])}</div><div style="font-size:14px;color:#55524B">{e(m["base"])} · {m["unit_kg"]:g}kg</div></div>'
        f'<div style="font-size:30px;font-weight:900">{won(m["price"])} <span style="font-size:22px;color:{chg_color(m["chg"])}">{chg_text(m["chg"])}</span></div>'
        f'<div style="text-align:right;font-size:16px;line-height:1.35;color:#2F4A28">{("최고 <b>" + e(m["best"]["market"]) + "</b><br>" + won(m["best"]["price"])) if m["best"] else ""}</div></div>'
        for i, m in enumerate(mine))
    mine_box = (f'<div style="background:#fff;border:3px solid #2F6B3A;border-radius:18px;padding:10px 20px">'
                f'<div style="font-size:16px;font-weight:700;color:#2F6B3A;margin-bottom:2px">내 품목</div>{mine_rows}</div>') if mine else ""
    cols = 6
    tiles = []
    for c in shown:
        bg, fg = tone(c["chg"])
        tiles.append(f'<div style="height:54px;border-radius:10px;background:{bg};color:{fg};display:flex;flex-direction:column;align-items:center;justify-content:center">'
                     f'<b style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px">{e(c["name"].split("(")[0])}</b><span style="font-size:13px">{chg_text(c["chg"], False)}</span></div>')
    top_box = (f'<div style="font-size:15px;color:#D6D3CC">가장 많이 오른</div><div style="font-size:28px;font-weight:900">{e(top["name"])}</div>'
               f'<div style="font-size:20px;font-weight:700;color:#FF8A80">{chg_text(top["chg"])}</div>') if top else \
        '<div style="font-size:15px;color:#D6D3CC">가장 많이 오른</div><div style="font-size:22px;font-weight:900">없음</div>'
    legend = "".join(f'<span style="width:14px;height:10px;border-radius:2px;background:{c}"></span>'
                     for c in ["#1E5BB8", "#7FA3DC", "#C9D9F2", "#F6C9C9", "#E57373", "#C62828"])
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">{FONT}
<style>body{{margin:0}}</style></head><body>
<div id="card" style="width:800px;height:800px;box-sizing:border-box;background:#F4F2EC;padding:36px;display:flex;flex-direction:column;gap:16px;font-family:'Noto Sans KR',sans-serif;color:#1C1B19">
<div style="display:flex;justify-content:space-between;align-items:flex-end">
<div><div style="font-size:18px;font-weight:700;color:#2F6B3A">오늘의 농산물 시세</div>
<div style="font-size:46px;font-weight:900;line-height:1.1;letter-spacing:-.02em">{e(date_label(r['ymd'], short=True))}</div></div>
<div style="text-align:right;font-size:15px;line-height:1.5;color:#55524B">전국 공영도매시장 정산 가격<br>전일 대비 · {r['item_count']}개 품목</div></div>
{mine_box}
<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px">
<div style="background:#fff;border-radius:16px;padding:16px 18px"><div style="font-size:15px;color:#55524B">오른 품목</div>
<div style="font-size:44px;font-weight:900;line-height:1.1;color:{UP}">{r['up_count']}<span style="font-size:20px">개</span></div></div>
<div style="background:#fff;border-radius:16px;padding:16px 18px"><div style="font-size:15px;color:#55524B">내린 품목</div>
<div style="font-size:44px;font-weight:900;line-height:1.1;color:{DOWN}">{r['down_count']}<span style="font-size:20px">개</span></div></div>
<div style="background:#1C1B19;color:#fff;border-radius:16px;padding:16px 18px">{top_box}</div></div>
<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px">
<div style="background:#fff;border-radius:16px;padding:14px 18px;display:flex;flex-direction:column;gap:8px"><b style="font-size:16px;color:{UP}">상승 TOP 3</b>{rows(r['ups'], UP)}</div>
<div style="background:#fff;border-radius:16px;padding:14px 18px;display:flex;flex-direction:column;gap:8px"><b style="font-size:16px;color:{DOWN}">하락 TOP 3</b>{rows(r['downs'], DOWN)}</div></div>
<div style="display:{"none" if mine else "flex"};flex-direction:column;gap:8px">
<div style="display:flex;justify-content:space-between;align-items:center"><b style="font-size:16px">거래 많은 {len(shown)}개 품목 등락</b>
<div style="display:flex;align-items:center;gap:4px;font-size:12px;color:#55524B">크게 내림 {legend} 크게 오름</div></div>
<div style="display:grid;grid-template-columns:repeat({cols},minmax(0,1fr));gap:6px">{''.join(tiles)}</div></div>
<div style="margin-top:auto;display:flex;justify-content:space-between;font-size:13px;color:#55524B">
<span>품목별 기준 등급 비교 · 출처 한국농수산식품유통공사</span><span>{f"⚠ 이상거래 {len(r.get('flagged', []))}건 분석 · " if r.get("flagged") else ""}전체 {r['item_count']}개는 링크에서</span></div>
</div></body></html>"""


def write_all(r, png=True):
    """docs/ 에 index.html, card.html, card-날짜.png 를 씁니다. PNG 경로(또는 None)를 돌려줍니다."""
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(report_html(r), encoding="utf-8")
    day_html = DOCS / "days" / f"{r['ymd']}.html"
    day_html.parent.mkdir(exist_ok=True)
    day_html.write_text(report_html(r).replace('src="art/', 'src="../art/'), encoding="utf-8")
    card = DOCS / "card.html"
    card.write_text(card_html(r), encoding="utf-8")
    if not png:
        return None
    out = DOCS / "cards" / f"card-{r['ymd']}.png"
    out.parent.mkdir(exist_ok=True)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        import os
        exe = os.environ.get("CHROME_PATH")
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page(viewport={"width": 800, "height": 800}, device_scale_factor=1)
        page.goto(card.as_uri())
        page.wait_for_timeout(1500)
        page.locator("#card").screenshot(path=str(out))
        browser.close()
    return out


def public_urls(r):
    base = SITE_URL.rstrip("/") + "/"
    return {"report": base + f"days/{r['ymd']}.html", "card": base + f"cards/card-{r['ymd']}.png"}
