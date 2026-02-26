"""
건축인허가 정보 조회 도구 (ArchPmsHubService)

국토교통부 건축HUB 건축인허가 API 기반:
  - 기본개요: 대지/건축면적, 건폐율, 용적률, 세대수, 허가일/사용승인일
  - 주차장: 자주식/기계식/옥외 주차대수
  - 지역지구구역: 용도지역, 용도지구, 용도구역
  - 대지위치: 지목, 행정동, 도로접면
  - 주택유형: 유형별(아파트/연립/다세대 등) 세대수

API: https://apis.data.go.kr/1613000/ArchPmsHubService
"""

from mcp.server.fastmcp import FastMCP

from _helpers import (
    ARCH_PMS_BASIS_URL,
    ARCH_PMS_PKLOT_URL,
    ARCH_PMS_JIJIGU_URL,
    ARCH_PMS_PLATPLC_URL,
    ARCH_PMS_HSTP_URL,
    run_arch_pms_tool,
)


# ── 파서 함수들 ───────────────────────────────────────────────────────────────

def _parse_basis(items: list) -> list[dict]:
    """기본개요 파싱"""
    result = []
    for it in items:
        result.append({
            "bld_name":       it.get("bldNm", ""),
            "plat_plc":       it.get("platPlc", ""),           # 대지위치
            "main_purps":     it.get("mainPurpsCdNm", ""),     # 주용도
            "strct":          it.get("strctCdNm", ""),         # 구조
            "roof":           it.get("roofCdNm", ""),          # 지붕
            "plat_area":      it.get("platArea", ""),          # 대지면적(㎡)
            "arch_area":      it.get("archArea", ""),          # 건축면적(㎡)
            "bc_rat":         it.get("bcRat", ""),             # 건폐율(%)
            "tot_area":       it.get("totArea", ""),           # 연면적(㎡)
            "vlrat_flo_area": it.get("vlratFlrArea", ""),      # 용적률 산정 연면적
            "vl_rat":         it.get("vlRat", ""),             # 용적률(%)
            "gnd_flr_cnt":    it.get("grndFlrCnt", ""),        # 지상층수
            "und_flr_cnt":    it.get("ugrndFlrCnt", ""),       # 지하층수
            "ho_cnt":         it.get("hoCnt", ""),             # 호수
            "hhld_cnt":       it.get("hhldCnt", ""),           # 가구수
            "fmly_cnt":       it.get("fmlyCnt", ""),           # 세대수
            "main_bld_cnt":   it.get("mainBldCnt", ""),        # 주건축물수
            "atch_bld_cnt":   it.get("atchBldCnt", ""),        # 부속건축물수
            "arch_pms_day":   it.get("archPmsDay", ""),        # 건축허가일
            "stcns_day":      it.get("stcnsDay", ""),          # 착공일
            "use_apr_day":    it.get("useAprDay", ""),         # 사용승인일
            "crtn_day":       it.get("crtnDay", ""),           # 생성일자
        })
    return result


def _parse_pklot(items: list) -> list[dict]:
    """주차장 파싱"""
    result = []
    for it in items:
        result.append({
            "bld_name":         it.get("bldNm", ""),
            "plat_plc":         it.get("platPlc", ""),
            "pklot_cd_nm":      it.get("pklotCdNm", ""),        # 주차장구분
            "auto_prkng_cnt":   it.get("autoPrkngCnt", ""),     # 자주식 대수
            "mchng_prkng_cnt":  it.get("mchngPrkngCnt", ""),    # 기계식 대수
            "outdor_prkng_cnt": it.get("outdorMechPrkngCnt", "") or it.get("outdorPrkngCnt", ""),  # 옥외 대수
            "indr_prkng_cnt":   it.get("indrAutoMechPrkngCnt", "") or it.get("indrPrkngCnt", ""),  # 옥내 대수
            "crtn_day":         it.get("crtnDay", ""),
        })
    return result


def _parse_jijigu(items: list) -> list[dict]:
    """지역지구구역 파싱"""
    result = []
    for it in items:
        result.append({
            "bld_name":      it.get("bldNm", ""),
            "plat_plc":      it.get("platPlc", ""),
            "jiyuk_cd_nm":   it.get("jiyukCdNm", ""),     # 용도지역
            "jigu_cd_nm":    it.get("jiguCdNm", ""),      # 용도지구
            "guyuk_cd_nm":   it.get("guyukCdNm", ""),     # 용도구역
            "etc_jiyuk":     it.get("etcJiyukCd", ""),    # 기타지역
            "etc_jigu":      it.get("etcJiguCd", ""),     # 기타지구
            "crtn_day":      it.get("crtnDay", ""),
        })
    return result


def _parse_platplc(items: list) -> list[dict]:
    """대지위치 파싱"""
    result = []
    for it in items:
        result.append({
            "bld_name":      it.get("bldNm", ""),
            "plat_plc":      it.get("platPlc", ""),          # 대지위치
            "jimok_cd_nm":   it.get("jimokCdNm", ""),        # 지목
            "sigungu_nm":    it.get("sigunguNm", ""),        # 시군구명
            "bjdong_nm":     it.get("bjdongNm", ""),         # 법정동명
            "hjdong_nm":     it.get("hjdongNm", ""),         # 행정동명
            "road_nm":       it.get("newPlatPlc", "") or it.get("roadNm", ""),  # 도로명주소
            "bun":           it.get("bun", ""),
            "ji":            it.get("ji", ""),
            "crtn_day":      it.get("crtnDay", ""),
        })
    return result


def _parse_hstp(items: list) -> list[dict]:
    """주택유형 파싱"""
    result = []
    for it in items:
        result.append({
            "bld_name":     it.get("bldNm", ""),
            "plat_plc":     it.get("platPlc", ""),
            "hs_tp_cd_nm":  it.get("hsTpCdNm", ""),     # 주택유형명
            "hhld_cnt":     it.get("hhldCnt", ""),      # 가구수
            "fmly_cnt":     it.get("fmlyCnt", ""),      # 세대수
            "crtn_day":     it.get("crtnDay", ""),
        })
    return result


# ── MCP 도구 등록 ─────────────────────────────────────────────────────────────

def register_building_permit_tools(mcp: FastMCP) -> None:
    """건축인허가 관련 MCP 도구 등록"""

    @mcp.tool()
    async def get_building_permit_basis(
        sigungu_cd: str,
        bjdong_cd: str = "",
        bun: str = "",
        ji: str = "",
        start_date: str = "",
        end_date: str = "",
        num_of_rows: int = 100,
    ) -> dict:
        """
        건축인허가 기본개요를 조회합니다.
        대지면적, 건축면적, 건폐율, 연면적, 용적률, 세대수, 허가일, 사용승인일 등을 반환합니다.

        Args:
            sigungu_cd: 시군구 5자리 코드 (예: '11680' = 강남구).
                        get_region_code() 도구로 확인하세요.
            bjdong_cd: 법정동 5자리 코드 (예: '10300'. 빈 값이면 시군구 전체 조회)
            bun: 번지 본번 (선택)
            ji: 번지 부번 (선택)
            start_date: 검색 시작일 YYYYMMDD (예: '20240101')
            end_date: 검색 종료일 YYYYMMDD (예: '20241231')
            num_of_rows: 최대 조회 건수 (기본 100)

        Returns:
            total_count, items(건물명/대지위치/주용도/구조/면적/건폐율/용적률/세대수/허가일/사용승인일)
        """
        return await run_arch_pms_tool(
            ARCH_PMS_BASIS_URL, sigungu_cd, bjdong_cd, _parse_basis, "건축인허가 기본개요",
            bun=bun, ji=ji, start_date=start_date, end_date=end_date, num_of_rows=num_of_rows,
        )

    @mcp.tool()
    async def get_building_permit_parking(
        sigungu_cd: str,
        bjdong_cd: str = "",
        bun: str = "",
        ji: str = "",
        start_date: str = "",
        end_date: str = "",
        num_of_rows: int = 100,
    ) -> dict:
        """
        건축인허가 주차장 정보를 조회합니다.
        자주식/기계식/옥외 주차대수 등을 반환합니다.

        Args:
            sigungu_cd: 시군구 5자리 코드 (예: '11680' = 강남구)
            bjdong_cd: 법정동 5자리 코드 (빈 값이면 시군구 전체)
            bun: 번지 본번 (선택)
            ji: 번지 부번 (선택)
            start_date: 검색 시작일 YYYYMMDD
            end_date: 검색 종료일 YYYYMMDD
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(건물명/대지위치/주차장구분/자주식/기계식/옥외 대수)
        """
        return await run_arch_pms_tool(
            ARCH_PMS_PKLOT_URL, sigungu_cd, bjdong_cd, _parse_pklot, "건축인허가 주차장",
            bun=bun, ji=ji, start_date=start_date, end_date=end_date, num_of_rows=num_of_rows,
        )

    @mcp.tool()
    async def get_building_permit_zone(
        sigungu_cd: str,
        bjdong_cd: str = "",
        bun: str = "",
        ji: str = "",
        start_date: str = "",
        end_date: str = "",
        num_of_rows: int = 100,
    ) -> dict:
        """
        건축인허가 지역지구구역 정보를 조회합니다.
        용도지역, 용도지구, 용도구역 정보를 반환합니다.

        Args:
            sigungu_cd: 시군구 5자리 코드 (예: '11680' = 강남구)
            bjdong_cd: 법정동 5자리 코드 (빈 값이면 시군구 전체)
            bun: 번지 본번 (선택)
            ji: 번지 부번 (선택)
            start_date: 검색 시작일 YYYYMMDD
            end_date: 검색 종료일 YYYYMMDD
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(건물명/대지위치/용도지역/용도지구/용도구역)
        """
        return await run_arch_pms_tool(
            ARCH_PMS_JIJIGU_URL, sigungu_cd, bjdong_cd, _parse_jijigu, "건축인허가 지역지구구역",
            bun=bun, ji=ji, start_date=start_date, end_date=end_date, num_of_rows=num_of_rows,
        )

    @mcp.tool()
    async def get_building_permit_location(
        sigungu_cd: str,
        bjdong_cd: str = "",
        bun: str = "",
        ji: str = "",
        start_date: str = "",
        end_date: str = "",
        num_of_rows: int = 100,
    ) -> dict:
        """
        건축인허가 대지위치 정보를 조회합니다.
        지목, 법정동/행정동명, 도로명주소를 반환합니다.

        Args:
            sigungu_cd: 시군구 5자리 코드 (예: '11680' = 강남구)
            bjdong_cd: 법정동 5자리 코드 (빈 값이면 시군구 전체)
            bun: 번지 본번 (선택)
            ji: 번지 부번 (선택)
            start_date: 검색 시작일 YYYYMMDD
            end_date: 검색 종료일 YYYYMMDD
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(건물명/대지위치/지목/시군구명/법정동/행정동/도로명주소/번지)
        """
        return await run_arch_pms_tool(
            ARCH_PMS_PLATPLC_URL, sigungu_cd, bjdong_cd, _parse_platplc, "건축인허가 대지위치",
            bun=bun, ji=ji, start_date=start_date, end_date=end_date, num_of_rows=num_of_rows,
        )

    @mcp.tool()
    async def get_building_permit_housing_type(
        sigungu_cd: str,
        bjdong_cd: str = "",
        bun: str = "",
        ji: str = "",
        start_date: str = "",
        end_date: str = "",
        num_of_rows: int = 100,
    ) -> dict:
        """
        건축인허가 주택유형 정보를 조회합니다.
        아파트/연립/다세대/단독 등 유형별 세대수를 반환합니다.

        Args:
            sigungu_cd: 시군구 5자리 코드 (예: '11680' = 강남구)
            bjdong_cd: 법정동 5자리 코드 (빈 값이면 시군구 전체)
            bun: 번지 본번 (선택)
            ji: 번지 부번 (선택)
            start_date: 검색 시작일 YYYYMMDD
            end_date: 검색 종료일 YYYYMMDD
            num_of_rows: 최대 조회 건수

        Returns:
            total_count, items(건물명/대지위치/주택유형/가구수/세대수)
        """
        return await run_arch_pms_tool(
            ARCH_PMS_HSTP_URL, sigungu_cd, bjdong_cd, _parse_hstp, "건축인허가 주택유형",
            bun=bun, ji=ji, start_date=start_date, end_date=end_date, num_of_rows=num_of_rows,
        )
