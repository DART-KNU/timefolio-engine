"""
timefolio
=========
Python client library for the Timefolio mock investment contest API.

Quick start::

    from timefolio import TimefolioAPIClient, TimefolioTrader

    api = TimefolioAPIClient(email="you@example.com", password="secret")
    api.login()

    trader = TimefolioTrader(api_client=api, pf_id=18762)
    trader.order(prod_id="A005930", weight=0.05, ls="L")
"""

from .api_client import TimefolioAPIClient
from .trader import TimefolioTrader

__all__ = ["TimefolioAPIClient", "TimefolioTrader"]
__version__ = "0.1.0"
