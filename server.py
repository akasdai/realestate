"""
한국 부동산 실거래가 MCP 서버
Korea Real Estate Transaction MCP Server

국토교통부 공공데이터 API 기반으로 다음 정보를 제공합니다:
  - 아파트/오피스텔/빌라/단독주택/다가구 매매 실거래가
  - 아파트/오피스텔/빌라/단독주택 전월세 실거래
  - 상업용/업무용 건물 매매 실거래가
  - 온비드(Onbid) 공매 물건 조회 및 입찰 결과
  - 지역 코드 조회 (법정동 5자리 코드)

사전 준비:
  1. https://www.data.go.kr 회원 가입
  2. 아래 API 활용 신청:
     - 국토교통부_아파트매매실거래자료
     - 국토교통부_아파트전월세자료
     - 국토교통부_오피스텔매매신고자료
     - 국토교통부_오피스텔전월세신고조회서비스
     - 국토교통부_연립다세대매매실거래자료
     - 국토교통부_연립다세대전월세자료
     - 국토교통부_단독다가구매매실거래가자료
     - 국토교통부_단독다가구전월세자료
     - 국토교통부_상업업무용부동산매매신고자료
     - 온비드공매정보서비스 (선택)
  3. 발급된 API 키를 DATA_GO_KR_API_KEY 환경변수에 설정

환경 변수:
  DATA_GO_KR_API_KEY - 공공데이터포털 API 키 (필수)
  ONBID_API_KEY      - 온비드 전용 API 키 (없으면 DATA_GO_KR_API_KEY 사용)
  MCP_HOST           - HTTP 모드 호스트 (기본: 0.0.0.0)
  MCP_PORT           - HTTP 모드 포트 (기본: 8000)
"""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# MCP 서버 생성
mcp = FastMCP(
    name="korea-realestate-mcp",
    instructions="""
한국 부동산 실거래가 및 공매 정보를 조회하는 MCP 서버입니다.

## 사용 순서
1. 지역 코드 확인: get_region_code("강남구") → 코드 11680 반환
2. 현재 년월 확인: get_current_year_month_tool() → 예: "202502"
3. 실거래가 조회: get_apartment_trades(region_code="11680", year_month="202502")

## 제공 데이터
- 매매 실거래가: 아파트, 오피스텔, 빌라(연립/다세대), 단독/다가구, 상업용 건물
- 전월세: 아파트, 오피스텔, 빌라, 단독/다가구
- 공매: 온비드 물건 목록, 입찰 결과(낙찰가)

## 주의사항
- 실거래 데이터는 통상 1-2개월 후 공개됩니다
- 지역 코드는 법정동 앞 5자리입니다 (예: 11680 = 서울 강남구)
- API 키 없이는 조회 불가합니다 (data.go.kr에서 발급)
""",
)

# 도구 등록
from tools.trade import register_trade_tools
from tools.rent import register_rent_tools
from tools.onbid import register_onbid_tools
from tools.region import register_region_tools
from tools.building_permit import register_building_permit_tools

register_trade_tools(mcp)
register_rent_tools(mcp)
register_onbid_tools(mcp)
register_region_tools(mcp)
register_building_permit_tools(mcp)


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()

    if transport == "http":
        import uvicorn
        from starlette.applications import Starlette
        from starlette.routing import Mount
        from web_api import create_web_routes

        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        print(f"[Korea Real Estate MCP] HTTP 모드로 시작: {host}:{port}", flush=True)
        print(f"  웹 UI:  http://{host}:{port}/", flush=True)
        print(f"  MCP:    http://{host}:{port}/mcp", flush=True)

        mcp_app = mcp.streamable_http_app()
        app = Starlette(
            routes=create_web_routes() + [Mount("/mcp", app=mcp_app)]
        )
        uvicorn.run(app, host=host, port=port, log_level="info")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
