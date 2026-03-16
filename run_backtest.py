"""백테스트 실행 진입점. 전략 교체는 backtest/strategy.py를 수정하세요."""

import os

import matplotlib.pyplot as plt

from backtest.data     import download_prices, get_sector_map, load_prices, load_universe, save_prices
from backtest.engine   import run_backtest
from backtest.metrics  import print_report
from backtest.strategy import compute_target_weights

BACKTEST_START = "2022-01-01"
BACKTEST_END   = "2026-04-01"
PRICE_CACHE    = "prices_cache.parquet"


def main() -> None:
    print("[1/4] 유니버스 로드 중...")
    universe   = load_universe()
    sector_map = get_sector_map(universe)
    print(f"      종목 수: {len(universe)}개")

    print("[2/4] 주가 로드 중...")
    if os.path.exists(PRICE_CACHE):
        prices = load_prices(PRICE_CACHE)
    else:
        print("      yfinance 다운로드 중... (수 분 소요)")
        prices = download_prices(universe, start=BACKTEST_START, end=BACKTEST_END)
        save_prices(prices, PRICE_CACHE)
    print(f"      {prices.index[0].date()} ~ {prices.index[-1].date()}, {len(prices.columns)}종목")

    print("[3/4] 백테스트 실행 중...")
    result = run_backtest(prices, compute_target_weights, sector_map)

    print("[4/4] 성과 보고서")
    print_report(result["nav"], result["turnover_log"], result["turnover_violations"])

    nav = result["nav"]
    fig, ax = plt.subplots(figsize=(12, 5))
    (nav / nav.iloc[0] * 100).plot(ax=ax, label="전략", color="steelblue")
    ax.set_title("포트폴리오 누적 수익률")
    ax.set_ylabel("수익률 지수 (기준 = 100)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig("backtest_result.png", dpi=150)
    print("\n차트 저장: backtest_result.png")
    plt.show()


if __name__ == "__main__":
    main()
