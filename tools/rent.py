"""
부동산 전월세 실거래 조회 도구

- 아파트 전월세
- 오피스텔 전월세
- 연립/다세대(빌라) 전월세
- 단독/다가구 주택 전월세
"""

from mcp.server.fastmcp import FastMCP

from _helpers import (
    APT_RENT_URL,
    OFFICETEL_RENT_URL,
    VILLA_RENT_URL,
    SINGLE_HOUSE_RENT_URL,
    _txt,
    _parse_amount,
    _make_date,
    run_molit_tool,
    _summarize_prices,
)


def _rent_summary(items: list[dict]) -> dict:
    """전세/월세 각각 가격 요약"""
    jeonse = [i["deposit"] for i in items if i.get("rent_type") == "전세" and isinstance(i.get("deposit"), int)]
    monthly_deposits = [i["deposit"] for i in items if i.get("rent_type") == "월세" and isinstance(i.get("deposit"), int)]
    monthly_rents = [i["monthly_rent"] for i in items if isinstance(i.get("monthly_rent"), int) and i.get("monthly_rent", 0) > 0]

    summary = {}
    if jeonse:
        summary["전세_보증금_만원"] = _summarize_prices(jeonse)
    if monthly_deposits:
        summary["월세_보증금_만원"] = _summarize_prices(monthly_deposits)
    if monthly_rents:
        summary["월세_월임대료_만원"] = _summarize_prices(monthly_rents)
    return summary


def _parse_apt_rent(items_el) -> list[dict]:
    result = []
    for item in items_el:
        deposit_raw = _txt(item, "deposit") or _txt(item, "보증금액")
        monthly_raw = _txt(item, "monthlyRent") or _txt(item, "월세금액")
        deposit = _parse_amount(deposit_raw)
        monthly = _parse_amount(monthly_raw)
        rent_type = "월세" if monthly and monthly > 0 else "전세"
        result.append({
            "apt_name": _txt(item, "aptNm") or _txt(item, "아파트"),
            "rent_type": rent_type,
            "deposit": deposit,
            "deposit_raw": deposit_raw,
            "monthly_rent": monthly,
            "monthly_rent_raw": monthly_raw,
            "area_m2": _txt(item, "excluUseAr") or _txt(item, "전용면적"),
            "floor": _txt(item, "floor") or _txt(item, "층"),
            "build_year": _txt(item, "buildYear") or _txt(item, "건축년도"),
            "dong": _txt(item, "umdNm") or _txt(item, "법정동"),
            "deal_date": _make_date(
                _txt(item, "dealYear") or _txt(item, "년"),
                _txt(item, "dealMonth") or _txt(item, "월"),
                _txt(item, "dealDay") or _txt(item, "일"),
            ),
        })
    return result


def _parse_officetel_rent(items_el) -> list[dict]:
    result = []
    for item in items_el:
        deposit_raw = _txt(item, "deposit") or _txt(item, "보증금액")
        monthly_raw = _txt(item, "monthlyRent") or _txt(item, "월세금액")
        deposit = _parse_amount(deposit_raw)
        monthly = _parse_amount(monthly_raw)
        rent_type = "월세" if monthly and monthly > 0 else "전세"
        result.append({
            "offi_name": _txt(item, "offiNm") or _txt(item, "오피스텔"),
            "rent_type": rent_type,
            "deposit": deposit,
            "deposit_raw": deposit_raw,
            "monthly_rent": monthly,
            "monthly_rent_raw": monthly_raw,
            "area_m2": _txt(item, "excluUseAr") or _txt(item, "전용면적"),
            "floor": _txt(item, "floor") or _txt(item, "층"),
            "build_year": _txt(item, "buildYear") or _txt(item, "건축년도"),
            "dong": _txt(item, "umdNm") or _txt(item, "법정동"),
            "deal_date": _make_date(
                _txt(item, "dealYear") or _txt(item, "년"),
                _txt(item, "dealMonth") or _txt(item, "월"),
                _txt(item, "dealDay") or _txt(item, "일"),
            ),
        })
    return result


def _parse_villa_rent(items_el) -> list[dict]:
    result = []
    for item in items_el:
        deposit_raw = _txt(item, "deposit") or _txt(item, "보증금액")
        monthly_raw = _txt(item, "monthlyRent") or _txt(item, "월세금액")
        deposit = _parse_amount(deposit_raw)
        monthly = _parse_amount(monthly_raw)
        rent_type = "월세" if monthly and monthly > 0 else "전세"
        result.append({
            "house_name": _txt(item, "mhouseNm") or _txt(item, "연립다세대"),
            "rent_type": rent_type,
            "deposit": deposit,
            "deposit_raw": deposit_raw,
            "monthly_rent": monthly,
            "monthly_rent_raw": monthly_raw,
            "area_m2": _txt(item, "excluUseAr") or _txt(item, "전용면적"),
            "floor": _txt(item, "floor") or _txt(item, "층"),
            "build_year": _txt(item, "buildYear") or _txt(item, "건축년도"),
            "dong": _txt(item, "umdNm") or _txt(item, "법정동"),
            "deal_date": _make_date(
                _txt(item, "dealYear") or _txt(item, "년"),
                _txt(item, "dealMonth") or _txt(item, "월"),
                _txt(item, "dealDay") or _txt(item, "일"),
            ),
        })
    return result


def _parse_single_house_rent(items_el) -> list[dict]:
    result = []
    for item in items_el:
        deposit_raw = _txt(item, "deposit") or _txt(item, "보증금액")
        monthly_raw = _txt(item, "monthlyRent") or _txt(item, "월세금액")
        deposit = _parse_amount(deposit_raw)
        monthly = _parse_amount(monthly_raw)
        rent_type = "월세" if monthly and monthly > 0 else "전세"
        result.append({
            "house_type": _txt(item, "houseType") or _txt(item, "주택유형"),
            "rent_type": rent_type,
            "deposit": deposit,
            "deposit_raw": deposit_raw,
            "monthly_rent": monthly,
            "monthly_rent_raw": monthly_raw,
            "area_m2": _txt(item, "totalFloorAr") or _txt(item, "연면적"),
            "dong": _txt(item, "umdNm") or _txt(item, "법정동"),
            "deal_date": _make_date(
                _txt(item, "dealYear") or _txt(item, "년"),
                _txt(item, "dealMonth") or _txt(item, "월"),
                _txt(item, "dealDay") or _txt(item, "일"),
            ),
        })
    return result


def register_rent_tools(mcp: FastMCP) -> None:
    """전월세 실거래 MCP 도구 등록"""

    @mcp.tool()
    async def get_apartment_rent(
        region_code: str,
        year_month: str,
        num_of_rows: int = 100,
    ) -> dict:
        """
        아파트 전세/월세 실거래 정보를 조회합니다.

        Args:
            region_code: 법정동 앞 5자리 코드 (예: '11680' = 강남구)
            year_month: 거래년월 (YYYYMM, 예: '202501')
            num_of_rows: 최대 조회 건수 (기본 100)

        Returns:
            total_count, items(아파트명/전세월세구분/보증금/월세/면적/층/날짜), 가격요약
        """
        result = await run_molit_tool(
            APT_RENT_URL, region_code, year_month, num_of_rows,
            _parse_apt_rent, "아파트 전월세"
        )
        if "items" in result:
            result.pop("price_summary_만원", None)
            result["rent_summary"] = _rent_summary(result["items"])
        return result

    @mcp.tool()
    async def get_officetel_rent(
        region_code: str,
        year_month: str,
        num_of_rows: int = 100,
    ) -> dict:
        """
        오피스텔 전세/월세 실거래 정보를 조회합니다.

        Args:
            region_code: 법정동 앞 5자리 코드
            year_month: 거래년월 (YYYYMM)
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(오피스텔명/전세월세구분/보증금/월세/면적/층/날짜), 가격요약
        """
        result = await run_molit_tool(
            OFFICETEL_RENT_URL, region_code, year_month, num_of_rows,
            _parse_officetel_rent, "오피스텔 전월세"
        )
        if "items" in result:
            result.pop("price_summary_만원", None)
            result["rent_summary"] = _rent_summary(result["items"])
        return result

    @mcp.tool()
    async def get_villa_rent(
        region_code: str,
        year_month: str,
        num_of_rows: int = 100,
    ) -> dict:
        """
        연립주택/다세대주택(빌라) 전세/월세 실거래 정보를 조회합니다.

        Args:
            region_code: 법정동 앞 5자리 코드
            year_month: 거래년월 (YYYYMM)
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(건물명/전세월세구분/보증금/월세/면적/층/날짜), 가격요약
        """
        result = await run_molit_tool(
            VILLA_RENT_URL, region_code, year_month, num_of_rows,
            _parse_villa_rent, "연립/다세대 전월세"
        )
        if "items" in result:
            result.pop("price_summary_만원", None)
            result["rent_summary"] = _rent_summary(result["items"])
        return result

    @mcp.tool()
    async def get_single_house_rent(
        region_code: str,
        year_month: str,
        num_of_rows: int = 100,
    ) -> dict:
        """
        단독주택/다가구주택 전세/월세 실거래 정보를 조회합니다.

        Args:
            region_code: 법정동 앞 5자리 코드
            year_month: 거래년월 (YYYYMM)
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(주택유형/전세월세구분/보증금/월세/연면적/동/날짜), 가격요약
        """
        result = await run_molit_tool(
            SINGLE_HOUSE_RENT_URL, region_code, year_month, num_of_rows,
            _parse_single_house_rent, "단독/다가구 전월세"
        )
        if "items" in result:
            result.pop("price_summary_만원", None)
            result["rent_summary"] = _rent_summary(result["items"])
        return result
