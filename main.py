"""
일일 전략 실행 스크립트
========================
매일 장 시작 전(예: 08:30) cron으로 실행합니다.

실행:
    python main.py

cron 예시 (매일 08:30):
    30 8 * * 1-5 cd /path/to/timefolio-engine && python main.py
"""

import os
import logging
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

from timefolio.api_client import TimefolioAPIClient
from timefolio.trader     import TimefolioTrader
from backtest.data        import load_universe, download_prices, get_sector_map
from backtest.engine      import apply_constraints
from backtest.strategy    import compute_target_weights  # ← 전략 교체 시 여기만 변경

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
EMAIL    = os.environ["TIMEFOLIO_EMAIL"]
PASSWORD = os.environ["TIMEFOLIO_PASSWORD"]
PF_ID    = int(os.environ.get("TIMEFOLIO_PF_ID", 0))

MIN_ORDER_WEIGHT = 0.01   # 이 비중 미만의 매수/매도는 실행하지 않음 (슬리피지 방지)
PRICE_LOOKBACK   = 200    # 전략 신호 계산에 필요한 과거 거래일 수


# ---------------------------------------------------------------------------
# 티커 변환 유틸리티
# ---------------------------------------------------------------------------

def to_prod_id(yf_ticker: str) -> str:
    """yfinance 티커 → 대회 주문 티커. 예: 005930.KS → A005930"""
    return "A" + yf_ticker.replace(".KS", "")

def to_yf_ticker(prod_id: str) -> str:
    """대회 주문 티커 → yfinance 티커. 예: A005930 → 005930.KS"""
    return prod_id.lstrip("A") + ".KS"


# ---------------------------------------------------------------------------
# 현재 포트폴리오 파싱
# ---------------------------------------------------------------------------

def get_current_weights(trader: TimefolioTrader) -> pd.Series:
    """대회 API에서 현재 보유 비중을 가져옵니다.

    반환: pd.Series (yf_ticker → 비중). 현금 포함 기준.

    ⚠️ API 응답 구조는 실제 계정으로 get_balance()를 호출해 확인하세요.
    아래는 응답 예시 기준이며 필드명이 다를 수 있습니다.
    """
    balance = trader.get_balance()
    if not balance:
        log.error("포트폴리오 조회 실패")
        return pd.Series(dtype=float)

    # --- API 응답 구조 확인 후 아래를 수정하세요 ---
    # 예시 응답 형태:
    # {
    #   "nav": 1020000000,
    #   "holdings": [
    #     {"prodId": "A005930", "weight": 0.08},
    #     ...
    #   ]
    # }
    holdings = balance.get("holdings", [])
    weights  = {
        to_yf_ticker(h["prodId"]): float(h["weight"])
        for h in holdings
        if "prodId" in h and "weight" in h
    }
    return pd.Series(weights)


# ---------------------------------------------------------------------------
# 주문 생성
# ---------------------------------------------------------------------------

def compute_orders(
    target: pd.Series,
    current: pd.Series,
    min_weight: float = MIN_ORDER_WEIGHT,
) -> tuple[pd.Series, pd.Series]:
    """목표 비중과 현재 비중의 차이로 매수/매도 주문을 생성합니다.

    Returns: (buy_orders, sell_orders) — 각각 pd.Series(yf_ticker → 주문 비중)
    """
    all_tickers = target.index.union(current.index)
    delta = (target.reindex(all_tickers, fill_value=0.0)
             - current.reindex(all_tickers, fill_value=0.0))

    buy  = delta[delta >  min_weight]
    sell = delta[delta < -min_weight].abs()
    return buy, sell


# ---------------------------------------------------------------------------
# 주문 실행
# ---------------------------------------------------------------------------

def execute_orders(
    trader: TimefolioTrader,
    buy: pd.Series,
    sell: pd.Series,
    use_twap: bool = True,
) -> None:
    """매도 먼저, 매수 나중에 실행합니다.

    use_twap: True면 09:00~14:50 TWAP 분할 주문 (시장 충격 최소화)
    """
    hm0 = "09:00" if use_twap else None
    hm1 = "14:50" if use_twap else None

    # 매도 먼저 (현금 확보)
    for yf_ticker, weight in sell.items():
        prod_id = to_prod_id(yf_ticker)
        result  = trader.order(prod_id=prod_id, weight=weight, ls="S", hm0=hm0, hm1=hm1)
        if result:
            log.info("매도 주문: %s %.2f%%", prod_id, weight * 100)

    # 매수
    for yf_ticker, weight in buy.items():
        prod_id = to_prod_id(yf_ticker)
        result  = trader.order(prod_id=prod_id, weight=weight, ls="L", hm0=hm0, hm1=hm1)
        if result:
            log.info("매수 주문: %s %.2f%%", prod_id, weight * 100)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    log.info("=== 일일 전략 실행 시작 [%s] ===", today)

    # 1. 로그인
    api    = TimefolioAPIClient(email=EMAIL, password=PASSWORD)
    if not api.login():
        raise RuntimeError("로그인 실패 — .env 파일 확인")
    trader = TimefolioTrader(api_client=api, pf_id=PF_ID)

    # 2. 유니버스 + 최근 주가 다운로드
    log.info("주가 다운로드 중...")
    universe   = load_universe()
    sector_map = get_sector_map(universe)

    end   = today
    start = (datetime.now() - timedelta(days=int(PRICE_LOOKBACK * 1.5))).strftime("%Y-%m-%d")
    prices = download_prices(universe, start=start, end=end)

    if prices.empty:
        log.error("주가 데이터 없음 — 종료")
        return

    # 3. 전략 실행 → 목표 비중
    log.info("전략 실행 중...")
    raw_target = compute_target_weights(prices)

    if raw_target.empty:
        log.warning("전략 신호 없음 — 데이터 부족 가능성")
        return

    raw_target  = raw_target[raw_target.index.isin(prices.columns)]
    target_weights = apply_constraints(raw_target, sector_map)
    log.info("목표 편입 종목: %d개", len(target_weights))

    # 4. 현재 포트폴리오 조회
    current_weights = get_current_weights(trader)
    log.info("현재 편입 종목: %d개", len(current_weights))

    # 5. 주문 생성
    buy_orders, sell_orders = compute_orders(target_weights, current_weights)
    log.info("매수 %d건, 매도 %d건", len(buy_orders), len(sell_orders))

    if buy_orders.empty and sell_orders.empty:
        log.info("리밸런싱 불필요 — 종료")
        return

    # 6. 주문 실행
    execute_orders(trader, buy_orders, sell_orders)
    log.info("=== 실행 완료 ===")


if __name__ == "__main__":
    main()
