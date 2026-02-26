"""
공통 API 호출 헬퍼 및 URL 상수

국토교통부 공공데이터 API (data.go.kr) 기반
"""

import os
import statistics
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()

# ── API 키 ──────────────────────────────────────────────────────────────────
API_KEY = os.getenv("DATA_GO_KR_API_KEY", "")
ONBID_API_KEY = os.getenv("ONBID_API_KEY", "") or API_KEY

# ── 국토교통부 실거래가 API 엔드포인트 ────────────────────────────────────────
BASE = "http://apis.data.go.kr"

# 아파트
APT_TRADE_URL = f"{BASE}/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
APT_RENT_URL = f"{BASE}/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"

# 오피스텔
OFFICETEL_TRADE_URL = f"{BASE}/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade"
OFFICETEL_RENT_URL = f"{BASE}/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"

# 연립/다세대 (빌라)
VILLA_TRADE_URL = f"{BASE}/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"
VILLA_RENT_URL = f"{BASE}/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent"

# 단독/다가구
SINGLE_HOUSE_TRADE_URL = f"{BASE}/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade"
SINGLE_HOUSE_RENT_URL = f"{BASE}/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent"

# 상업용/업무용 빌딩
COMMERCIAL_TRADE_URL = f"{BASE}/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"

# 온비드 공매 (data.go.kr 경유)
ONBID_BID_RESULT_URL = f"{BASE}/1230000/OnbidService/getOnbidBidResultList"
ONBID_THING_INFO_URL = f"{BASE}/1230000/OnbidService/getOnbidThingInfoList"

# 건축인허가 (ArchPmsHubService)
ARCH_PMS_BASE = f"{BASE}/1613000/ArchPmsHubService"
ARCH_PMS_BASIS_URL    = f"{ARCH_PMS_BASE}/getApBasisOulnInfo"    # 기본개요
ARCH_PMS_PKLOT_URL    = f"{ARCH_PMS_BASE}/getApPklotInfo"        # 주차장
ARCH_PMS_JIJIGU_URL   = f"{ARCH_PMS_BASE}/getApJijiguInfo"       # 지역지구구역
ARCH_PMS_PLATPLC_URL  = f"{ARCH_PMS_BASE}/getApPlatPlcInfo"      # 대지위치
ARCH_PMS_HSTP_URL     = f"{ARCH_PMS_BASE}/getApHsTpInfo"         # 주택유형


# ── HTTP 클라이언트 ──────────────────────────────────────────────────────────
_TIMEOUT = httpx.Timeout(30.0)


def _build_url(base_url: str, service_key: str, params: dict) -> str:
    """
    serviceKey를 URL 문자열에 직접 삽입합니다.
    data.go.kr API는 httpx params 딕셔너리로 serviceKey를 전달하면
    재인코딩 문제가 생기므로 URL에 직접 포함시킵니다.
    """
    from urllib.parse import urlencode
    query = urlencode(params)
    return f"{base_url}?serviceKey={service_key}&{query}"


async def _fetch_xml(url: str, params: dict) -> str | None:
    """XML 응답 비동기 조회 (serviceKey는 params에 포함)"""
    service_key = params.pop("serviceKey", API_KEY)
    full_url = _build_url(url, service_key, params)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.get(full_url)
            resp.raise_for_status()
            return resp.text
        except httpx.TimeoutException:
            return None
        except httpx.HTTPStatusError:
            return None
        except Exception:
            return None


async def _fetch_json(url: str, params: dict) -> dict | None:
    """JSON 응답 비동기 조회 (serviceKey는 params에 포함)"""
    service_key = params.pop("serviceKey", ONBID_API_KEY)
    full_url = _build_url(url, service_key, params)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.get(full_url)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            return None
        except httpx.HTTPStatusError:
            return None
        except Exception:
            return None


# ── XML 파싱 헬퍼 ────────────────────────────────────────────────────────────
def _txt(element, tag: str, default: str = "") -> str:
    """XML 태그에서 텍스트 추출"""
    try:
        import xml.etree.ElementTree as ET
        node = element.find(tag)
        return (node.text or "").strip() if node is not None else default
    except Exception:
        return default


def _parse_amount(value: str) -> int | None:
    """한국 금액 문자열(쉼표 포함)을 정수로 변환 (단위: 만원)"""
    try:
        return int(value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _make_date(year: str, month: str, day: str = "") -> str:
    """년/월/일 문자열을 ISO 날짜로 조합"""
    try:
        y = year.strip()
        m = month.strip().zfill(2)
        d = day.strip().zfill(2) if day.strip() else "01"
        return f"{y}-{m}-{d}"
    except Exception:
        return ""


def _summarize_prices(prices: list[int]) -> dict:
    """가격 목록에서 중앙값/최솟값/최댓값 계산"""
    if not prices:
        return {}
    return {
        "median": statistics.median(prices),
        "min": min(prices),
        "max": max(prices),
        "count": len(prices),
    }


# ── 공통 API 호출 플로우 ─────────────────────────────────────────────────────
async def run_molit_tool(
    url: str,
    region_code: str,
    year_month: str,
    num_of_rows: int,
    parser_fn,
    label: str,
) -> dict:
    """
    국토교통부 실거래가 API 공통 호출 및 파싱 플로우

    Args:
        url: API 엔드포인트 URL
        region_code: 법정동 앞 5자리 코드
        year_month: 거래년월 (YYYYMM)
        num_of_rows: 최대 행 수
        parser_fn: XML 파싱 함수 (xml_text -> list[dict])
        label: 로그용 레이블
    """
    if not API_KEY:
        return {"error": "DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다."}

    params = {
        "serviceKey": API_KEY,
        "LAWD_CD": region_code,
        "DEAL_YMD": year_month,
        "numOfRows": str(num_of_rows),
        "pageNo": "1",
    }

    xml_text = await _fetch_xml(url, params)
    if xml_text is None:
        return {"error": f"{label} API 요청 실패 (타임아웃 또는 서버 오류)"}

    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return {"error": f"XML 파싱 오류: {e}", "raw": xml_text[:500]}

    # 결과 코드 확인
    result_code = root.findtext(".//resultCode") or root.findtext("./header/resultCode") or ""
    if result_code not in ("", "00", "000", "0000"):
        result_msg = root.findtext(".//resultMsg") or "알 수 없는 오류"
        return {"error": f"API 오류 {result_code}: {result_msg}"}

    # totalCount
    total_count_text = root.findtext(".//totalCount") or "0"
    try:
        total_count = int(total_count_text)
    except ValueError:
        total_count = 0

    items_el = root.findall(".//item")
    items = parser_fn(items_el)

    result: dict[str, Any] = {
        "total_count": total_count,
        "returned_count": len(items),
        "region_code": region_code,
        "year_month": year_month,
        "items": items,
    }

    # 가격 요약 추가
    trade_amounts = [i["amount"] for i in items if isinstance(i.get("amount"), int)]
    if trade_amounts:
        result["price_summary_만원"] = _summarize_prices(trade_amounts)

    return result


def get_current_year_month() -> str:
    """현재 날짜를 YYYYMM 형식으로 반환"""
    return datetime.now().strftime("%Y%m")


# ── 건축인허가 API 공통 호출 플로우 ──────────────────────────────────────────
async def run_arch_pms_tool(
    url: str,
    sigungu_cd: str,
    bjdong_cd: str,
    parser_fn,
    label: str,
    *,
    bun: str = "",
    ji: str = "",
    start_date: str = "",
    end_date: str = "",
    num_of_rows: int = 100,
    page_no: int = 1,
) -> dict:
    """
    건축인허가 API (ArchPmsHubService) 공통 호출 및 파싱 플로우

    Args:
        url: 오퍼레이션 URL
        sigungu_cd: 시군구 5자리 코드 (예: 11680 = 강남구)
        bjdong_cd: 법정동 5자리 코드 (예: 10300. 빈 문자열이면 전체 읍면동)
        parser_fn: JSON body → list[dict] 파서 함수
        label: 로그용 레이블
        bun: 번지 본번 (선택)
        ji: 번지 부번 (선택)
        start_date: 검색 시작일 YYYYMMDD (선택)
        end_date: 검색 종료일 YYYYMMDD (선택)
        num_of_rows: 최대 행 수 (기본 100)
        page_no: 페이지 번호 (기본 1)
    """
    if not API_KEY:
        return {"error": "DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다."}

    params: dict[str, str] = {
        "serviceKey": API_KEY,
        "sigunguCd":  sigungu_cd,
        "bjdongCd":   bjdong_cd,
        "_type":      "json",
        "numOfRows":  str(num_of_rows),
        "pageNo":     str(page_no),
    }
    if bun:
        params["bun"] = bun
    if ji:
        params["ji"] = ji
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date

    data = await _fetch_json(url, params)
    if data is None:
        return {"error": f"{label} API 요청 실패 (타임아웃 또는 서버 오류)"}

    # 결과 코드 확인
    header = data.get("response", {}).get("header", {})
    result_code = str(header.get("resultCode", ""))
    if result_code not in ("", "00", "000", "0000"):
        return {"error": f"API 오류 {result_code}: {header.get('resultMsg', '알 수 없는 오류')}"}

    body = data.get("response", {}).get("body", {})
    total_count = int(body.get("totalCount", 0) or 0)

    raw_items = body.get("items", {})
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("item", []) or []
    if isinstance(raw_items, dict):  # 단건인 경우 dict로 반환됨
        raw_items = [raw_items]

    items = parser_fn(raw_items)

    return {
        "total_count": total_count,
        "returned_count": len(items),
        "sigungu_cd": sigungu_cd,
        "bjdong_cd": bjdong_cd,
        "items": items,
    }
