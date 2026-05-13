"""
timefolio
=========
Python client library for the Timefolio mock investment contest API.

Quick start::

    from timefolio import TimefolioAPIClient, TimefolioTrader, TimefolioCollector

    api = TimefolioAPIClient(email="you@example.com", password="secret")
    api.login()

    # Trading
    trader = TimefolioTrader(api_client=api, pf_id=18762)
    trader.order(prod_id="A005930", weight=0.05, ls="L")

    # Leaderboard & portfolio collection
    collector = TimefolioCollector(api_client=api, contest_id=86)
    leaderboard = collector.get_leaderboard()
    df = collector.collect_all_holdings(top_n=20)
    collector.save_snapshot(df)
"""

from .api_client import TimefolioAPIClient
from .trader import TimefolioTrader
from .collector import TimefolioCollector

__all__ = ["TimefolioAPIClient", "TimefolioTrader", "TimefolioCollector"]
__version__ = "0.1.0"
