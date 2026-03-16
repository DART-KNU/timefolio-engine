# 무위험 수익률: 한국은행 기준금리 2.75% (2026년 2월)
# 변경 시 이 값만 수정하면 샤프 비율 등 모든 지표에 자동 반영됨
RISK_FREE_RATE_ANNUAL = 0.0275
RISK_FREE_RATE_DAILY  = (1 + RISK_FREE_RATE_ANNUAL) ** (1 / 252) - 1

# 대회 제약 (RFM 11회 기준)
MAX_SINGLE_WEIGHT    = 0.15   # 단일 종목 (삼성전자 제외)
MAX_SAMSUNG_WEIGHT   = 0.40   # 삼성전자(005930.KS)
MAX_SMALL_CAP_WEIGHT = 0.30   # 시총 1조 미만 합산
SMALL_CAP_THRESHOLD  = 1e12   # 소형주 기준: 1조 원
MIN_MARKET_CAP       = 1e11   # 편입 불가: 1,000억 원 미만
MIN_TRADE_VALUE      = 3e9    # 편입 불가: 5일 평균 거래대금 30억 미만

MIN_WEEKLY_TURNOVER     = 0.05
MAX_TURNOVER_VIOLATIONS = 3

SAMSUNG_YF      = "005930.KS"
UNIVERSE_FILE   = "RFM-11-sector.txt"

# KOSPI200 GICS 섹터 비중 (2025년 말 기준, 분기별 갱신 필요)
SECTOR_WEIGHTS: dict[str, float] = {
    "IT": 0.35, "Fi": 0.14, "In": 0.11, "CD": 0.09, "He": 0.08,
    "Ma": 0.07, "Co": 0.05, "CS": 0.04, "En": 0.03, "Ut": 0.03, "Re": 0.01,
}


def sector_max_weight(sector_code: str) -> float:
    """섹터별 포트폴리오 최대 편입 비중.
    시장 비중 × 2, 단 시장 비중 ≤ 5%이면 최대 10%.
    """
    mkt_w = SECTOR_WEIGHTS.get(sector_code, 0.0)
    return 0.10 if mkt_w <= 0.05 else min(mkt_w * 2.0, 1.0)
