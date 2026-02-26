"""
부동산 매매 실거래가 조회 도구

- 아파트 매매
- 오피스텔 매매
- 연립/다세대(빌라) 매매
- 단독/다가구 주택 매매
- 상업용/업무용 건물 매매
"""

from mcp.server.fastmcp import FastMCP

from _helpers import (
    APT_TRADE_URL,
    COMMERCIAL_TRADE_URL,
    OFFICETEL_TRADE_URL,
    SINGLE_HOUSE_TRADE_URL,
    VILLA_TRADE_URL,
    _txt,
    _parse_amount,
    _make_date,
    run_molit_tool,
)


def _parse_apt_trades(items_el) -> list[dict]:
    result = []
    for item in items_el:
        amount_raw = _txt(item, "dealAmount") or _txt(item, "거래금액")
        result.append({
            "apt_name": _txt(item, "aptNm") or _txt(item, "아파트"),
            "amount": _parse_amount(amount_raw),
            "amount_raw": amount_raw,
            "area_m2": _txt(item, "excluUseAr") or _txt(item, "전용면적"),
            "floor": _txt(item, "floor") or _txt(item, "층"),
            "build_year": _txt(item, "buildYear") or _txt(item, "건축년도"),
            "dong": _txt(item, "umdNm") or _txt(item, "법정동"),
            "jibun": _txt(item, "jibun") or _txt(item, "지번"),
            "deal_date": _make_date(
                _txt(item, "dealYear") or _txt(item, "년"),
                _txt(item, "dealMonth") or _txt(item, "월"),
                _txt(item, "dealDay") or _txt(item, "일"),
            ),
            "deal_type": _txt(item, "dealingGbn") or _txt(item, "거래유형"),
            "agent_location": _txt(item, "estateAgentSggNm") or _txt(item, "중개사소재지"),
        })
    return result


def _parse_officetel_trades(items_el) -> list[dict]:
    result = []
    for item in items_el:
        amount_raw = _txt(item, "dealAmount") or _txt(item, "거래금액")
        result.append({
            "offi_name": _txt(item, "offiNm") or _txt(item, "오피스텔"),
            "amount": _parse_amount(amount_raw),
            "amount_raw": amount_raw,
            "area_m2": _txt(item, "excluUseAr") or _txt(item, "전용면적"),
            "floor": _txt(item, "floor") or _txt(item, "층"),
            "build_year": _txt(item, "buildYear") or _txt(item, "건축년도"),
            "dong": _txt(item, "umdNm") or _txt(item, "법정동"),
            "jibun": _txt(item, "jibun") or _txt(item, "지번"),
            "deal_date": _make_date(
                _txt(item, "dealYear") or _txt(item, "년"),
                _txt(item, "dealMonth") or _txt(item, "월"),
                _txt(item, "dealDay") or _txt(item, "일"),
            ),
        })
    return result


def _parse_villa_trades(items_el) -> list[dict]:
    result = []
    for item in items_el:
        amount_raw = _txt(item, "dealAmount") or _txt(item, "거래금액")
        result.append({
            "house_name": _txt(item, "mhouseNm") or _txt(item, "연립다세대"),
            "amount": _parse_amount(amount_raw),
            "amount_raw": amount_raw,
            "area_m2": _txt(item, "excluUseAr") or _txt(item, "전용면적"),
            "floor": _txt(item, "floor") or _txt(item, "층"),
            "build_year": _txt(item, "buildYear") or _txt(item, "건축년도"),
            "dong": _txt(item, "umdNm") or _txt(item, "법정동"),
            "jibun": _txt(item, "jibun") or _txt(item, "지번"),
            "deal_date": _make_date(
                _txt(item, "dealYear") or _txt(item, "년"),
                _txt(item, "dealMonth") or _txt(item, "월"),
                _txt(item, "dealDay") or _txt(item, "일"),
            ),
            "deal_type": _txt(item, "dealingGbn") or _txt(item, "거래유형"),
        })
    return result


def _parse_single_house_trades(items_el) -> list[dict]:
    result = []
    for item in items_el:
        amount_raw = _txt(item, "dealAmount") or _txt(item, "거래금액")
        result.append({
            "house_type": _txt(item, "houseType") or _txt(item, "주택유형"),
            "amount": _parse_amount(amount_raw),
            "amount_raw": amount_raw,
            "area_m2": _txt(item, "totalFloorAr") or _txt(item, "연면적"),
            "land_area_m2": _txt(item, "platArea") or _txt(item, "대지면적"),
            "floor_count": _txt(item, "floorCount") or _txt(item, "층"),
            "build_year": _txt(item, "buildYear") or _txt(item, "건축년도"),
            "dong": _txt(item, "umdNm") or _txt(item, "법정동"),
            "jibun": _txt(item, "jibun") or _txt(item, "지번"),
            "deal_date": _make_date(
                _txt(item, "dealYear") or _txt(item, "년"),
                _txt(item, "dealMonth") or _txt(item, "월"),
                _txt(item, "dealDay") or _txt(item, "일"),
            ),
            "deal_type": _txt(item, "dealingGbn") or _txt(item, "거래유형"),
        })
    return result


def _parse_commercial_trades(items_el) -> list[dict]:
    result = []
    for item in items_el:
        amount_raw = _txt(item, "dealAmount") or _txt(item, "거래금액")
        result.append({
            "use_type": _txt(item, "useNm") or _txt(item, "용도"),
            "amount": _parse_amount(amount_raw),
            "amount_raw": amount_raw,
            "area_m2": _txt(item, "dealArea") or _txt(item, "건물면적"),
            "land_area_m2": _txt(item, "platArea") or _txt(item, "대지면적"),
            "floor": _txt(item, "floor") or _txt(item, "층"),
            "total_floors": _txt(item, "totalFloor") or _txt(item, "건물층수"),
            "build_year": _txt(item, "buildYear") or _txt(item, "건축년도"),
            "dong": _txt(item, "umdNm") or _txt(item, "법정동"),
            "jibun": _txt(item, "jibun") or _txt(item, "지번"),
            "deal_date": _make_date(
                _txt(item, "dealYear") or _txt(item, "년"),
                _txt(item, "dealMonth") or _txt(item, "월"),
                _txt(item, "dealDay") or _txt(item, "일"),
            ),
            "deal_type": _txt(item, "dealingGbn") or _txt(item, "거래유형"),
        })
    return result


def register_trade_tools(mcp: FastMCP) -> None:
    """매매 실거래가 관련 MCP 도구 등록"""

    @mcp.tool()
    async def get_apartment_trades(
        region_code: str,
        year_month: str,
        num_of_rows: int = 100,
    ) -> dict:
        """
        아파트 매매 실거래가를 조회합니다.

        Args:
            region_code: 법정동 앞 5자리 코드 (예: '11680' = 강남구).
                         모르면 먼저 get_region_code() 도구를 사용하세요.
            year_month: 거래년월 (YYYYMM, 예: '202501').
                        현재 월은 get_current_year_month() 도구로 확인하세요.
            num_of_rows: 최대 조회 건수 (기본 100, 최대 1000)

        Returns:
            total_count, items(아파트명/금액/면적/층/건축년도/동/날짜), price_summary_만원
        """
        return await run_molit_tool(
            APT_TRADE_URL, region_code, year_month, num_of_rows,
            _parse_apt_trades, "아파트 매매"
        )

    @mcp.tool()
    async def get_officetel_trades(
        region_code: str,
        year_month: str,
        num_of_rows: int = 100,
    ) -> dict:
        """
        오피스텔 매매 실거래가를 조회합니다.

        Args:
            region_code: 법정동 앞 5자리 코드 (예: '11680' = 강남구)
            year_month: 거래년월 (YYYYMM)
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(오피스텔명/금액/면적/층/건축년도/동/날짜), price_summary_만원
        """
        return await run_molit_tool(
            OFFICETEL_TRADE_URL, region_code, year_month, num_of_rows,
            _parse_officetel_trades, "오피스텔 매매"
        )

    @mcp.tool()
    async def get_villa_trades(
        region_code: str,
        year_month: str,
        num_of_rows: int = 100,
    ) -> dict:
        """
        연립주택/다세대주택(빌라) 매매 실거래가를 조회합니다.

        Args:
            region_code: 법정동 앞 5자리 코드
            year_month: 거래년월 (YYYYMM)
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(건물명/금액/면적/층/건축년도/동/날짜), price_summary_만원
        """
        return await run_molit_tool(
            VILLA_TRADE_URL, region_code, year_month, num_of_rows,
            _parse_villa_trades, "연립/다세대 매매"
        )

    @mcp.tool()
    async def get_single_house_trades(
        region_code: str,
        year_month: str,
        num_of_rows: int = 100,
    ) -> dict:
        """
        단독주택/다가구주택 매매 실거래가를 조회합니다.

        Args:
            region_code: 법정동 앞 5자리 코드
            year_month: 거래년월 (YYYYMM)
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(주택유형/금액/연면적/대지면적/층수/건축년도/동/날짜), price_summary_만원
        """
        return await run_molit_tool(
            SINGLE_HOUSE_TRADE_URL, region_code, year_month, num_of_rows,
            _parse_single_house_trades, "단독/다가구 매매"
        )

    @mcp.tool()
    async def get_commercial_trades(
        region_code: str,
        year_month: str,
        num_of_rows: int = 100,
    ) -> dict:
        """
        상업용/업무용 건물 매매 실거래가를 조회합니다.
        오피스빌딩, 상가, 근린생활시설, 숙박시설 등이 포함됩니다.

        Args:
            region_code: 법정동 앞 5자리 코드
            year_month: 거래년월 (YYYYMM)
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(용도/금액/건물면적/대지면적/층/건축년도/동/날짜), price_summary_만원
        """
        return await run_molit_tool(
            COMMERCIAL_TRADE_URL, region_code, year_month, num_of_rows,
            _parse_commercial_trades, "상업/업무용 매매"
        )
