from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

from .config import UNIVERSE_FILE


def load_universe(filepath: Optional[str] = None) -> pd.DataFrame:
    """RFM-11-sector.txt 유니버스 로드.

    반환 컬럼: sector_code, sector_name, ticker(A005930), name, yf_ticker(005930.KS)
    """
    path = Path(filepath) if filepath else Path(__file__).parent.parent / UNIVERSE_FILE
    df = pd.read_csv(path, sep="\t", dtype=str)
    df.columns = ["sector_code", "sector_name", "ticker", "name"]
    df["yf_ticker"] = df["ticker"].str[1:] + ".KS"  # A005930 → 005930.KS
    return df.reset_index(drop=True)


def get_sector_map(universe: pd.DataFrame) -> dict[str, str]:
    """yf_ticker → sector_code 매핑."""
    return dict(zip(universe["yf_ticker"], universe["sector_code"]))


def download_prices(
    universe: pd.DataFrame,
    start: str,
    end: str,
    chunk_size: int = 100,
) -> pd.DataFrame:
    """yfinance 수정주가 다운로드 (행: 거래일, 열: yf_ticker).

    상장폐지 등 데이터 없는 종목은 자동 제외됩니다.
    처음 실행 후 save_prices()로 캐시하면 재실행 시 빠릅니다.
    DataGuide CSV가 있다면 load_prices_from_csv()를 사용하세요.
    """
    chunks: list[pd.DataFrame] = []
    tickers = universe["yf_ticker"].tolist()

    for i in range(0, len(tickers), chunk_size):
        batch = tickers[i : i + chunk_size]
        raw = yf.download(batch, start=start, end=end, auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
        else:
            close = raw[["Close"]]
            close.columns = batch
        chunks.append(close)

    prices = pd.concat(chunks, axis=1)
    prices.index = pd.to_datetime(prices.index)
    return prices.sort_index().dropna(axis=1, how="all")


def load_prices_from_csv(filepath: str, universe: pd.DataFrame) -> pd.DataFrame:
    """DataGuide CSV 수정주가 로드.

    CSV 형식: 첫 컬럼=날짜, 이후 컬럼=종목코드(A005930 또는 005930).
    """
    df = pd.read_csv(filepath, index_col=0, parse_dates=True).sort_index()
    df.columns = [c.lstrip("A") + ".KS" for c in df.columns]
    valid = set(universe["yf_ticker"])
    return df[[c for c in df.columns if c in valid]].dropna(axis=1, how="all")


def save_prices(prices: pd.DataFrame, path: str) -> None:
    """주가를 parquet으로 저장."""
    prices.to_parquet(path)


def load_prices(path: str) -> pd.DataFrame:
    """저장된 parquet 주가 로드."""
    return pd.read_parquet(path)
