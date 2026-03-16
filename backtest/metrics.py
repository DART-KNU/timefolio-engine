from __future__ import annotations

import numpy as np
import pandas as pd

from .config import RISK_FREE_RATE_ANNUAL, RISK_FREE_RATE_DAILY, MIN_WEEKLY_TURNOVER, MAX_TURNOVER_VIOLATIONS


def compute_metrics(nav: pd.Series) -> dict:
    """NAV 시계열로 주요 성과 지표 계산.

    Returns: total_return, cagr, volatility, sharpe_ratio, max_drawdown, calmar_ratio, win_rate (모두 %)
    """
    ret = nav.pct_change().dropna()
    if len(ret) < 2:
        return {k: float("nan") for k in
                ["total_return", "cagr", "volatility", "sharpe_ratio", "max_drawdown", "calmar_ratio", "win_rate"]}

    n_years      = len(ret) / 252
    total_return = nav.iloc[-1] / nav.iloc[0] - 1.0
    cagr         = (1.0 + total_return) ** (1.0 / n_years) - 1.0
    vol          = ret.std() * np.sqrt(252)
    sharpe       = (ret.mean() - RISK_FREE_RATE_DAILY) / ret.std() * np.sqrt(252)
    mdd          = ((nav - nav.cummax()) / nav.cummax()).min()
    calmar       = cagr / abs(mdd) if mdd != 0 else 0.0

    return {
        "total_return": round(total_return * 100, 2),
        "cagr"        : round(cagr * 100, 2),
        "volatility"  : round(vol * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown": round(mdd * 100, 2),
        "calmar_ratio": round(calmar, 3),
        "win_rate"    : round((ret > 0).mean() * 100, 1),
    }


def print_report(nav: pd.Series, turnover_log: pd.DataFrame, turnover_violations: int) -> None:
    """백테스트 성과 보고서 출력."""
    m = compute_metrics(nav)

    print("=" * 52)
    print("           백테스트 성과 보고서")
    print("=" * 52)
    print(f"  기간            : {nav.index[0].date()} ~ {nav.index[-1].date()}")
    print(f"  초기 NAV        : {nav.iloc[0]:>15,.0f} 원")
    print(f"  최종 NAV        : {nav.iloc[-1]:>15,.0f} 원")
    print("-" * 52)
    print(f"  총 수익률       : {m['total_return']:>8.2f} %")
    print(f"  연 환산 수익률  : {m['cagr']:>8.2f} %")
    print(f"  연 변동성       : {m['volatility']:>8.2f} %")
    print(f"  샤프 비율       : {m['sharpe_ratio']:>8.3f}  (RF = {RISK_FREE_RATE_ANNUAL*100:.2f} %)")
    print(f"  최대 낙폭(MDD)  : {m['max_drawdown']:>8.2f} %")
    print(f"  칼마 비율       : {m['calmar_ratio']:>8.3f}")
    print(f"  일간 승률       : {m['win_rate']:>8.1f} %")
    print("-" * 52)

    ok = turnover_violations < MAX_TURNOVER_VIOLATIONS
    print(f"  주간 회전율 위반: {turnover_violations}회 ({MAX_TURNOVER_VIOLATIONS}회부터 수상 제외)  {'✅' if ok else '❌ 수상 제외'}")
    if not turnover_log.empty and "turnover" in turnover_log.columns:
        avg = turnover_log["turnover"].mean() * 100
        low = turnover_log["turnover"].min() * 100
        print(f"  평균 주간 회전율: {avg:.2f} %  (최저 {low:.2f} %, 기준 {MIN_WEEKLY_TURNOVER*100:.0f} %)")
    print("=" * 52)
