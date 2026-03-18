"""
TimefolioTrader
---------------
High-level trading operations built on top of :class:`TimefolioAPIClient`.
"""

import logging
import time
import threading
from datetime import datetime
from typing import Optional

from signalrcore.hub_connection_builder import HubConnectionBuilder

logger = logging.getLogger(__name__)


class TimefolioTrader:

    def __init__(self, api_client, pf_id: int) -> None:
        self.api = api_client
        self.pf_id = pf_id
        self._holdings = None
        self._orders = None
        self._positions = None
        self._hub = None

    # ------------------------------------------------------------------
    # Portfolio selection
    # ------------------------------------------------------------------

    def set_tournament(self, target_name: str = "연습용 대회") -> bool:
        res = self.api.post("Auth/SilentRefresh")
        if res.status_code == 200:
            for pf in res.json().get("pfs", []):
                if target_name in pf.get("ctstNm", ""):
                    self.pf_id = pf["Id"]
                    logger.info(
                        "Switched to contest '%s' (pfId: %s)",
                        target_name, self.pf_id
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
                ls, prod_id, weight * 100,
                limit_prc, stop_prc, hm0_val, hm1,
            )
            return res.json()

        logger.error(
            "Order submission failed (HTTP %s): %s",
            res.status_code, res.text
        )
        return None

    def cancel_order(self, ord_id: int) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        payload = {"d": today, "pfId": self.pf_id, "ordId": ord_id}
        res = self.api.post("Portfolio/DeleteOrder", payload=payload)
        
        # 200 또는 204면 성공으로 처리
        if res.status_code in (200, 204):
            logger.info("Order cancelled (ordId: %s)", ord_id)
            # 응답 내용 있으면 반환, 없으면 True
            try:
                return res.json()
            except Exception:
                return True  # 빈 응답도 성공!

        logger.error(
            "Cancel failed for ordId=%s (HTTP %s): %s",
            ord_id, res.status_code, res.text,
        )
        return False

    def cancel_all_pending(self) -> int:
        """미접수 주문 전체 취소"""
        pending = self.get_pending_orders()
        if not pending:
            logger.info("취소할 미접수 주문 없음")
            return 0

        cancelled = 0
        for order in pending:
            ord_id = order.get("Id")
            if ord_id and self.cancel_order(ord_id):
                cancelled += 1
                logger.info(
                    "미접수 취소: %s %s (Id: %s)",
                    order.get("prodNm"),
                    order.get("wei"),
                    ord_id
                )

        logger.info("총 %d건 취소 완료", cancelled)
        return cancelled

    def cancel_pending_by_stock(self, prod_id: str) -> int:
        """특정 종목 미접수 주문만 취소"""
        pending = self.get_pending_orders()
        target = [o for o in pending
                  if o.get("prodId") == prod_id]

        if not target:
            logger.info("%s 미접수 주문 없음", prod_id)
            return 0

        cancelled = 0
        for order in target:
            ord_id = order.get("Id")
            if ord_id and self.cancel_order(ord_id):
                cancelled += 1

        logger.info("%s 미접수 %d건 취소 완료", prod_id, cancelled)
        return cancelled

    def get_balance(self) -> Optional[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        res = self.api.get(
            "Portfolio/Summary",
            params={"pfId": self.pf_id, "d": today}
        )
        if res.status_code == 200:
            return res.json()

        logger.error(
            "get_balance failed (HTTP %s): %s",
            res.status_code, res.text
        )
        return None

    # ------------------------------------------------------------------
    # SignalR 실시간 연결
    # ------------------------------------------------------------------

    def connect_realtime(self) -> None:
        """SignalR WebSocket 연결 및 실시간 데이터 수신 시작"""
        token = self.api.get_token()

        self._hub = HubConnectionBuilder()\
            .with_url(
                "wss://contest.timefolio.net/hubs/main",
                options={
                    "access_token_factory": lambda: token,
                    "verify_ssl": True
                }
            )\
            .build()

        self._hub.on("ReceivePortfolio", self._on_portfolio_update)
        self._hub.start()
        logger.info("SignalR 연결 완료")
        self._request_portfolio()

    def _request_portfolio(self) -> None:
        """서버에 포트폴리오 데이터 요청"""
        self._hub.send("RequestPortfolio", [{
            "intv": 3,
            "auto": True,
            "lastT": int(time.time()),
            "d": datetime.now().strftime("%Y-%m-%d"),
            "pfId": self.pf_id
        }])

    def _on_portfolio_update(self, data: list) -> None:
        """ReceivePortfolio 메시지 수신 핸들러"""
        if not data:
            return

        portfolio = data[0]

        if portfolio.get("bs") is not None:
            self._holdings = portfolio["bs"]
            logger.info("보유잔고 업데이트: %s", self._holdings)

        if portfolio.get("ords") is not None:
            self._orders = portfolio["ords"]
            logger.info("주문 업데이트: %s", self._orders)

        if portfolio.get("pos") is not None:
            self._positions = portfolio["pos"]
            logger.info("포지션 업데이트: %s", self._positions)

    # ------------------------------------------------------------------
    # 실시간 데이터 조회
    # ------------------------------------------------------------------

    def get_holdings(self) -> Optional[dict]:
        """보유잔고 조회"""
        return self._holdings

    def get_orders(self) -> Optional[list]:
        """주문 목록 조회"""
        return self._orders

    def get_positions(self) -> Optional[list]:
        """포지션 조회"""
        return self._positions

    def get_pending_orders(self) -> list:
        """미접수 주문만 필터링"""
        if not self._orders:
            return []
        return [o for o in self._orders
                if o.get("state") == "Generated"]

    def get_error_orders(self) -> list:
        """에러 주문만 필터링"""
        if not self._orders:
            return []
        return [o for o in self._orders
                if o.get("errMsg") is not None]

    def disconnect_realtime(self) -> None:
        """SignalR 연결 종료"""
        if self._hub:
            self._hub.stop()
            logger.info("SignalR 연결 종료")