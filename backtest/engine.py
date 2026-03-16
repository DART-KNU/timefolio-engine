from __future__ import annotations

from typing import Callable, Optional

import pandas as pd

from .config import (
    MAX_SINGLE_WEIGHT,
    MAX_SAMSUNG_WEIGHT,
    MAX_SMALL_CAP_WEIGHT,
    MIN_WEEKLY_TURNOVER,
    MAX_TURNOVER_VIOLATIONS,
    SAMSUNG_YF,
    sector_max_weight,
)


def _enforce_min_turnover(
    new_weights: pd.Series,
    old_weights: pd.Series,
    min_turnover: float,
) -> pd.Series:
    """회전율이 min_turnover 미만이면 포트폴리오 변화를 스케일 업해서 최소 회전율 보장."""
    all_tickers = new_weights.index.union(old_weights.index)
    new = new_weights.reindex(all_tickers, fill_value=0.0)
    old = old_weights.reindex(all_tickers, fill_value=0.0)
    diff = new - old
    current_turnover = diff.abs().sum() / 2.0
    if current_turnover >= min_turnover or current_turnover == 0:
        return new_weights
    scale = min_turnover / current_turnover
    adjusted = (old + diff * scale).clip(lower=0)
    total = adjusted.sum()
    if total > 0:
        adjusted = adjusted / total
    return adjusted[adjusted > 0]


def apply_constraints(
    raw_weights: pd.Series,
    sector_map: dict[str, str],
    is_large_cap: Optional[dict[str, bool]] = None,
) -> pd.Series:
    """RFM 대회 제약조건 적용 후 정규화된 비중 반환.

    is_large_cap: yf_ticker → 시총 1조 이상 여부. None이면 소형주 제약 미적용.
    """
    w = raw_weights.copy().clip(lower=0)
    if w.sum() == 0:
        return w

    # 1. 개별 종목 비중 캡
    if SAMSUNG_YF in w:
        w[SAMSUNG_YF] = min(w[SAMSUNG_YF], MAX_SAMSUNG_WEIGHT)
    for ticker in w.index:
        if ticker != SAMSUNG_YF:
            w[ticker] = min(w[ticker], MAX_SINGLE_WEIGHT)

    # 2. 섹터 비중 캡 — 초과 섹터 종목을 비례 축소
    sector_totals: dict[str, float] = {}
    for ticker, weight in w.items():
        sc = sector_map.get(ticker, "Unknown")
        sector_totals[sc] = sector_totals.get(sc, 0.0) + weight

    for sc, total in sector_totals.items():
        cap = sector_max_weight(sc)
        if total > cap:
            scale = cap / total
            for ticker in w.index:
                if sector_map.get(ticker) == sc:
                    w[ticker] *= scale

    # 3. 소형주(시총 1조 미만) 합산 30% 캡
    if is_large_cap is not None:
        small = [t for t in w.index if not is_large_cap.get(t, True)]
        small_total = w[small].sum()
        if small_total > MAX_SMALL_CAP_WEIGHT:
            scale = MAX_SMALL_CAP_WEIGHT / small_total
            for ticker in small:
                w[ticker] *= scale

    total = w.sum()
    return w / total if total > 0 else w


def run_backtest(
    prices: pd.DataFrame,
    strategy_fn: Callable[[pd.DataFrame], pd.Series],
    sector_map: dict[str, str],
    is_large_cap: Optional[dict[str, bool]] = None,
    rebal_freq: str = "W-FRI",
    initial_nav: float = 1_000_000_000,
    buy_cost: float = 0.0010,
    sell_cost: float = 0.0030,
) -> dict:
    """주간 리밸런싱 백테스트 실행.

    체결 가정 (옵션 A): 리밸런싱일 t 종가로 신호 계산 → t+1일부터 새 비중 적용.
    자세한 내용은 backtest/README.md를 참고하세요.

    Returns: nav, weight_history, turnover_log, turnover_violations, final_weights
    """
    dates = prices.index.sort_values()
    if len(dates) < 2:
        raise ValueError("주가 데이터가 부족합니다 (최소 2일 필요).")

    rebal_dates = set(prices.resample(rebal_freq).last().index.intersection(dates))

    nav            = initial_nav
    nav_series     = pd.Series(index=dates, dtype=float)
    weight_history = pd.DataFrame(index=dates, dtype=float)
    nav_series.iloc[0] = nav

    weights: pd.Series = pd.Series(dtype=float)
    turnover_log: list[dict] = []
    violations = 0

    for i in range(1, len(dates)):
        date, prev = dates[i], dates[i - 1]

        # Step 1: 오늘 수익 계산 (전날 비중 기준) — 옵션 A
        if not weights.empty:
            held = weights.index.intersection(prices.columns)
            if not held.empty:
                prev_px = prices.loc[prev, held]
                curr_px = prices.loc[date, held]
                valid = prev_px > 0
                daily_ret = (curr_px[valid] / prev_px[valid] - 1.0).fillna(0.0)
                nav *= 1.0 + (weights.reindex(daily_ret.index, fill_value=0.0) * daily_ret).sum()

        nav_series[date] = nav

        # Step 2: 리밸런싱 — 오늘 종가로 신호 계산, 내일부터 적용 — 옵션 A
        if date in rebal_dates:
            raw_w = strategy_fn(prices.loc[:date])
            if not raw_w.empty:
                raw_w = raw_w[raw_w.index.isin(prices.columns)]
                new_weights = apply_constraints(raw_w, sector_map, is_large_cap)
                new_weights = _enforce_min_turnover(new_weights, weights, MIN_WEEKLY_TURNOVER)
            else:
                new_weights = weights.copy()

            all_tickers = weights.index.union(new_weights.index)
            turnover = float(
                (new_weights.reindex(all_tickers, fill_value=0.0)
                 - weights.reindex(all_tickers, fill_value=0.0)).abs().sum() / 2.0
            )
            violated = turnover < MIN_WEEKLY_TURNOVER
            if violated:
                violations += 1
            turnover_log.append({"date": date, "turnover": turnover, "violated": violated})

            nav *= 1.0 - turnover * (buy_cost + sell_cost) / 2.0
            weights = new_weights

        if not weights.empty:
            weight_history.loc[date, weights.index] = weights.values

    if violations >= MAX_TURNOVER_VIOLATIONS:
        print(f"[경고] 주간 회전율 위반 {violations}회 → 대회 수상 제외")

    return {
        "nav"                : nav_series.dropna(),
        "weight_history"     : weight_history.dropna(how="all"),
        "turnover_log"       : pd.DataFrame(turnover_log) if turnover_log else pd.DataFrame(),
        "turnover_violations": violations,
        "final_weights"      : weights,
    }
