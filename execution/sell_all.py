"""
계좌 정보 조회 + 보유 주식 전량 매도 스크립트
=============================================
1. Timefolio 로그인
2. SignalR로 현재 포지션/잔고 조회
3. 보유 종목 전체 EXIT 주문 실행
"""

import sys
import os
import time
import logging
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가 (패키지 미설치 환경 대비)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# 프로젝트 루트의 .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, ".env"))
except ImportError:
    pass

from timefolio import TimefolioAPIClient, TimefolioTrader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sell_all")

MAX_RETRIES = 3
RETRY_DELAY = 5
BATCH_SIZE = 5
BATCH_SLEEP = 10


def get_account_info(trader):
    """계좌 잔고 요약 조회 (REST API)"""
    balance = trader.get_balance()
    if balance:
        print(f"\n{'=' * 60}")
        print(f"  계좌 요약 (pfId: {trader.pf_id})")
        print(f"{'=' * 60}")
        for key, val in balance.items():
            print(f"  {key}: {val}")
    else:
        print("\n  계좌 요약 조회 실패")
    return balance


def get_current_positions(trader):
    """SignalR로 현재 포지션 조회"""
    logger.info("SignalR 연결 → 현재 포지션 조회 중...")
    trader.connect_realtime()
    time.sleep(5)

    positions = trader.get_positions() or []
    holdings = trader.get_holdings()
    orders = trader.get_orders() or []

    trader.disconnect_realtime()

    # 포지션 파싱
    current = []
    for pos in positions:
        prod_id = (pos.get("prodId") or pos.get("ProdId")
                   or pos.get("prod_id") or pos.get("ticker"))
        wei = float(pos.get("wei") or pos.get("Wei")
                    or pos.get("weight") or pos.get("Weight") or 0)
        name = (pos.get("prodNm") or pos.get("ProdNm")
                or pos.get("name") or prod_id)

        if prod_id and wei > 0:
            current.append({"code": prod_id, "name": name, "weight": wei})

    # 미채결 주문 종목
    pending_codes = set()
    for o in orders:
        state = o.get("state") or o.get("State") or ""
        if state in ("Generated", "Submitted", "PartiallyFilled"):
            pid = o.get("prodId") or o.get("ProdId") or ""
            if pid:
                pending_codes.add(pid)

    return current, holdings, pending_codes


def print_positions(positions):
    """보유 종목 출력"""
    if not positions:
        print("\n  보유 종목 없음 (빈 포트폴리오)")
        return

    positions.sort(key=lambda x: x["weight"], reverse=True)
    total_weight = sum(p["weight"] for p in positions)

    print(f"\n{'=' * 60}")
    print(f"  보유 종목: {len(positions)}개  |  총 비중: {total_weight:.4f}%")
    print(f"{'=' * 60}")
    print(f"  {'#':>3}  {'코드':<8}  {'종목명':<20}  {'비중(%)':>8}")
    print(f"  {'-' * 50}")
    for i, p in enumerate(positions, 1):
        print(f"  {i:>3}  {p['code']:<8}  {p['name']:<20}  {p['weight']:>7.4f}%")
    print(f"  {'-' * 50}")
    print(f"  {'합계':>33}  {total_weight:>7.4f}%")


def submit_exit_order(trader, code, name, weight):
    """단일 EXIT 주문 (재시도 포함)"""
    today = datetime.now().strftime("%Y-%m-%d")
    hm0 = datetime.now().strftime("%H:%M")

    for attempt in range(MAX_RETRIES):
        try:
            payload = {
                "d": today,
                "pfId": trader.pf_id,
                "prodId": code,
                "ls": "L",
                "ex": "X",
                "wei": round(weight, 2),
                "exitAll": True,
                "hm0": hm0,
                "hm1": None,
                "limitIdx": 5,
                "limitPrc": None,
                "stopPrc": None,
            }
            res = trader.api.post("Portfolio/AddOrder", payload=payload)

            if res.status_code == 200:
                return True, None

            if res.status_code == 503:
                wait = RETRY_DELAY * (attempt + 1)
                logger.warning(f"  503 ({code}) → {wait}초 후 재시도 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue

            return False, res.text[:80] if res.text else f"HTTP {res.status_code}"

        except Exception as e:
            wait = RETRY_DELAY * (attempt + 1)
            logger.warning(f"  오류 ({code}) → {wait}초 후 재시도: {e}")
            time.sleep(wait)

    return False, "최대 재시도 초과"


def sell_all(trader, positions, pending_codes):
    """보유 종목 전량 매도"""
    # 미채결 종목 제외
    to_sell = [p for p in positions if p["code"] not in pending_codes]
    skipped = [p for p in positions if p["code"] in pending_codes]

    if skipped:
        print(f"\n  미채결 주문 있어 스킵: {', '.join(p['name'] for p in skipped)}")

    if not to_sell:
        print("  매도할 종목이 없습니다.")
        return

    total = len(to_sell)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    success = 0
    fail = 0

    for i in range(0, total, BATCH_SIZE):
        batch = to_sell[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        print(f"\n  배치 {batch_num}/{total_batches}  ({i+1}~{i+len(batch)}/{total})")
        print(f"  {'-' * 45}")

        for p in batch:
            ok, err = submit_exit_order(trader, p["code"], p["name"], p["weight"])
            if ok:
                success += 1
                print(f"    [OK]   EXIT  {p['name']:<16}  {p['code']}  wei={p['weight']:.4f}%")
            else:
                fail += 1
                print(f"    [FAIL] EXIT  {p['name']:<16}  {p['code']}  {err}")

        if i + BATCH_SIZE < total:
            print(f"    ... {BATCH_SLEEP}초 대기 ...")
            time.sleep(BATCH_SLEEP)

    print(f"\n{'=' * 50}")
    print(f"  전량 매도 완료  |  성공: {success}건  실패: {fail}건  전체: {total}건")
    print(f"{'=' * 50}")


def main():
    EMAIL = os.environ.get("TIMEFOLIO_EMAIL")
    PASSWORD = os.environ.get("TIMEFOLIO_PASSWORD")
    PF_ID = int(os.environ.get("TIMEFOLIO_PF_ID", 19252))

    if not EMAIL or not PASSWORD:
        print("ERROR: .env에 TIMEFOLIO_EMAIL, TIMEFOLIO_PASSWORD를 설정하세요.")
        sys.exit(1)

    # 로그인
    print(f"\n  Timefolio 로그인 중...")
    api = TimefolioAPIClient(email=EMAIL, password=PASSWORD)
    if not api.login():
        raise RuntimeError("로그인 실패!")

    trader = TimefolioTrader(api_client=api, pf_id=PF_ID)
    logger.info(f"Trader ready (pfId={trader.pf_id})")

    # 1. 계좌 정보 조회
    get_account_info(trader)

    # 2. 포지션 조회
    positions, holdings, pending_codes = get_current_positions(trader)
    print_positions(positions)

    if holdings:
        print(f"\n  잔고 정보: {holdings}")

    if not positions:
        print("\n  보유 종목이 없어 종료합니다.")
        return

    # 3. 전량 매도 실행
    print(f"\n{'=' * 50}")
    print(f"  전량 매도 시작")
    print(f"{'=' * 50}")
    sell_all(trader, positions, pending_codes)


if __name__ == "__main__":
    main()
