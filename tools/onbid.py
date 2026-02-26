"""
온비드(Onbid) 공매 조회 도구

- 공매 물건 목록 조회
- 공매 입찰 결과 조회
- 공매 물건 상세 조회

온비드 공공데이터 API: http://apis.data.go.kr/1230000/OnbidService/
"""

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from _helpers import (
    ONBID_BID_RESULT_URL,
    ONBID_THING_INFO_URL,
    ONBID_API_KEY,
    _fetch_xml,
    _fetch_json,
    _txt,
    _parse_amount,
)

# 온비드 물건 용도 코드 (주요)
ONBID_USE_CODES = {
    "001": "토지",
    "002": "건물",
    "003": "아파트",
    "004": "오피스텔",
    "005": "상가",
    "006": "공장",
    "007": "차량/기계",
    "008": "기타동산",
    "009": "유가증권",
    "010": "임야",
    "011": "농지",
    "012": "선박/항공기",
}

# 온비드 처분방법 코드
ONBID_DISPOSAL_CODES = {
    "01": "매각",
    "02": "임대",
    "03": "교환",
    "05": "분양",
}


def _parse_onbid_bid_result(data: Any) -> list[dict]:
    """공매 입찰결과 파싱 (JSON)"""
    items = []
    try:
        records = (
            data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        )
        if isinstance(records, dict):
            records = [records]
        for rec in records:
            items.append({
                "item_no": rec.get("cltrMngNo", ""),
                "item_name": rec.get("goodsNm", "") or rec.get("cltrNm", ""),
                "location": rec.get("ldtlAddr", "") or rec.get("rdnAddr", ""),
                "use_type": rec.get("useNm", ""),
                "appraised_value": _parse_amount(str(rec.get("apprAmt", "0"))),
                "minimum_bid": _parse_amount(str(rec.get("minBidAmt", "0"))),
                "winning_bid": _parse_amount(str(rec.get("sucsBidAmt", "0") or rec.get("sellAmt", "0"))),
                "bid_date": rec.get("pbctDt", "") or rec.get("bidDt", ""),
                "bid_status": rec.get("pbctSttNm", "") or rec.get("bidSttNm", ""),
                "disposal_method": rec.get("dspslMthdNm", ""),
                "agency": rec.get("cnsgAgcyNm", "") or rec.get("agcyNm", ""),
            })
    except Exception:
        pass
    return items


def _parse_onbid_thing_info(data: Any) -> list[dict]:
    """공매 물건정보 파싱 (JSON/XML)"""
    items = []
    try:
        records = (
            data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        )
        if isinstance(records, dict):
            records = [records]
        for rec in records:
            items.append({
                "item_no": rec.get("cltrMngNo", ""),
                "item_name": rec.get("goodsNm", "") or rec.get("cltrNm", ""),
                "location": rec.get("ldtlAddr", "") or rec.get("rdnAddr", ""),
                "use_type": rec.get("useNm", ""),
                "area_m2": rec.get("totArea", "") or rec.get("exclsArea", ""),
                "appraised_value": _parse_amount(str(rec.get("apprAmt", "0"))),
                "minimum_bid": _parse_amount(str(rec.get("minBidAmt", "0"))),
                "bid_start_date": rec.get("pbctBgngDt", ""),
                "bid_end_date": rec.get("pbctEndDt", ""),
                "bid_count": rec.get("pbctCnt", ""),
                "disposal_method": rec.get("dspslMthdNm", ""),
                "agency": rec.get("cnsgAgcyNm", "") or rec.get("agcyNm", ""),
                "remarks": rec.get("rmrk", ""),
            })
    except Exception:
        pass
    return items


def register_onbid_tools(mcp: FastMCP) -> None:
    """공매 관련 MCP 도구 등록"""

    @mcp.tool()
    async def get_public_auction_items(
        sido: str = "",
        sigungu: str = "",
        use_code: str = "",
        disposal_method: str = "",
        min_price: int = 0,
        max_price: int = 0,
        bid_start_date: str = "",
        bid_end_date: str = "",
        keyword: str = "",
        num_of_rows: int = 50,
        page_no: int = 1,
    ) -> dict:
        """
        온비드(Onbid) 공매 물건 목록을 조회합니다.

        Args:
            sido: 시도명 (예: '서울특별시', '경기도'). 빈 값이면 전국 조회
            sigungu: 시군구명 (예: '강남구', '수원시')
            use_code: 물건 용도 코드 (003=아파트, 004=오피스텔, 005=상가, 001=토지, 002=건물)
            disposal_method: 처분방법 (01=매각, 02=임대)
            min_price: 최저입찰가 최솟값 (만원 단위)
            max_price: 최저입찰가 최댓값 (만원 단위, 0=제한없음)
            bid_start_date: 입찰 시작일 (YYYYMMDD)
            bid_end_date: 입찰 종료일 (YYYYMMDD)
            keyword: 물건명 키워드
            num_of_rows: 최대 조회 건수 (기본 50)
            page_no: 페이지 번호 (기본 1)

        Returns:
            total_count, items(물건번호/명/위치/용도/감정가/최저입찰가/입찰일/처분방법/기관)
        """
        if not ONBID_API_KEY:
            return {
                "error": "ONBID_API_KEY 또는 DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다.",
                "tip": "data.go.kr에서 온비드 공매정보 API 활용신청 후 키를 발급받으세요.",
            }

        params: dict[str, Any] = {
            "serviceKey": ONBID_API_KEY,
            "numOfRows": str(num_of_rows),
            "pageNo": str(page_no),
        }

        if sido:
            params["sido"] = sido
        if sigungu:
            params["sigungu"] = sigungu
        if use_code:
            params["useCode"] = use_code
        if disposal_method:
            params["dspslMthd"] = disposal_method
        if min_price > 0:
            params["minBidAmtFrom"] = str(min_price * 10000)
        if max_price > 0:
            params["minBidAmtTo"] = str(max_price * 10000)
        if bid_start_date:
            params["pbctBgngDt"] = bid_start_date
        if bid_end_date:
            params["pbctEndDt"] = bid_end_date
        if keyword:
            params["goodsNm"] = keyword

        data = await _fetch_json(ONBID_THING_INFO_URL, params)
        if data is None:
            return {"error": "온비드 공매물건 API 요청 실패"}

        items = _parse_onbid_thing_info(data)
        total_count = (
            data.get("response", {}).get("body", {}).get("totalCount", 0)
        )

        return {
            "total_count": total_count,
            "returned_count": len(items),
            "page_no": page_no,
            "items": items,
            "use_code_reference": ONBID_USE_CODES,
        }

    @mcp.tool()
    async def get_public_auction_bid_results(
        sido: str = "",
        sigungu: str = "",
        use_code: str = "",
        bid_start_date: str = "",
        bid_end_date: str = "",
        keyword: str = "",
        num_of_rows: int = 50,
        page_no: int = 1,
    ) -> dict:
        """
        온비드(Onbid) 공매 입찰 결과(낙찰가 포함)를 조회합니다.

        Args:
            sido: 시도명 (예: '서울특별시')
            sigungu: 시군구명 (예: '강남구')
            use_code: 물건 용도 코드 (003=아파트, 004=오피스텔, 005=상가 등)
            bid_start_date: 입찰 시작일 (YYYYMMDD)
            bid_end_date: 입찰 종료일 (YYYYMMDD)
            keyword: 물건명 키워드
            num_of_rows: 최대 조회 건수 (기본 50)
            page_no: 페이지 번호

        Returns:
            total_count, items(물건번호/명/위치/감정가/최저입찰가/낙찰가/입찰일/상태/기관)
        """
        if not ONBID_API_KEY:
            return {
                "error": "ONBID_API_KEY 또는 DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다.",
            }

        params: dict[str, Any] = {
            "serviceKey": ONBID_API_KEY,
            "numOfRows": str(num_of_rows),
            "pageNo": str(page_no),
        }

        if sido:
            params["sido"] = sido
        if sigungu:
            params["sigungu"] = sigungu
        if use_code:
            params["useCode"] = use_code
        if bid_start_date:
            params["pbctBgngDt"] = bid_start_date
        if bid_end_date:
            params["pbctEndDt"] = bid_end_date
        if keyword:
            params["goodsNm"] = keyword

        data = await _fetch_json(ONBID_BID_RESULT_URL, params)
        if data is None:
            return {"error": "온비드 입찰결과 API 요청 실패"}

        items = _parse_onbid_bid_result(data)
        total_count = (
            data.get("response", {}).get("body", {}).get("totalCount", 0)
        )

        # 낙찰률 계산
        winning_bids = [i for i in items if i.get("winning_bid") and i["winning_bid"] > 0]
        stats = {}
        if winning_bids:
            rates = []
            for i in winning_bids:
                if i.get("minimum_bid") and i["minimum_bid"] > 0:
                    rate = round(i["winning_bid"] / i["minimum_bid"] * 100, 1)
                    rates.append(rate)
                    i["winning_rate_pct"] = rate
            if rates:
                import statistics as stat
                stats["avg_winning_rate_pct"] = round(stat.mean(rates), 1)
                stats["max_winning_rate_pct"] = max(rates)

        return {
            "total_count": total_count,
            "returned_count": len(items),
            "page_no": page_no,
            "items": items,
            "statistics": stats,
        }

    @mcp.tool()
    async def get_onbid_use_codes() -> dict:
        """
        온비드 공매 물건 용도 코드 목록을 반환합니다.
        get_public_auction_items의 use_code 파라미터에 사용합니다.

        Returns:
            용도코드와 명칭 딕셔너리
        """
        return {
            "use_codes": ONBID_USE_CODES,
            "disposal_methods": ONBID_DISPOSAL_CODES,
            "usage": "use_code 파라미터에 코드 값을 입력하세요. 예: '003' = 아파트",
        }
