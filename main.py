import logging
import config
from timefolio.api_client import TimefolioAPIClient
from timefolio.trader import TimefolioTrader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def run_strategy():
    api = TimefolioAPIClient(config.EMAIL, config.PASSWORD)
    if not api.login():
        logging.error("로그인에 실패하여 봇을 종료합니다.")
        return 

    bot = TimefolioTrader(api_client=api, pf_id=config.DEFAULT_PF_ID)

    print("\n--- 🤖 타임폴리오 트레이딩 봇 구동 시작 ---")
    
    # ==========================================
    # 🎯 주말 테스트용 주문 실행 파트 (현대차로 변경!)
    # ==========================================
    # 현대차(A005380) 5% 매수 예약 주문 (금요일 기준 09:00)
    bot.order(
        prod_id="A005380", weight=0.10, ls="L", 
        hm0="09:00", hm1="12:20", target_date="2026-03-03"
    )

if __name__ == "__main__":
    run_strategy()