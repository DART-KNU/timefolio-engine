"""
TimefolioTrader
---------------
High-level trading operations built on top of :class:`TimefolioAPIClient`.

All order parameters map directly to the server's ``Portfolio/AddOrder``
endpoint.  Refer to the payload spec in ``timefolio/claude.md`` for the
authoritative field descriptions.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class TimefolioTrader:
    """Executes trading operations against a Timefolio contest portfolio.

    Uses :class:`TimefolioAPIClient` for all HTTP communication (Composition
    pattern), keeping trading logic cleanly separated from transport concerns.

    :param api_client: An *authenticated* :class:`TimefolioAPIClient` instance.
    :param pf_id: Contest portfolio ID (``pfId``).
    """

    def __init__(self, api_client, pf_id: int) -> None:
        self.api = api_client
        self.pf_id = pf_id

    # ------------------------------------------------------------------
    # Portfolio selection
    # ------------------------------------------------------------------

    def set_tournament(self, target_name: str = "연습용 대회") -> bool:
        """Switch the active portfolio to the contest whose name contains *target_name*.

        Calls ``Auth/SilentRefresh`` to fetch the list of enrolled portfolios
        and selects the first one whose ``ctstNm`` field contains *target_name*.

        :param target_name: Substring to match against the contest name field.
        :returns: ``True`` if a matching portfolio was found and set.
        """
        res = self.api.post("Auth/SilentRefresh")
        if res.status_code == 200:
            for pf in res.json().get("pfs", []):
                if target_name in pf.get("ctstNm", ""):
                    self.pf_id = pf["Id"]
                    logger.info(
                        "Switched to contest '%s' (pfId: %s)", target_name, self.pf_id
                    )
                    return True

        logger.error("Contest '%s' not found.", target_name)
        return False

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    def order(
        self,
        prod_id: str,
        weight: float,
        ls: str = "L",
        ex: str = "E",
        limit_idx: int = 5,
        limit_prc: Optional[float] = None,
        stop_prc: Optional[float] = None,
        hm0: Optional[str] = None,
        hm1: Optional[str] = None,
        target_date: Optional[str] = None,
    ) -> Optional[dict]:
        """Submit an order to the contest portfolio.

        The server natively supports market, TWAP, limit, and stop execution
        styles through the parameters below.  All advanced options default to
        ``None`` (immediate market execution at the best available price).

        :param prod_id:
            Ticker symbol prefixed with ``"A"``, e.g. ``"A005930"``
            (Samsung Electronics).
        :param weight:
            Portfolio weight to allocate — ``0.05`` means 5 % of total NAV.
        :param ls:
            ``"L"`` for Long/Buy, ``"S"`` for Short/Sell.
        :param ex:
            Execution type.  ``"E"`` is the standard server-side algorithm.
        :param limit_idx:
            Order-book aggressiveness on a scale of 1–10.
            Higher values are more aggressive and more likely to fill quickly.
        :param limit_prc:
            Exact limit price (지정가).  ``None`` → algo/market price.
        :param stop_prc:
            Stop-loss / stop-limit trigger price.  ``None`` → disabled.
        :param hm0:
            Order start time ``"HH:MM"``.  ``None`` → execute immediately.
        :param hm1:
            Order end time ``"HH:MM"`` for TWAP time-sliced execution.
            Only meaningful when *hm0* is also set.
        :param target_date:
            Target business date ``"YYYY-MM-DD"``.  ``None`` → today.
            Must not be a weekend or public holiday.
        :returns:
            Parsed JSON response ``dict`` on success, ``None`` on failure.
        """
        target_d = target_date or datetime.now().strftime("%Y-%m-%d")
        hm0_val = hm0 or datetime.now().strftime("%H:%M")

        payload = {
            "d": target_d,
            "pfId": self.pf_id,
            "prodId": prod_id,
            "ls": ls,
            "ex": ex,
            "wei": weight,
            "exitAll": False,
            "hm0": hm0_val,
            "hm1": hm1,
            "limitIdx": limit_idx,
            "limitPrc": limit_prc,
            "stopPrc": stop_prc,
        }

        res = self.api.post("Portfolio/AddOrder", payload=payload)
        if res.status_code == 200:
            logger.info(
                "Order submitted [%s] %s weight=%.1f%% | "
                "limitPrc=%s stopPrc=%s hm0=%s hm1=%s",
                ls, prod_id, weight * 100, limit_prc, stop_prc, hm0_val, hm1,
            )
            return res.json()

        logger.error("Order submission failed (HTTP %s): %s", res.status_code, res.text)
        return None

    def cancel_order(self, ord_id: int) -> Optional[dict]:
        """Cancel an existing order by its server-assigned order ID.

        :param ord_id: Order ID returned in the response of a prior :meth:`order` call.
        :returns: Parsed JSON response on success, ``None`` on failure.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        payload = {"d": today, "pfId": self.pf_id, "ordId": ord_id}
        res = self.api.post("Portfolio/DeleteOrder", payload=payload)
        if res.status_code == 200:
            logger.info("Order cancelled (ordId: %s)", ord_id)
            return res.json()

        logger.error(
            "Cancel failed for ordId=%s (HTTP %s): %s",
            ord_id, res.status_code, res.text,
        )
        return None

    def get_balance(self) -> Optional[dict]:
        """Retrieve today's portfolio summary (holdings, cash, NAV, P&L).

        :returns: Parsed JSON response on success, ``None`` on failure.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        res = self.api.get("Portfolio/Summary", params={"pfId": self.pf_id, "d": today})
        if res.status_code == 200:
            return res.json()

        logger.error(
            "get_balance failed (HTTP %s): %s", res.status_code, res.text
        )
        return None
