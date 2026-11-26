"""보고서 HTML(웹 리포트)과 카톡용 카드 이미지(800x800 PNG)를 만듭니다."""
import html
from datetime import datetime
from pathlib import Path

from .config import SITE_URL
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
body{margin:0;background:#F4F2EC;font-family:'Noto Sans KR',sans-serif;color:#1C1B19}
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
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.card{position:relative;isolation:isolate;overflow:hidden;background:#fff;border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:8px}
.card .art{position:absolute;z-index:-1;right:-18px;top:30px;width:136px;height:136px;opacity:.2;pointer-events:none}
.tag{align-self:flex-start;font-size:12px;font-weight:500;color:#2F4A28;background:#EEF4EC;border-radius:6px;padding:2px 8px}
.price{font-size:24px;font-weight:900}
.chip{font-size:14px;font-weight:700;border-radius:999px;padding:2px 10px;white-space:nowrap}
.spark{width:100%;height:44px}
.nospark{font-size:12px;color:#55524B;height:44px;display:flex;align-items:center}
.ladder{border-top:1px solid #ECE9E1;padding-top:10px;display:flex;flex-direction:column;gap:5px}
.lrow{display:grid;grid-template-columns:34px minmax(0,1fr) 72px;align-items:center;gap:8px;font-size:13px}
.track{height:10px;background:#F4F2EC;border-radius:5px;overflow:hidden}
.mrow{display:grid;grid-template-columns:64px minmax(0,1fr) 84px;align-items:center;gap:10px;font-size:15px;font-weight:700}
.mtrack{height:24px;background:#F4F2EC;border-radius:6px;overflow:hidden}
footer{font-size:13px;line-height:1.7;color:#55524B;padding:8px 4px}
@media (max-width:480px){h1{font-size:26px}.kpi b{font-size:26px}}
"""


def report_html(r):
    maxabs = max([abs(c["chg"]) for c in r["ranked"]] or [1]) or 1
    rank_rows = []
    for c in r["ranked"]:
        w = abs(c["chg"]) / maxabs * 100
        neg = f'<div style="height:16px;border-radius:4px 0 0 4px;background:{DOWN};width:{w:.1f}%"></div>' if c["chg"] < 0 else ""
        pos = f'<div style="height:16px;border-radius:0 4px 4px 0;background:{UP};width:{w:.1f}%"></div>' if c["chg"] > 0 else ""
        rank_rows.append(
            f'<div class="rank"><div class="nm"><span>{e(c["name"])}</span><span>{e(spec(c))}</span></div>'
            f'<div style="display:flex"><div class="half l">{neg}</div><div class="half">{pos}</div></div>'
            f'<div style="font-size:15px;font-weight:700;text-align:right;color:{chg_color(c["chg"])}">{chg_text(c["chg"])}</div></div>')

    cards = []
    for c in r["cards"]:
        art = f'<img class="art" src="art/{e(c["art"])}.svg" alt="" aria-hidden="true">'
        if c["missing"]:
            cards.append(f'<article class="card" data-cat="{e(c["cat"])}">{art}<div style="font-size:17px;font-weight:900">{e(c["name"])}</div>'
                         f'<div class="muted" style="font-size:14px">오늘은 거래 기록이 없어요.</div></article>')
            continue
        top = max(l["price"] for l in c["ladder"]) or 1
        ladder = "".join(
            f'<div class="lrow"><span style="font-weight:700;color:{"#2F6B3A" if l["base"] else "#55524B"}">{e(l["grade"])}</span>'
            f'<div class="track"><div style="height:10px;border-radius:5px;width:{l["price"] / top * 100:.0f}%;background:{"#2F6B3A" if l["base"] else "#B9CDB3"}"></div></div>'
            f'<span style="text-align:right;font-weight:{700 if l["base"] else 400}">{won(l["price"])}</span></div>'
            for l in c["ladder"])
        chip_bg = "#FDECEC" if (c["chg"] or 0) > 0 else ("#EAF0FA" if (c["chg"] or 0) < 0 else "#ECE9E1")
        hl = ""
        if c["hi"] and c["lo"]:
            hl = (f'<div style="display:flex;justify-content:space-between;font-size:12px" class="muted">'
                  f'<span>최고 {e(c["hi"][0])} {won(c["hi"][1])}</span><span>최저 {e(c["lo"][0])} {won(c["lo"][1])}</span></div>')
        cards.append(
            f'<article class="card" data-cat="{e(c["cat"])}">{art}'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline"><div style="font-size:17px;font-weight:900">{e(c["name"])}</div>'
            f'<div class="muted" style="font-size:12px">{e(c["cat"])}</div></div>'
            f'<div class="tag">기준 {e(spec(c))}</div>'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px"><div class="price">{won(c["price"])}</div>'
            f'<div class="chip" style="background:{chip_bg};color:{chg_color(c["chg"])}">{chg_text(c["chg"])}</div></div>'
            f'<div class="muted" style="font-size:13px;margin-top:-4px">kg당 {won(c["per_kg"])} · 거래 {c["volume_t"]:.1f}톤</div>'
            f'{spark_svg(c)}<div class="ladder"><div style="font-size:13px;font-weight:700">등급별 가격</div>{ladder}</div>{hl}</article>')

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
        feat = (f'<section class="box"><h2>시장별로 비교하면 · {e(f["name"])} {e(spec(f))}</h2>'
                f'<div class="muted" style="font-size:14px;margin-bottom:6px">거래량이 많은 시장만 골랐어요. 출하할 시장을 고를 때 보세요.</div>{rows}{gap}</section>')

    avg_col = chg_color(r["avg"])
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(date_label(r['ymd']))} 농산물 시세</title>{FONT}<style>{CSS}</style></head>
<body><div class="wrap">
<header style="display:flex;flex-direction:column;gap:6px;padding:8px 4px">
<span style="font-size:14px;font-weight:700;color:#2F6B3A">오늘의 시세</span>
<h1>{e(date_label(r['ymd']))} 농산물 시세</h1>
<div class="muted" style="font-size:15px">전국 공영도매시장 정산 가격 · 전일 대비 · {r['item_count']}개 품목 · 품목별 기준 등급으로 비교</div>
</header>
<section class="dark"><div style="font-size:14px;color:#D6D3CC">오늘 한 줄 요약</div>
<div style="font-size:20px;font-weight:700;line-height:1.5;margin-top:6px">{e(r['headline'])}</div></section>
<section class="kpis">
<div class="kpi"><span class="muted" style="font-size:14px">오른 품목</span><b style="color:{UP}">{r['up_count']}개</b></div>
<div class="kpi"><span class="muted" style="font-size:14px">내린 품목</span><b style="color:{DOWN}">{r['down_count']}개</b></div>
<div class="kpi"><span class="muted" style="font-size:14px">평균 등락</span><b style="color:{avg_col}">{chg_text(r['avg'], False)}</b></div>
</section>
<section class="note"><b>등락은 품목마다 정한 기준 등급 하나로만 계산해요.</b><br>
여러 등급을 섞어 평균을 내면, 그날 좋은 등급이 많이 나왔을 뿐인데 값이 오른 것처럼 보이기 때문이에요.
가격은 포장 단위가 달라도 비교할 수 있게 kg당 가격으로 바꾼 뒤 기준 단위로 환산했어요.</section>
<section class="box"><h2>등락률 순위</h2>
<div class="muted" style="font-size:14px;margin-bottom:10px">가운데 선 오른쪽은 오름, 왼쪽은 내림이에요.</div>
{''.join(rank_rows) or '<div class="muted">전일 데이터가 쌓이면 표시돼요.</div>'}
</section>
<section style="display:flex;flex-direction:column;gap:12px">
<div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:10px;padding:8px 4px 0">
<h2>품목별 시세와 흐름</h2>
<div class="tabs" role="group" aria-label="품목 분류">
<button type="button" aria-pressed="true" data-f="전체">전체</button><button type="button" aria-pressed="false" data-f="채소">채소</button>
<button type="button" aria-pressed="false" data-f="과일">과일</button><button type="button" aria-pressed="false" data-f="특작">특작</button>
</div></div>
<div class="grid">{''.join(cards)}</div>
</section>
{feat}
<footer>출처: 한국농수산식품유통공사 전국 공영도매시장 정산정보 (공공데이터포털)<br>
도매시장 경락 가격이라 소매 가격과는 달라요. 매일 아침 자동으로 바뀝니다.</footer>
</div>
<script>
document.querySelectorAll('.tabs button').forEach(function(b){{b.addEventListener('click',function(){{
var f=b.dataset.f;document.querySelectorAll('.tabs button').forEach(function(x){{x.setAttribute('aria-pressed',x===b?'true':'false')}});
document.querySelectorAll('.card').forEach(function(c){{c.style.display=(f==='전체'||c.dataset.cat===f)?'':'none'}});}})}});
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

    shown = [c for c in r["cards"] if not c["missing"]][:18]
    cols = 6
    tiles = []
    for c in shown:
        bg, fg = tone(c["chg"])
        tiles.append(f'<div style="height:66px;border-radius:10px;background:{bg};color:{fg};display:flex;flex-direction:column;align-items:center;justify-content:center">'
                     f'<b style="font-size:14px;white-space:nowrap">{e(c["name"])}</b><span style="font-size:13px">{chg_text(c["chg"], False)}</span></div>')
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
<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px">
<div style="background:#fff;border-radius:16px;padding:16px 18px"><div style="font-size:15px;color:#55524B">오른 품목</div>
<div style="font-size:44px;font-weight:900;line-height:1.1;color:{UP}">{r['up_count']}<span style="font-size:20px">개</span></div></div>
<div style="background:#fff;border-radius:16px;padding:16px 18px"><div style="font-size:15px;color:#55524B">내린 품목</div>
<div style="font-size:44px;font-weight:900;line-height:1.1;color:{DOWN}">{r['down_count']}<span style="font-size:20px">개</span></div></div>
<div style="background:#1C1B19;color:#fff;border-radius:16px;padding:16px 18px">{top_box}</div></div>
<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px">
<div style="background:#fff;border-radius:16px;padding:14px 18px;display:flex;flex-direction:column;gap:8px"><b style="font-size:16px;color:{UP}">상승 TOP 3</b>{rows(r['ups'], UP)}</div>
<div style="background:#fff;border-radius:16px;padding:14px 18px;display:flex;flex-direction:column;gap:8px"><b style="font-size:16px;color:{DOWN}">하락 TOP 3</b>{rows(r['downs'], DOWN)}</div></div>
<div style="display:flex;flex-direction:column;gap:8px">
<div style="display:flex;justify-content:space-between;align-items:center"><b style="font-size:16px">품목별 등락 한눈에</b>
<div style="display:flex;align-items:center;gap:4px;font-size:12px;color:#55524B">크게 내림 {legend} 크게 오름</div></div>
<div style="display:grid;grid-template-columns:repeat({cols},minmax(0,1fr));gap:6px">{''.join(tiles)}</div></div>
<div style="margin-top:auto;display:flex;justify-content:space-between;font-size:13px;color:#55524B">
<span>품목별 기준 등급 비교 · 출처 한국농수산식품유통공사</span><span>자세한 그래프는 링크에서</span></div>
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
