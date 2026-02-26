"""
웹 UI용 REST API 라우트

포트 8000에 통합:
  GET /               → index.html
  GET /style.css      → 정적 파일
  GET /main.js        → 정적 파일
  GET /api/region     → 지역코드 검색
  GET /api/trades     → 매매 실거래가 조회
  GET /api/rent       → 전월세 조회
  GET /api/complex    → 단지정보 조회
  GET /api/building   → 건축인허가 조회
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

from data.region_codes import search_region_code
from _helpers import (
    APT_TRADE_URL,
    OFFICETEL_TRADE_URL,
    VILLA_TRADE_URL,
    SINGLE_HOUSE_TRADE_URL,
    COMMERCIAL_TRADE_URL,
    APT_RENT_URL,
    OFFICETEL_RENT_URL,
    VILLA_RENT_URL,
    SINGLE_HOUSE_RENT_URL,
    run_molit_tool,
    ARCH_PMS_BASIS_URL,
    ARCH_PMS_PKLOT_URL,
    ARCH_PMS_JIJIGU_URL,
    ARCH_PMS_PLATPLC_URL,
    ARCH_PMS_HSTP_URL,
    run_arch_pms_tool,
)
from tools.trade import (
    _parse_apt_trades,
    _parse_officetel_trades,
    _parse_villa_trades,
    _parse_single_house_trades,
    _parse_commercial_trades,
)
from tools.complex import enrich_with_complex_info
from tools.building_permit import (
    _parse_basis,
    _parse_pklot,
    _parse_jijigu,
    _parse_platplc,
    _parse_hstp,
)
from tools.rent import (
    _parse_apt_rent,
    _parse_officetel_rent,
    _parse_villa_rent,
    _parse_single_house_rent,
    _rent_summary,
)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ── 정적 파일 ─────────────────────────────────────────────────────────────────

async def index(request: Request) -> FileResponse:
    return FileResponse(os.path.join(_BASE_DIR, "index.html"))


async def serve_css(request: Request) -> FileResponse:
    return FileResponse(os.path.join(_BASE_DIR, "style.css"), media_type="text/css")


async def serve_js(request: Request) -> FileResponse:
    return FileResponse(os.path.join(_BASE_DIR, "main.js"), media_type="application/javascript")


# ── API 엔드포인트 ────────────────────────────────────────────────────────────

async def api_region(request: Request) -> JSONResponse:
    """GET /api/region?q={지역명} → 지역코드 검색"""
    q = request.query_params.get("q", "").strip()
    if not q:
        return JSONResponse({"error": "q 파라미터가 필요합니다."}, status_code=400)
    result = search_region_code(q)
    return JSONResponse(result)


_TRADE_CONFIGS = {
    "apt":        (APT_TRADE_URL,          _parse_apt_trades,          "아파트 매매"),
    "offi":       (OFFICETEL_TRADE_URL,    _parse_officetel_trades,    "오피스텔 매매"),
    "villa":      (VILLA_TRADE_URL,        _parse_villa_trades,        "빌라 매매"),
    "house":      (SINGLE_HOUSE_TRADE_URL, _parse_single_house_trades, "단독주택 매매"),
    "commercial": (COMMERCIAL_TRADE_URL,   _parse_commercial_trades,   "상업용 매매"),
}

_RENT_CONFIGS = {
    "apt":   (APT_RENT_URL,         _parse_apt_rent,          "아파트 전월세"),
    "offi":  (OFFICETEL_RENT_URL,   _parse_officetel_rent,    "오피스텔 전월세"),
    "villa": (VILLA_RENT_URL,       _parse_villa_rent,        "빌라 전월세"),
    "house": (SINGLE_HOUSE_RENT_URL, _parse_single_house_rent, "단독주택 전월세"),
}


async def api_trades(request: Request) -> JSONResponse:
    """GET /api/trades?type=apt&region_code=11680&year_month=202412&rows=100"""
    p = request.query_params
    trade_type = p.get("type", "apt").lower()
    region_code = p.get("region_code", "").strip()
    year_month = p.get("year_month", "").strip()
    rows = int(p.get("rows", "100"))

    if not region_code or not year_month:
        return JSONResponse({"error": "region_code와 year_month가 필요합니다."}, status_code=400)

    if trade_type not in _TRADE_CONFIGS:
        return JSONResponse({"error": f"type은 {list(_TRADE_CONFIGS.keys())} 중 하나여야 합니다."}, status_code=400)

    url, parser, label = _TRADE_CONFIGS[trade_type]
    result = await run_molit_tool(url, region_code, year_month, rows, parser, label)
    return JSONResponse(result)


async def api_rent(request: Request) -> JSONResponse:
    """GET /api/rent?type=apt&region_code=11680&year_month=202412&rows=100"""
    p = request.query_params
    rent_type = p.get("type", "apt").lower()
    region_code = p.get("region_code", "").strip()
    year_month = p.get("year_month", "").strip()
    rows = int(p.get("rows", "100"))

    if not region_code or not year_month:
        return JSONResponse({"error": "region_code와 year_month가 필요합니다."}, status_code=400)

    if rent_type not in _RENT_CONFIGS:
        return JSONResponse({"error": f"type은 {list(_RENT_CONFIGS.keys())} 중 하나여야 합니다."}, status_code=400)

    url, parser, label = _RENT_CONFIGS[rent_type]
    result = await run_molit_tool(url, region_code, year_month, rows, parser, label)
    if "items" in result:
        result.pop("price_summary_만원", None)
        result["rent_summary"] = _rent_summary(result["items"])
    return JSONResponse(result)


async def api_complex(request: Request) -> JSONResponse:
    """
    GET /api/complex?region_code=11680&apt_names=은마,대림역삼,...

    단지 목록 조회 + 매칭된 단지 상세(세대수 등) 반환.
    apt_names: 쉼표 구분 아파트명 목록 (거래 결과에서 추출)
    """
    region_code = request.query_params.get("region_code", "").strip()
    if not region_code:
        return JSONResponse({"error": "region_code가 필요합니다."}, status_code=400)

    raw_names = request.query_params.get("apt_names", "")
    apt_names = [n.strip() for n in raw_names.split(",") if n.strip()] if raw_names else []

    complex_map, error = await enrich_with_complex_info(region_code, apt_names)

    if error and not complex_map:
        return JSONResponse({"error": error, "complex_map": {}})

    return JSONResponse({
        "complex_map": complex_map,   # {normalized_name: {kaptCode, units, ...}}
        "matched_count": len(complex_map),
        "error": error,
    })


_BUILDING_CONFIGS = {
    "basis":   (ARCH_PMS_BASIS_URL,   _parse_basis,   "건축인허가 기본개요"),
    "parking": (ARCH_PMS_PKLOT_URL,   _parse_pklot,   "건축인허가 주차장"),
    "zone":    (ARCH_PMS_JIJIGU_URL,  _parse_jijigu,  "건축인허가 지역지구구역"),
    "location":(ARCH_PMS_PLATPLC_URL, _parse_platplc, "건축인허가 대지위치"),
    "housing": (ARCH_PMS_HSTP_URL,    _parse_hstp,    "건축인허가 주택유형"),
}


async def api_building(request: Request) -> JSONResponse:
    """
    GET /api/building?type=basis&sigungu_cd=11680&bjdong_cd=10300&start_date=20240101&end_date=20241231&rows=100

    type: basis | parking | zone | location | housing
    sigungu_cd: 시군구 5자리 코드 (필수, 예: 11680 = 강남구)
    bjdong_cd: 법정동 5자리 코드 (필수, 예: 10300 = 개포동)
               단지정보(/api/complex) 응답의 bjdCode 필드 값을 사용하세요.
    bun, ji: 번지 본번/부번 (선택)
    start_date, end_date: YYYYMMDD (선택)
    rows: 최대 건수 (기본 100)
    """
    p = request.query_params
    building_type = p.get("type", "basis").lower()
    sigungu_cd = p.get("sigungu_cd", "").strip()
    bjdong_cd = p.get("bjdong_cd", "").strip()
    bun = p.get("bun", "").strip()
    ji = p.get("ji", "").strip()
    start_date = p.get("start_date", "").strip()
    end_date = p.get("end_date", "").strip()
    rows = int(p.get("rows", "100"))

    if not sigungu_cd or not bjdong_cd:
        return JSONResponse(
            {"error": "sigungu_cd와 bjdong_cd가 모두 필요합니다. "
                      "bjdong_cd는 /api/complex 응답의 bjdCode 필드를 사용하세요."},
            status_code=400,
        )

    if building_type not in _BUILDING_CONFIGS:
        return JSONResponse(
            {"error": f"type은 {list(_BUILDING_CONFIGS.keys())} 중 하나여야 합니다."},
            status_code=400,
        )

    url, parser, label = _BUILDING_CONFIGS[building_type]
    result = await run_arch_pms_tool(
        url, sigungu_cd, bjdong_cd, parser, label,
        bun=bun, ji=ji, start_date=start_date, end_date=end_date, num_of_rows=rows,
    )
    return JSONResponse(result)


# ── 라우트 목록 ───────────────────────────────────────────────────────────────

def create_web_routes() -> list:
    return [
        Route("/", index),
        Route("/style.css", serve_css),
        Route("/main.js", serve_js),
        Route("/api/region", api_region),
        Route("/api/trades", api_trades),
        Route("/api/rent", api_rent),
        Route("/api/complex", api_complex),
        Route("/api/building", api_building),
    ]
