"""
지역 코드 조회 도구

국토교통부 실거래가 API에서 사용하는 법정동 앞 5자리 코드를 조회합니다.
"""

import sys
import os

from mcp.server.fastmcp import FastMCP

# 프로젝트 루트의 data 패키지 접근
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.region_codes import search_region_code, REGION_CODES
from _helpers import get_current_year_month


def register_region_tools(mcp: FastMCP) -> None:
    """지역 코드 및 유틸리티 MCP 도구 등록"""

    @mcp.tool()
    def get_region_code(query: str) -> dict:
        """
        지역명을 법정동 코드(5자리)로 변환합니다.
        국토교통부 실거래가 API 조회 전 반드시 이 도구로 코드를 확인하세요.

        Args:
            query: 검색할 지역명
                   - 구 단위: '강남구', '마포구', '해운대구'
                   - 시+구: '서울 강남구', '부산 해운대구'
                   - 시 단위: '수원시', '성남시'
                   - 광역시: '서울', '부산', '대구', '인천', '광주', '대전', '울산'
                   - 도: '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남'

        Returns:
            {
                "code": "11680",       # API에 사용할 5자리 코드
                "name": "강남구",      # 매칭된 지역명
                "candidates": [...]    # 유사 지역 목록 (최대 10개)
            }
        """
        return search_region_code(query)

    @mcp.tool()
    def get_all_region_codes() -> dict:
        """
        전체 지역 코드 목록을 반환합니다.
        특정 지역 코드를 모를 때 참고용으로 사용하세요.

        Returns:
            지역명 -> 5자리 코드 딕셔너리 (전국 시군구)
        """
        return {
            "region_codes": REGION_CODES,
            "total_count": len(REGION_CODES),
            "usage": "반환된 코드를 get_apartment_trades 등의 region_code 파라미터에 사용하세요.",
        }

    @mcp.tool()
    def get_current_year_month_tool() -> dict:
        """
        현재 년월을 YYYYMM 형식으로 반환합니다.
        실거래가 API의 year_month 파라미터 기본값으로 사용하세요.

        Returns:
            {"year_month": "202502", "description": "현재 년월"}
        """
        ym = get_current_year_month()
        return {
            "year_month": ym,
            "description": f"현재 년월: {ym[:4]}년 {ym[4:]}월",
            "tip": "최신 데이터는 1-2개월 지연될 수 있으므로 이전 달도 함께 확인하세요.",
        }
