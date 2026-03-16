"""전략 파일 — compute_target_weights()를 수정해 본인 전략을 구현하세요.

반환: pd.Series(yf_ticker → 목표 비중). 제약조건은 engine.py에서 자동 적용됩니다.
룩어헤드 바이어스 주의사항은 backtest/README.md를 참고하세요.
"""

from __future__ import annotations

import pandas as pd


# ── 여기를 수정하세요 ──────────────────────────────────────────────────────────

def compute_target_weights(prices: pd.DataFrame) -> pd.Series:
    """종목별 목표 비중 반환 (yf_ticker → 비중).

    prices: 신호 계산 기준일(t)까지의 수정주가. 마지막 행 = t일 종가.
    반환된 비중은 t+1일부터 적용됩니다. (옵션 A, 룩어헤드 없음)
    """
    signal = _momentum(prices, lookback=63, skip=5)
    if signal.empty:
        return pd.Series(dtype=float)

    n = max(10, min(30, int(len(signal) * 0.2)))
    selected = signal.nlargest(n).index
    return pd.Series(1.0 / n, index=selected)  # 균등 비중


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _momentum(prices: pd.DataFrame, lookback: int, skip: int) -> pd.Series:
    """t-skip일 ~ t-skip-lookback일 수익률 (단기 반전 노이즈 제거).

    [옵션 A] end/start 모두 t 이전 데이터 → 룩어헤드 없음.
    """
    if len(prices) < lookback + skip + 2:
        return pd.Series(dtype=float)
    end   = prices.iloc[-(skip + 1)]
    start = prices.iloc[-(lookback + skip + 1)]
    return (end / start - 1.0).dropna()
