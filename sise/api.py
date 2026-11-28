"""공공데이터포털 API에서 도매시장 데이터를 받아옵니다.

- 정산정보 (katSale/trades): 시장·품목·등급·크기별로 하루 거래를 묶은 값. 등급별 평균가가 있어 보고서의 기준입니다.
  도매시장 코드가 꼭 필요해서, 시장 목록은 data/markets.json 에 저장해 둡니다.
- 실시간 경매정보 (katRealTime2/trades2): markets.json 이 없을 때 시장 목록을 알아내는 데만 씁니다.
"""
import json
import os
import time
from pathlib import Path

import requests

SALE_URL = "https://apis.data.go.kr/B552845/katSale/trades"
REALTIME_URL = "https://apis.data.go.kr/B552845/katRealTime2/trades2"
DATA = Path(__file__).resolve().parent.parent / "data"

SALE_COLUMNS = ",".join([
    "trd_clcln_ymd", "whsl_mrkt_cd", "whsl_mrkt_nm", "gds_mclsf_nm", "gds_sclsf_nm",
    "unit_qty", "unit_nm", "grd_nm", "sz_nm", "corp_nm", "plor_nm", "unit_tot_qty", "totprc", "avgprc", "lwprc", "hgprc",
])


class ApiError(RuntimeError):
    pass


def _key():
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        raise ApiError("DATA_GO_KR_KEY 가 설정되지 않았어요. GitHub Secrets 에 공공데이터포털 '일반 인증키(Decoding)'를 넣어 주세요.")
    return key


def _get(url, params, tries=3):
    params = {"serviceKey": _key(), "returnType": "json", **params}
    last = None
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code != 200:
                raise ApiError(f"HTTP {r.status_code}: {r.text[:200]}")
            try:
                body = r.json()
            except ValueError:
                raise ApiError(f"JSON이 아닌 응답: {r.text[:200]}")
            resp = body.get("response", body)
            header = resp.get("header", {})
            code = str(header.get("resultCode", "00"))
            if code not in ("0", "00", "000", "INFO-000"):
                raise ApiError(f"API 오류 {code}: {header.get('resultMsg')}")
            return resp.get("body", {})
        except (requests.RequestException, ApiError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def _items(body):
    items = body.get("items") or {}
    if isinstance(items, dict):
        items = items.get("item") or []
    if isinstance(items, dict):
        items = [items]
    return items


def _paged(url, params, rows=1000, max_pages=50):
    out, page = [], 1
    while page <= max_pages:
        body = _get(url, {**params, "pageNo": page, "numOfRows": rows})
        batch = _items(body)
        out.extend(batch)
        total = int(body.get("totalCount") or 0)
        if not batch or len(out) >= total:
            break
        page += 1
    return out


def markets(ymd):
    """도매시장 코드 목록. data/markets.json 이 있으면 그대로 씁니다."""
    path = DATA / "markets.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved:
            return saved
    rows = _paged(REALTIME_URL, {
        "cond[trd_clcln_ymd::EQ]": ymd,
        "selectable": "whsl_mrkt_cd,whsl_mrkt_nm",
    }, max_pages=20)
    found = {}
    for r in rows:
        if r.get("whsl_mrkt_cd"):
            found[r["whsl_mrkt_cd"]] = r.get("whsl_mrkt_nm", r["whsl_mrkt_cd"])
    result = [{"code": c, "name": n} for c, n in sorted(found.items())]
    if result:
        path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


_COLS = [SALE_COLUMNS]
_OPTIONAL = [",plor_nm", ",corp_nm", ",sz_nm"]   # 거부되면 하나씩 빼고 다시 받는 항목


def sale_day(ymd, market_list):
    """하루치 정산 데이터 (전체 시장). 선택 항목(산지·법인·크기)이 거부되면 빼고 다시 받습니다."""
    rows = []
    for m in market_list:
        params = {"cond[trd_clcln_ymd::EQ]": ymd, "cond[whsl_mrkt_cd::EQ]": m["code"]}
        while True:
            try:
                rows.extend(_paged(SALE_URL, {**params, "selectable": _COLS[0]}))
                break
            except ApiError as e:
                drop = next((x for x in _OPTIONAL if x in _COLS[0]), None)
                if not drop:
                    print(f"  ! {m['name']} {ymd}: {e}")
                    break
                _COLS[0] = _COLS[0].replace(drop, "")
                print(f"  ({drop[1:]} 항목 없이 다시 받아요: {e})")
    return rows
