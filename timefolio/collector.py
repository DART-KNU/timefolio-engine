"""
TimefolioCollector
------------------
대회 리더보드 및 참가자 포트폴리오를 수집하는 고수준 클라이언트.
모든 HTTP 요청은 :class:`TimefolioAPIClient`의 ``get`` 헬퍼를 통해 수행한다.
"""

import logging
import time
import os
from datetime import datetime
from typing import Optional

import pandas as pd

from .api_client import TimefolioAPIClient

logger = logging.getLogger(__name__)


class TimefolioCollector:
    """대회 리더보드 및 참가자 포트폴리오 수집기.

    :param api_client: 이미 ``login()``이 완료된 :class:`TimefolioAPIClient` 인스턴스
    :param contest_id: 대회 ID (기본값 86 = RFM 11기)
    """

    def __init__(self, api_client: TimefolioAPIClient, contest_id: int = 86) -> None:
        self.api = api_client
        self.contest_id = contest_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _today(self) -> str:
        """오늘 날짜를 'YYYY-MM-DD' 형식으로 반환한다."""
        return datetime.now().strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------

    def get_leaderboard(self, date: str = None) -> list:
        """전체 참가자 리더보드를 반환한다.

        ``GET /api/Contest/PfList?ctstId={contest_id}&d={date}``

        :param date: 조회 날짜 ('YYYY-MM-DD'). None이면 오늘 날짜를 사용한다.
        :returns: 참가자 목록 (list of dict). 실패 시 빈 리스트.
        """
        date = date or self._today()
        res = self.api.get(
            "Contest/PfList",
            params={"ctstId": self.contest_id, "d": date},
        )
        if res.status_code == 200:
            data = res.json()
            # 응답이 list이면 그대로, dict이면 내부 리스트를 탐색
            if isinstance(data, list):
                entries = data
            elif isinstance(data, dict):
                entries = next(
                    (v for v in data.values() if isinstance(v, list)),
                    [data],
                )
            else:
                return []

            # API는 rank=None으로 반환하므로 rt(누적수익률) 기준 정렬
            def _score(entry: dict) -> float:
                stat = entry.get("stat") or {}
                return stat.get("rt") or 0.0

            entries = sorted(entries, key=_score, reverse=True)

            # 정렬 후 rank 부여 (1-based)
            for i, entry in enumerate(entries, start=1):
                entry["rank"] = i

            return entries

        logger.error(
            "get_leaderboard failed (HTTP %s): %s",
            res.status_code, res.text,
        )
        return []

    def get_top_leaders(self, date: str = None, top_n: int = 20) -> list:
        """상위 top_n명의 리더보드를 반환한다.

        :param date: 조회 날짜. None이면 오늘.
        :param top_n: 반환할 최대 참가자 수.
        :returns: 상위 top_n명 목록.
        """
        return self.get_leaderboard(date=date)[:top_n]

    # ------------------------------------------------------------------
    # Portfolio detail
    # ------------------------------------------------------------------

    def get_portfolio_detail(self, pf_id: int, date: str = None) -> Optional[dict]:
        """특정 참가자의 포트폴리오 상세 정보를 반환한다.

        ``GET /api/Contest/TopRankDetail?d={date}&pfId={pf_id}``

        :param pf_id: 참가자 포트폴리오 ID.
        :param date: 조회 날짜. None이면 오늘.
        :returns: 포트폴리오 상세 dict. 실패 시 None.
        """
        date = date or self._today()
        res = self.api.get(
            "Contest/TopRankDetail",
            params={"d": date, "pfId": pf_id},
        )
        if res.status_code == 200:
            return res.json()

        logger.error(
            "get_portfolio_detail failed for pfId=%s (HTTP %s): %s",
            pf_id, res.status_code, res.text,
        )
        return None

    def get_holdings(self, pf_id: int, date: str = None) -> list:
        """특정 참가자의 보유종목 리스트를 반환한다.

        :meth:`get_portfolio_detail` 응답의 ``prfts`` 키를 추출한다.

        :param pf_id: 참가자 포트폴리오 ID.
        :param date: 조회 날짜. None이면 오늘.
        :returns: 보유종목 리스트. ``prfts`` 키가 없으면 빈 리스트.
        """
        detail = self.get_portfolio_detail(pf_id=pf_id, date=date)
        if detail is None:
            return []
        holdings = detail.get("prfts", [])
        if not isinstance(holdings, list):
            logger.error(
                "Unexpected type for 'prfts' key (pfId=%s): %s",
                pf_id, type(holdings),
            )
            return []
        return holdings

    # ------------------------------------------------------------------
    # Bulk collection
    # ------------------------------------------------------------------

    def collect_all_holdings(
        self,
        date: str = None,
        top_n: int = 20,
        delay: float = 0.5,
    ) -> pd.DataFrame:
        """상위 top_n명의 보유종목을 전부 수집하여 DataFrame으로 반환한다.

        각 행에 ``captured_at``, ``participant_pfid``, ``participant_rank``
        컬럼이 추가된다.

        :param date: 조회 날짜. None이면 오늘.
        :param top_n: 수집할 상위 참가자 수.
        :param delay: 참가자 간 요청 딜레이(초).
        :returns: 보유종목 DataFrame.
        """
        date = date or self._today()
        leaders = self.get_top_leaders(date=date, top_n=top_n)
        if not leaders:
            logger.error("No leaderboard data returned for date=%s", date)
            return pd.DataFrame()

        captured_at = datetime.now().isoformat()
        rows = []

        for entry in leaders:
            pf_id = entry.get("Id") or entry.get("pfId") or entry.get("id")
            rank = entry.get("rank")
            name = entry.get("userNick") or entry.get("pfNm") or str(pf_id)

            if pf_id is None:
                logger.error("pfId not found in entry: %s", entry)
                continue

            holdings = self.get_holdings(pf_id=pf_id, date=date)
            logger.info("[%s위] %s (pfId=%s) → %d종목", rank, name, pf_id, len(holdings))

            for h in holdings:
                row = dict(h)
                row["captured_at"] = captured_at
                row["participant_pfid"] = pf_id
                row["participant_rank"] = rank
                rows.append(row)

            if delay > 0:
                time.sleep(delay)

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Violations
    # ------------------------------------------------------------------

    def get_violations(self, pf_id: int, date: str = None) -> Optional[dict]:
        """투자제한 위반 여부를 반환한다.

        ``GET /api/Contest/Violations?pfId={pf_id}&d={date}``

        :param pf_id: 참가자 포트폴리오 ID.
        :param date: 조회 날짜. None이면 오늘.
        :returns: 위반 정보 dict. 실패 시 None.
        """
        date = date or self._today()
        res = self.api.get(
            "Contest/Violations",
            params={"pfId": pf_id, "d": date},
        )
        if res.status_code == 200:
            return res.json()

        logger.error(
            "get_violations failed for pfId=%s (HTTP %s): %s",
            pf_id, res.status_code, res.text,
        )
        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_snapshot(self, df: pd.DataFrame, output_dir: str = "runs") -> str:
        """DataFrame을 날짜별 폴더에 CSV로 저장한다.

        저장 경로: ``{output_dir}/{date}/holdings_top{n}.csv``

        :param df: 저장할 DataFrame (:meth:`collect_all_holdings` 반환값).
        :param output_dir: 최상위 출력 디렉터리.
        :returns: 저장된 파일의 절대 경로.
        """
        date = self._today()
        n = df["participant_pfid"].nunique() if "participant_pfid" in df.columns else len(df)
        folder = os.path.join(output_dir, date)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"holdings_top{n}.csv")
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info("Snapshot saved → %s", os.path.abspath(path))
        return os.path.abspath(path)
