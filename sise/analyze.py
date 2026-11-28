"""받아온 거래 데이터를 품목·등급·시장별 kg당 가격으로 정리하고, 이상거래를 찾아 설명을 붙입니다.

같은 품목도 포장 단위가 섞여 있어서, 모든 가격을 '총가격 ÷ 총물량(kg)'으로 kg당 가격으로 바꾼 뒤
보고서의 기준 포장 단위(config 의 unit_kg, 없으면 그날 가장 많이 거래된 포장)로 다시 곱합니다.
등락은 품목마다 '기준 등급' 하나로만 비교합니다. 여러 등급을 섞으면 그날 특품이 많이 나왔을 뿐인데
값이 오른 것처럼 보이는 착시가 생기기 때문입니다.
"""
import hashlib
import json
import re
from collections import defaultdict
from statistics import median

from .config import ITEMS, GRADE_ORDER, FEATURED, NO_GRADE, CATS, MY, THIN_KG

# 품목 목록이 바뀌면 저장해 둔 요약을 다시 받도록 표시하는 값
SIG = hashlib.md5(json.dumps([[i["name"], i["mid"], i.get("small"), i.get("exclude")] for i in ITEMS],
                             ensure_ascii=False).encode()).hexdigest()[:10] + "-v4"


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _match(item, row):
    if (row.get("gds_mclsf_nm") or "").strip() != item["mid"]:
        return False
    small = row.get("gds_sclsf_nm") or ""
    if "수입" in small:
        return False
    if any(x in small for x in item.get("exclude", [])):
        return False
    return not item.get("small") or item["small"] in small


def grade_name(raw):
    g = (raw or "").strip()
    if not re.search(r"[0-9A-Za-z가-힣]", g) or g in ("등급없음", "무등급", "기타", "없음"):
        return NO_GRADE
    return g


def catalog(rows):
    """API에 실제로 나온 품목 이름 목록 (mid / small 을 고칠 때 참고)."""
    seen = defaultdict(int)
    for r in rows:
        seen[f"{r.get('gds_mclsf_nm')} / {r.get('gds_sclsf_nm')}"] += 1
    return dict(sorted(seen.items(), key=lambda kv: -kv[1]))


def _new():
    return {"won": 0.0, "kg": 0.0, "n": 0, "pack": defaultdict(float), "var": defaultdict(float), "size": defaultdict(float),
            "by": {"vars": defaultdict(lambda: [0.0, 0.0]), "corp": defaultdict(lambda: [0.0, 0.0]),
                   "org": defaultdict(lambda: [0.0, 0.0])}}


def _add(a, won, kg, pack, var=None, size=None, corp=None, org=None):
    a["won"] += won
    a["kg"] += kg
    a["n"] += 1
    if pack > 0:
        a["pack"][f"{pack:g}"] += kg
    if var:
        a["var"][var] += kg
    if size:
        a["size"][size] += kg
    for key, v in (("vars", var), ("corp", corp), ("org", org)):
        if v:
            a["by"][key][v][0] += won
            a["by"][key][v][1] += kg


SIDO = {"전남광주통합특별시": "전남", "전라남도": "전남", "경상남도": "경남", "경상북도": "경북", "전라북도": "전북",
        "전북특별자치도": "전북", "충청북도": "충북", "충청남도": "충남", "강원특별자치도": "강원", "강원도": "강원",
        "경기도": "경기", "제주특별자치도": "제주", "세종특별자치시": "세종"}


def origin_name(raw):
    """출하자 주소 → '시도 시군' (예: '경상남도 하동군 악양면' → '경남 하동군')."""
    o = re.sub(r"\s+", " ", raw or "").strip()
    for k, v in SIDO.items():
        o = o.replace(k, v)
    p = o.split(" ")
    return " ".join(p[:2]) if len(p) >= 2 and p[1] else ""


def _top(d, n=5):
    rows = [[k, round(w / kg), round(kg)] for k, (w, kg) in d.items() if kg > 0]
    return sorted(rows, key=lambda x: -x[2])[:n]


def _share(d, total):
    if not d:
        return None
    k, v = max(d.items(), key=lambda kv: kv[1])
    return [k, round(v / total, 3)]


def _fin(a, detail=False):
    out = {"per_kg": a["won"] / a["kg"], "kg": a["kg"], "n": a["n"]}
    if a["pack"]:
        out["pack"] = float(max(a["pack"].items(), key=lambda kv: kv[1])[0])
    if detail:
        for key in ("vars", "corp", "org"):
            if a["by"][key]:
                out[key] = _top(a["by"][key])
        if a["var"]:
            out["var"] = _share(a["var"], a["kg"])
        if a["size"]:
            out["size"] = _share(a["size"], a["kg"])
    return out


def summarize(rows):
    """하루치 원자료 → 품목별 {등급: kg당 가격·물량·건수·주 포장}, {등급: {시장: …}}"""
    acc = {i["name"]: {"g": defaultdict(_new), "m": defaultdict(lambda: defaultdict(_new)), "all": _new(),
                       "mine": _new(), "mine_m": defaultdict(_new)} for i in ITEMS}
    mine_key = MY.get("origin") or ""
    markets = set()
    for r in rows:
        if str(r.get("unit_nm") or "").strip().lower() != "kg":
            continue
        kg = _num(r.get("unit_tot_qty"))
        won = _num(r.get("totprc"))
        if kg <= 0 or won <= 0:
            continue
        pack = _num(r.get("unit_qty"))
        grade = grade_name(r.get("grd_nm"))
        var = (r.get("gds_sclsf_nm") or "").strip()
        size = (r.get("sz_nm") or "").strip()
        if not re.search(r"[0-9A-Za-z가-힣]", size) or size in ("기타", "없음", "무"):
            size = ""
        corp = (r.get("corp_nm") or "").strip()
        org = origin_name(r.get("plor_nm"))
        market = (r.get("whsl_mrkt_nm") or "?").replace("도매시장", "").replace("농수산물", "").replace("공판장", "").strip() or "?"
        markets.add(market)
        for item in ITEMS:
            if _match(item, r):
                a = acc[item["name"]]
                _add(a["g"][grade], won, kg, pack, var, size, corp, org)
                _add(a["m"][grade][market], won, kg, pack)
                _add(a["all"], won, kg, pack)
                if mine_key and mine_key in (r.get("plor_nm") or ""):
                    _add(a["mine"], won, kg, pack)
                    _add(a["mine_m"][market], won, kg, pack)
                break
    out = {"_sig": SIG, "_markets": len(markets),
           "_kg": sum(a["all"]["kg"] for a in acc.values())}
    for name, a in acc.items():
        if not a["g"]:
            continue
        out[name] = {
            "pack": _fin(a["all"]).get("pack"),
            "grades": {g: _fin(v, detail=True) for g, v in a["g"].items() if v["kg"] > 0},
            "markets": {g: {m: _fin(v) for m, v in mk.items() if v["kg"] > 0} for g, mk in a["m"].items()},
        }
        if a["mine"]["kg"] > 0:
            out[name]["mine"] = {"all": _fin(a["mine"]), "m": {m: _fin(v) for m, v in a["mine_m"].items() if v["kg"] > 0}}
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
    return len(GRADE_ORDER) + (1 if g == NO_GRADE else 0)


def _ranked(g):
    return g in GRADE_ORDER


def _base_grade(item, s):
    if item.get("grade") and item["grade"] in s["grades"]:
        return item["grade"]
    named = {g: v for g, v in s["grades"].items() if g != NO_GRADE} or s["grades"]
    return max(named.items(), key=lambda kv: kv[1]["kg"])[0]


def _t(kg):
    return f"{kg / 1000:.1f}톤" if kg >= 1000 else f"{kg:,.0f}kg"


def _pct(x):
    return f"{x * 100:.0f}%"


# ── 이상거래 분석 ───────────────────────────────────────────────

def _inversion_note(name, hi_g, lo_g, s, unit):
    """아래 등급이 위 등급보다 비쌀 때, 왜 그런지 자료에서 이유를 찾습니다."""
    G, M = s["grades"], s["markets"]
    hi, lo = G[hi_g], G[lo_g]
    total = sum(v["kg"] for v in G.values()) or 1
    gap = lo["per_kg"] / hi["per_kg"] - 1
    reasons = []

    share = lo["kg"] / total
    if share < 0.03 or lo["n"] <= 3:
        reasons.append(f"{lo_g} 등급은 거래가 {lo['n']}건·{_t(lo['kg'])}(전체의 {_pct(share)})뿐이라 몇 건의 값이 평균을 좌우했어요")

    hv, lv = hi.get("var"), lo.get("var")
    if hv and lv and hv[0] != lv[0] and lv[1] >= 0.4:
        reasons.append(f"{lo_g} 등급은 {lv[0]} 품종이 {_pct(lv[1])}이고, {josa(hi_g, '은', '는')} {hv[0]} 품종이 {_pct(hv[1])}예요. "
                       f"품종이 달라 값 차이가 생겼어요")
    hz, lz = hi.get("size"), lo.get("size")
    if hz and lz and hz[0] != lz[0] and lz[1] >= 0.4:
        reasons.append(f"{lo_g} 등급은 주로 '{lz[0]}' 크기({_pct(lz[1])}), {josa(hi_g, '은', '는')} 주로 '{hz[0]}' 크기({_pct(hz[1])})로 거래됐어요. "
                       f"크기가 달라 등급보다 크기 값이 더 크게 반영됐을 수 있어요")
    if hi.get("pack") and lo.get("pack") and lo["pack"] < hi["pack"] * 0.6:
        reasons.append(f"{lo_g} 등급은 주로 {lo['pack']:g}kg 소포장으로 거래됐어요. 작은 포장은 kg당 값이 높게 나와요"
                       f"({josa(hi_g, '은', '는')} 주로 {hi['pack']:g}kg)")

    common = [m for m in M.get(lo_g, {}) if m in M.get(hi_g, {})]
    if common:
        lo_w = sum(M[lo_g][m]["kg"] for m in common) or 1
        same_hi = sum(M[hi_g][m]["per_kg"] * M[lo_g][m]["kg"] for m in common) / lo_w
        same_lo = sum(M[lo_g][m]["per_kg"] * M[lo_g][m]["kg"] for m in common) / lo_w
        if same_hi >= same_lo:
            top_m, top_v = max(M[lo_g].items(), key=lambda kv: kv[1]["kg"])
            mshare = top_v["kg"] / (lo["kg"] or 1)
            diff = same_hi / same_lo - 1
            tail = (f"같은 시장끼리 비교하면 {josa(hi_g, '이', '가')} {lo_g}보다 {_pct(diff)} 비싸요" if diff >= 0.03
                    else "같은 시장끼리 비교하면 두 등급 값이 거의 같아요")
            reasons.append(f"{lo_g} 등급은 {top_m} 거래가 {_pct(mshare)}로 몰려 있어 시장 구성이 달라요. {tail}")
        elif not reasons:
            reasons.append("같은 시장 안에서도 아래 등급이 더 비싸요. 품종·크기·포장은 비슷해서, 시장(법인)마다 등급을 매기는 기준이 "
                           "달랐거나 그날 특정 산지 물건이 좋게 평가된 것으로 보여요")
    elif not reasons:
        reasons.append(f"{josa(hi_g, '과', '와')} {josa(lo_g, '이', '가')} 서로 다른 시장에서만 거래돼 직접 비교가 어려워요")

    return {"kind": "역전", "grades": [hi_g, lo_g],
            "title": f"{lo_g} 등급이 {hi_g} 등급보다 {_pct(gap)} 비싸요",
            "why": reasons}


def _jump_note(item, base, s, prev_s, chg, unit):
    cur = s["grades"][base]
    old = prev_s["grades"][base]
    reasons = []
    vr = cur["kg"] / old["kg"] if old["kg"] else None
    if vr is not None and chg > 0 and vr < 0.7:
        reasons.append(f"거래량이 전일의 {_pct(vr)}({_t(old['kg'])}→{_t(cur['kg'])})로 줄었어요. 물량이 줄면 값이 뛰기 쉬워요")
    elif vr is not None and chg < 0 and vr > 1.4:
        reasons.append(f"물량이 전일보다 {_pct(vr - 1)} 늘었어요({_t(old['kg'])}→{_t(cur['kg'])}). 반입이 몰리면 값이 내려가요")
    if cur["kg"] < 2000:
        reasons.append(f"하루 거래가 {_t(cur['kg'])}로 적어 등락이 크게 나오는 품목이에요")
    if cur.get("pack") and old.get("pack") and cur["pack"] != old["pack"]:
        reasons.append(f"주로 거래된 포장이 {old['pack']:g}kg→{cur['pack']:g}kg으로 바뀌었어요")

    # 어느 시장이 등락을 이끌었는지
    cm, pm = s["markets"].get(base, {}), prev_s["markets"].get(base, {})
    tot = sum(v["kg"] for v in cm.values()) or 1
    effects = []
    for m, v in cm.items():
        if m in pm and pm[m]["per_kg"] > 0 and v["kg"] / tot >= 0.05:
            effects.append((m, v["per_kg"] / pm[m]["per_kg"] - 1, v["kg"] / tot))
    if effects:
        m, r, w = max(effects, key=lambda x: abs(x[1]) * x[2] if (x[1] > 0) == (chg > 0) else 0)
        if (r > 0) == (chg > 0) and abs(r) >= 0.1:
            reasons.append(f"{m}(물량 {_pct(w)}) 값이 {_pct(abs(r))} {'올라 전체를 끌어올렸어요' if r > 0 else '내려 전체를 끌어내렸어요'}")
        else:
            new = [x for x in cm if x not in pm and cm[x]["kg"] / tot >= 0.15]
            if new:
                reasons.append(f"전일엔 없던 {new[0]} 거래({_pct(cm[new[0]]['kg'] / tot)})가 새로 섞였어요")
    if not reasons:
        reasons.append("대부분 시장에서 함께 움직였어요. 산지 출하량이나 날씨 영향일 가능성이 커요")
    return {"kind": "급등" if chg > 0 else "급락", "grades": [base],
            "title": f"{base} 등급이 하루 만에 {'▲' if chg > 0 else '▼'} {abs(chg):.0f}% 움직였어요",
            "why": reasons}


def _market_note(base, mk, unit):
    tot = sum(v["kg"] for v in mk.values()) or 1
    main = {m: v for m, v in mk.items() if v["kg"] / tot >= 0.03}
    big = {m: v for m, v in main.items() if v["kg"] / tot >= 0.10}
    if len(main) < 3:
        return None
    med = median(v["per_kg"] for v in main.values())
    odd = [(m, v["per_kg"] / med, v) for m, v in big.items() if v["per_kg"] / med >= 2 or v["per_kg"] / med <= 0.5]
    if not odd:
        return None
    m, ratio, v = max(odd, key=lambda x: abs(x[1] - 1))
    side = f"{ratio:.1f}배예요" if ratio > 1 else f"{_pct(ratio)} 수준이에요"
    why = [f"{m} {_t(v['kg'])}·{v['n']}건이 kg당 {v['per_kg']:,.0f}원으로, 다른 시장 가운데값({med:,.0f}원)의 {side}"]
    if v["n"] <= 3:
        why.append("거래가 몇 건뿐이라 특수품(선별품·소포장)이 섞였을 가능성이 커요")
    return {"kind": "시장", "grades": [base], "title": f"{m} 값이 다른 시장과 크게 달라요", "why": why}


def anomalies(item, base, s, prev_s, chg, unit):
    notes = []
    G = s["grades"]
    total = sum(v["kg"] for v in G.values()) or 1
    # 물량이 전체의 5% 이상인 등급끼리만 비교합니다 (몇 건짜리 등급은 원래 들쭉날쭉해서 보고서에서도 숨김)
    ranked = sorted([g for g in G if _ranked(g) and G[g]["kg"] / total >= 0.05], key=_grade_rank)
    for i, lo_g in enumerate(ranked):
        for hi_g in ranked[:i]:
            if G[lo_g]["per_kg"] > G[hi_g]["per_kg"] * 1.12:
                notes.append(_inversion_note(item["name"], hi_g, lo_g, s, unit))
                break
    if NO_GRADE in G and G[NO_GRADE]["kg"] / total >= 0.3:
        notes.append({"kind": "미표기", "grades": [NO_GRADE],
                      "title": f"등급 없이 거래된 물량이 {_pct(G[NO_GRADE]['kg'] / total)}예요",
                      "why": ["시장이 등급을 적지 않은 거래예요. 등급별 비교에서는 빼고 봤어요"]})
    if chg is not None and abs(chg) >= 25 and prev_s and base in prev_s.get("grades", {}):
        notes.append(_jump_note(item, base, s, prev_s, chg, unit))
    mn = _market_note(base, s["markets"].get(base, {}), unit)
    if mn:
        notes.append(mn)
    return notes


# ── 보고서 값 만들기 ─────────────────────────────────────────────

def build(today_ymd, today, prev, history, last_year=None):
    """보고서에 넣을 값 만들기.

    today/prev: summarize() 결과. history: [(ymd, summary), ...] 오래된 날부터, 오늘 포함.
    last_year: 1년 전 같은 요일의 summarize() 결과 (반입량 비교용, 없으면 None).
    """
    cards = []
    for item in ITEMS:
        s = today.get(item["name"])
        if not s:
            cards.append({**item, "missing": True})
            continue
        base = _base_grade(item, s)
        unit = item.get("unit_kg") or s["grades"][base].get("pack") or s.get("pack") or 1
        per_kg = s["grades"][base]["per_kg"]
        price = per_kg * unit
        base_kg = s["grades"][base]["kg"]
        thin = base_kg < THIN_KG

        chg = None
        ps = prev.get(item["name"]) if prev else None
        if ps and base in ps["grades"]:
            p = ps["grades"][base]["per_kg"]
            if p > 0:
                chg = (per_kg / p - 1) * 100

        spark = []
        for ymd, hs in history:
            v = hs.get(item["name"], {}).get("grades", {}).get(base)
            if v:
                spark.append((ymd, v["per_kg"] * unit))

        notes = anomalies(item, base, s, ps, chg, unit)
        # 최근 거래일들의 평소 값과 크게 다르면 원자료 확인 필요
        past = [p for d, p in spark[:-1]]
        if len(past) >= 3:
            med = median(past)
            ratio = price / med if med else 1
            if ratio < 0.6 or ratio > 1.6:
                g = s["grades"][base]
                notes.append({"kind": "확인", "grades": [base],
                              "title": f"최근 거래일 평소 값의 {ratio * 100:.0f}% 수준이에요",
                              "why": [f"최근 {len(past)}거래일 가운데값은 {med:,.0f}원인데 오늘은 {price:,.0f}원이에요(거래 {g['n']}건·{_t(g['kg'])}). "
                                      "품종·포장이 다른 물건이 섞였거나 원자료 분류가 잘못됐을 수 있어 값을 그대로 믿기 전에 확인이 필요해요"]})
        flagged = {g for n in notes if n["kind"] in ("역전", "미표기") for g in n["grades"][-1:]}

        total = sum(v["kg"] for v in s["grades"].values()) or 1
        lad = sorted(s["grades"].items(), key=lambda kv: (_grade_rank(kv[0]), -kv[1]["kg"]))

        def keep(g, v):
            if g == base:
                return True
            share = v["kg"] / total
            if share < 0.03:
                return False
            if g == NO_GRADE and share < 0.10:
                return False          # 등급 없이 거래된 소량은 등급표에서 뺌
            r = v["per_kg"] / per_kg if per_kg else 1
            if v["n"] <= 2 and (r > 2 or r < 0.5):
                return False          # 한두 건짜리 극단값
            return True
        lad = [kv for kv in lad if keep(*kv)][:5]
        ladder = [{"grade": g, "price": v["per_kg"] * unit, "base": g == base, "share": v["kg"] / total,
                   "flag": g in flagged} for g, v in lad]

        mk = s["markets"].get(base, {})
        mt = sum(v["kg"] for v in mk.values()) or 1
        main_mk = [(m, v["per_kg"] * unit, v["kg"]) for m, v in mk.items() if v["kg"] / mt >= 0.03]
        main_mk.sort(key=lambda x: -x[2])
        main_mk = sorted(main_mk[:6], key=lambda x: -x[1])
        hi = main_mk[0] if main_mk else None
        lo = main_mk[-1] if len(main_mk) > 1 else None

        # 반입량: 이 품목 전체 물량의 전 거래일·작년 같은 요일 대비
        def vol(sm):
            it = (sm or {}).get(item["name"])
            return sum(v["kg"] for v in it["grades"].values()) if it else None
        pv, lv = vol(prev), vol(last_year)
        vol_prev = (total / pv - 1) * 100 if pv else None
        vol_ly = (total / lv - 1) * 100 if lv else None

        gb = s["grades"][base]
        cards.append({
            **item,
            "unit_kg": unit,
            "missing": False,
            "base": base,
            "price": price,
            "per_kg": per_kg,
            "chg": chg,
            "thin": thin,
            "volume_t": base_kg / 1000,
            "total_t": total / 1000,
            "vol_prev": vol_prev,
            "vol_ly": vol_ly,
            "ladder": ladder,
            "spark": spark,
            "markets": main_mk,
            "hi": hi,
            "lo": lo,
            "vars": [[n, p * unit, kg] for n, p, kg in gb.get("vars", [])][:3] if len(gb.get("vars", [])) > 1 else [],
            "corps": [[n, p * unit, kg] for n, p, kg in gb.get("corp", [])][:3],
            "orgs": [[n, p * unit, kg] for n, p, kg in gb.get("org", [])][:3],
            "notes": notes,
            "_s": s,
        })

    # 같은 분류 안에서 거래량 많은 순
    cards.sort(key=lambda c: (CATS.index(c["cat"]) if c["cat"] in CATS else 99, c["missing"], -c.get("total_t", 0)))

    priced = [c for c in cards if not c["missing"] and c["chg"] is not None and not c["thin"]]
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

    # ── 내 품목 ──
    by_name = {c["name"]: c for c in cards}
    fee = MY.get("commission") or 0
    freight = MY.get("freight") or {}
    mine, mine_off = [], []
    for name in MY.get("items", []):
        c = by_name.get(name)
        if not c or c["missing"]:
            mine_off.append(name)
            continue
        s_ = c["_s"]
        mk = s_["markets"].get(c["base"], {})
        opts = []
        for m in MY.get("markets", []):
            v = mk.get(m)
            if not v:
                continue
            net_kg = v["per_kg"] * (1 - fee) - (freight.get(m) or 0)
            opts.append({"market": m, "price": v["per_kg"] * c["unit_kg"], "net": net_kg * c["unit_kg"],
                         "kg": v["kg"], "freight": m in freight})
        opts.sort(key=lambda o: -o["net"])
        all_w = sum(v["per_kg"] * v["kg"] for v in s_["grades"].values())
        all_kg = sum(v["kg"] for v in s_["grades"].values()) or 1
        nat = all_w / all_kg
        mo = s_.get("mine")
        origin = None
        if mo:
            mp = mo["all"]["per_kg"]
            top_m = sorted(mo["m"].items(), key=lambda kv: -kv[1]["kg"])[:3]
            origin = {"per_kg": mp, "kg": mo["all"]["kg"], "prem": (mp / nat - 1) * 100,
                      "markets": [[m, v["per_kg"], v["kg"]] for m, v in top_m]}
        mine.append({"name": name, "base": c["base"], "unit_kg": c["unit_kg"], "price": c["price"], "per_kg": c["per_kg"],
                     "chg": c["chg"], "thin": c["thin"], "best": opts[0] if opts else None, "options": opts,
                     "origin": origin, "notes": c["notes"]})

    featured = next((c for c in cards if c["name"] == FEATURED and not c["missing"]), None)
    flagged = [c for c in cards if not c["missing"] and c["notes"]]
    big = sorted([c for c in cards if not c["missing"]], key=lambda c: -c["total_t"])

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
        "flagged": flagged,
        "by_volume": big,
        "item_count": len([c for c in cards if not c["missing"]]),
        "mine": mine,
        "mine_off": mine_off,
        "my_origin": MY.get("origin"),
        "fee": fee,
        "has_freight": bool(freight),
        "off": [c["name"] for c in cards if c["missing"]],
        "thin_count": len([c for c in cards if not c["missing"] and c["thin"]]),
        "markets": today.get("_markets"),
    }
