"""받아온 거래 데이터를 품목·등급·시장별 kg당 가격으로 정리합니다.

같은 품목도 포장 단위가 섞여 있어서, 모든 가격을 '총가격 ÷ 총물량(kg)'으로 kg당 가격으로 바꾼 뒤
보고서의 기준 포장 단위(config 의 unit_kg)로 다시 곱합니다.
등락은 품목마다 '기준 등급' 하나로만 비교합니다. 여러 등급을 섞으면 그날 특품이 많이 나왔을 뿐인데
값이 오른 것처럼 보이는 착시가 생기기 때문입니다.
"""
from collections import defaultdict

from .config import ITEMS, GRADE_ORDER, FEATURED


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _match(item, row):
    if (row.get("gds_mclsf_nm") or "").strip() != item["mid"]:
        return False
    small = item.get("small")
    return not small or small in (row.get("gds_sclsf_nm") or "")


def catalog(rows):
    """API에 실제로 나온 품목 이름 목록 (mid / small 을 고칠 때 참고)."""
    seen = defaultdict(int)
    for r in rows:
        seen[f"{r.get('gds_mclsf_nm')} / {r.get('gds_sclsf_nm')}"] += 1
    return dict(sorted(seen.items(), key=lambda kv: -kv[1]))


def summarize(rows):
    """하루치 원자료 → 품목별 {등급: kg당 가격·물량}, {등급: {시장: kg당 가격·물량}}"""
    acc = {}
    for item in ITEMS:
        acc[item["name"]] = {"g": defaultdict(lambda: [0.0, 0.0]), "m": defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))}
    for r in rows:
        if str(r.get("unit_nm") or "").strip().lower() != "kg":
            continue
        kg = _num(r.get("unit_tot_qty"))
        won = _num(r.get("totprc"))
        if kg <= 0 or won <= 0:
            continue
        grade = (r.get("grd_nm") or "등급없음").strip()
        market = (r.get("whsl_mrkt_nm") or "?").replace("도매시장", "").replace("농수산물", "").replace("공판장", "").strip() or "?"
        for item in ITEMS:
            if _match(item, r):
                a = acc[item["name"]]
                a["g"][grade][0] += won
                a["g"][grade][1] += kg
                a["m"][grade][market][0] += won
                a["m"][grade][market][1] += kg
                break
    out = {}
    for name, a in acc.items():
        if not a["g"]:
            continue
        out[name] = {
            "grades": {g: {"per_kg": w / k, "kg": k} for g, (w, k) in a["g"].items() if k > 0},
            "markets": {g: {m: {"per_kg": w / k, "kg": k} for m, (w, k) in mk.items() if k > 0}
                        for g, mk in a["m"].items()},
        }
    return out


def josa(word, batchim, plain):
    """받침이 있으면 batchim, 없으면 plain (예: 딸기가 / 밤이)."""
    ch = word[-1]
    if "가" <= ch <= "힣":
        return word + (batchim if (ord(ch) - 0xAC00) % 28 else plain)
    return word + plain


def _grade_rank(g):
    for i, name in enumerate(GRADE_ORDER):
        if g == name:
            return i
    return len(GRADE_ORDER)


def _base_grade(item, s):
    if item.get("grade") and item["grade"] in s["grades"]:
        return item["grade"]
    return max(s["grades"].items(), key=lambda kv: kv[1]["kg"])[0]


def build(today_ymd, today, prev, history):
    """보고서에 넣을 값 만들기.

    today/prev: summarize() 결과. history: [(ymd, summary), ...] 오래된 날부터, 오늘 포함.
    """
    cards = []
    for item in ITEMS:
        s = today.get(item["name"])
        if not s:
            cards.append({**item, "missing": True})
            continue
        base = _base_grade(item, s)
        per_kg = s["grades"][base]["per_kg"]
        price = per_kg * item["unit_kg"]

        chg = None
        if prev and item["name"] in prev and base in prev[item["name"]]["grades"]:
            p = prev[item["name"]]["grades"][base]["per_kg"]
            if p > 0:
                chg = (per_kg / p - 1) * 100

        ladder = sorted(s["grades"].items(), key=lambda kv: (_grade_rank(kv[0]), -kv[1]["per_kg"]))
        ladder = [{"grade": g, "price": v["per_kg"] * item["unit_kg"], "base": g == base} for g, v in ladder[:4]]

        spark = []
        for ymd, hs in history:
            v = hs.get(item["name"], {}).get("grades", {}).get(base)
            if v:
                spark.append((ymd, v["per_kg"] * item["unit_kg"]))

        mk = s["markets"].get(base, {})
        total = sum(v["kg"] for v in mk.values()) or 1
        main_mk = [(m, v["per_kg"] * item["unit_kg"], v["kg"]) for m, v in mk.items() if v["kg"] / total >= 0.03]
        main_mk.sort(key=lambda x: -x[2])
        main_mk = sorted(main_mk[:6], key=lambda x: -x[1])
        hi = main_mk[0] if main_mk else None
        lo = main_mk[-1] if len(main_mk) > 1 else None

        cards.append({
            **item,
            "missing": False,
            "base": base,
            "price": price,
            "per_kg": per_kg,
            "chg": chg,
            "volume_t": s["grades"][base]["kg"] / 1000,
            "ladder": ladder,
            "spark": spark,
            "markets": main_mk,
            "hi": hi,
            "lo": lo,
        })

    priced = [c for c in cards if not c["missing"] and c["chg"] is not None]
    ups = sorted([c for c in priced if c["chg"] > 0], key=lambda c: -c["chg"])
    downs = sorted([c for c in priced if c["chg"] < 0], key=lambda c: c["chg"])
    flat = [c for c in priced if c["chg"] == 0]
    avg = sum(c["chg"] for c in priced) / len(priced) if priced else 0.0

    parts = []
    if ups:
        names = "·".join(c["name"] for c in ups[:2])
        parts.append(f"{josa(names, '이', '가')} 크게 올랐어요")
    if downs:
        names = "·".join(c["name"] for c in downs[:2])
        parts.append(f"{josa(names, '은', '는')} 내림세예요")
    headline = ". ".join(parts) + "." if parts else "전일과 비교할 데이터가 아직 없어요. 내일부터 등락이 표시돼요."

    featured = next((c for c in cards if c["name"] == FEATURED and not c["missing"]), None)

    return {
        "ymd": today_ymd,
        "cards": cards,
        "ranked": sorted(priced, key=lambda c: -c["chg"]),
        "ups": ups,
        "downs": downs,
        "up_count": len(ups),
        "down_count": len(downs),
        "flat_count": len(flat),
        "avg": avg,
        "headline": headline,
        "featured": featured,
        "item_count": len([c for c in cards if not c["missing"]]),
    }
