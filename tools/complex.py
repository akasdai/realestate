"""
공동주택 단지 정보 API

1) AptListService3/getSigunguAptList3   → 시군구 단지 목록 (kaptCode, kaptName, bjdCode)
2) AptBasisInfoServiceV4/getAphusBassInfoV4 → 단지 상세 (hoCnt 세대수, 층수 등)

사용 키: DATA_GO_KR_API_KEY (data.go.kr 동일 키, 각 API 별도 활용 신청 필요)
"""

import asyncio
import re
from typing import Optional

import httpx

from _helpers import API_KEY, _build_url

LIST_URL   = "https://apis.data.go.kr/1613000/AptListService3/getSigunguAptList3"
DETAIL_URL = "https://apis.data.go.kr/1613000/AptBasisInfoServiceV4/getAphusBassInfoV4"
_TIMEOUT   = httpx.Timeout(15.0)


def _norm(name: str) -> str:
    """단지명 정규화: 공백·특수문자 제거 소문자화"""
    return re.sub(r"[\s\-_·\(\)（）]", "", name).lower()


# ── 1단계: 시군구 단지 목록 (kaptCode + kaptName) ────────────────────────────

async def _fetch_list_page(sigungu_code: str, page: int, rows: int) -> dict:
    params = {"sigunguCode": sigungu_code, "pageNo": str(page), "numOfRows": str(rows)}
    url = _build_url(LIST_URL, API_KEY, params)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
        except Exception:
            return {}


async def fetch_complex_list(sigungu_code: str) -> list[dict]:
    """
    시군구 코드로 전체 단지 목록 조회.
    Returns: [{kaptCode, kaptName, kaptName_norm, bjdCode, as1~as3}, ...]
    """
    rows = 1000
    first = await _fetch_list_page(sigungu_code, 1, rows)
    body = first.get("response", {}).get("body", {})
    items = body.get("items", []) or []
    total = int(body.get("totalCount", 0))

    # 추가 페이지 병렬 조회
    if total > rows:
        pages = range(2, (total // rows) + 2)
        extras = await asyncio.gather(*[
            _fetch_list_page(sigungu_code, p, rows) for p in pages
        ])
        for ex in extras:
            items += ex.get("response", {}).get("body", {}).get("items", []) or []

    return [
        {
            "kaptCode":      it.get("kaptCode", ""),
            "kaptName":      it.get("kaptName", ""),
            "kaptName_norm": _norm(it.get("kaptName", "")),
            "bjdCode":       it.get("bjdCode", ""),
            "addr":          " ".join(filter(None, [it.get("as1"), it.get("as2"), it.get("as3")])),
        }
        for it in items
        if it.get("kaptCode")
    ]


# ── 2단계: 단지 상세 (hoCnt 세대수 등) ────────────────────────────────────────

async def _fetch_detail(kapt_code: str) -> dict:
    params = {"kaptCode": kapt_code}
    url = _build_url(DETAIL_URL, API_KEY, params)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            item = data.get("response", {}).get("body", {}).get("item", {}) or {}
            return {
                "kaptCode":   kapt_code,
                "units":      item.get("hoCnt"),          # 세대수
                "dong_cnt":   item.get("kaptDongCnt"),    # 동수
                "floor_max":  item.get("ktownFlrNo"),     # 지상 최고층수
                "floor_base": item.get("kaptBaseFloor"),  # 지하층수
                "use_date":   item.get("kaptUsedate"),    # 사용승인일 YYYYMMDD
                "heat":       item.get("codeHeatNm"),     # 난방방식
                "mgmt":       item.get("codeMgrNm"),      # 관리방식
                "builder":    item.get("kaptBcompany"),   # 시공사
            }
        except Exception:
            return {"kaptCode": kapt_code}


async def fetch_complex_details(kapt_codes: list[str]) -> dict[str, dict]:
    """
    kaptCode 목록으로 상세정보 병렬 조회.
    Returns: {kaptCode: detail_dict}
    """
    if not kapt_codes:
        return {}
    results = await asyncio.gather(*[_fetch_detail(c) for c in kapt_codes])
    return {r["kaptCode"]: r for r in results}


# ── 통합 조회 ─────────────────────────────────────────────────────────────────

async def enrich_with_complex_info(
    sigungu_code: str,
    apt_names: list[str],
) -> tuple[dict[str, dict], str | None]:
    """
    아파트 이름 목록을 받아 단지 정보로 보강.

    Steps:
      1. getSigunguAptList3 → name→kaptCode 맵 구성
      2. apt_names를 정규화해 kaptCode 매칭
      3. getAphusBassInfoV4 → 매칭된 단지 상세 병렬 조회

    Returns:
      (complex_map, error_msg)
      complex_map: {normalized_name: {kaptCode, kaptName, units, floor_max, ...}}
    """
    if not API_KEY:
        return {}, "DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다."

    # 1. 단지 목록
    try:
        all_complexes = await fetch_complex_list(sigungu_code)
    except Exception as e:
        return {}, f"단지 목록 조회 실패: {e}"

    if not all_complexes:
        return {}, "해당 지역의 단지 목록이 없습니다."

    # 2. 이름 매칭 (exact → partial)
    list_map: dict[str, dict] = {c["kaptName_norm"]: c for c in all_complexes}
    matched: dict[str, str] = {}  # normalized_apt_name → kaptCode

    for name in set(apt_names):
        if not name:
            continue
        norm = _norm(name)
        if norm in list_map:
            matched[norm] = list_map[norm]["kaptCode"]
            continue
        # partial match
        for key, val in list_map.items():
            if norm in key or key in norm:
                matched[norm] = val["kaptCode"]
                break

    if not matched:
        return {}, None  # 매칭 실패는 에러 아님

    # 3. 상세 조회 (중복 kaptCode 제거)
    unique_codes = list(set(matched.values()))
    details = await fetch_complex_details(unique_codes)

    # 4. 결과 맵 조합
    complex_map: dict[str, dict] = {}
    kapt_to_list = {c["kaptCode"]: c for c in all_complexes}

    for norm_name, kapt_code in matched.items():
        base = kapt_to_list.get(kapt_code, {})
        detail = details.get(kapt_code, {})
        complex_map[norm_name] = {
            "kaptCode":  kapt_code,
            "kaptName":  base.get("kaptName", ""),
            "bjdCode":   base.get("bjdCode", ""),
            "addr":      base.get("addr", ""),
            **detail,
        }

    return complex_map, None
