# trader.py
from datetime import datetime
import logging

class TimefolioTrader:
    def __init__(self, api_client, pf_id):
        """
        :param api_client: 로그인된 TimefolioAPIClient 객체
        :param pf_id: 대회 포트폴리오 ID
        """
        self.api = api_client  # 통신 모듈을 장착! (Composition 패턴)
        self.pf_id = pf_id

    def set_tournament(self, target_name="연습용 대회"):
        res = self.api.post("Auth/SilentRefresh")
        if res.status_code == 200:
            pfs = res.json().get("pfs", [])
            for pf in pfs:
                if target_name in pf.get("ctstNm", ""):
                    self.pf_id = pf["Id"]
                    logging.info(f"🎯 [{target_name}] 모드 전환 (pfId: {self.pf_id})")
                    return True
        logging.error(f"❌ '{target_name}' 대회를 찾을 수 없습니다.")
        return False

    def order(self, prod_id, weight, ls="L", ex="E", 
                limit_idx=5, limit_prc=None, stop_prc=None, 
                hm0=None, hm1=None, target_date=None):
            """
            🚀 [궁극의 주문 함수] 타임폴리오의 모든 알고리즘 옵션을 제어합니다.
            
            :param prod_id: 종목코드 (예: "A005930")
            :param weight: 주문 비중 (0.01 = 1%)
            :param ls: "L" (매수) / "S" (매도)
            :param ex: "E" (기본 알고리즘 실행 타입 추정)
            :param limit_idx: 상대/자기호가 설정 (1~10). 숫자가 클수록 체결에 유리한 호가.
            :param limit_prc: 지정가 (특정 가격에 딱 맞춰 사고 팔 때). 안 쓰면 None.
            :param stop_prc: STOP 가격 (손절매, 혹은 돌파매매용). 안 쓰면 None.
            :param hm0: 주문 시작 시간 ("09:00" 등). 즉시 실행 시 None.
            :param hm1: 주문 종료 시간 ("15:20" 등). 시간 분할 매매 시에만 입력.
            :param target_date: 기준 영업일 (주말 예약 테스트용)
            """
            # 날짜와 시작 시간이 안 들어오면 '오늘', '지금'으로 자동 세팅
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
                "hm0": hm0_val,       # 시작 시간 (즉시 or 예약)
                "hm1": hm1,           # 종료 시간 (시간 분할)
                "limitIdx": limit_idx,# 상대/자기호가 (1~10)
                "limitPrc": limit_prc,# 지정가
                "stopPrc": stop_prc   # STOP가
            }

            res = self.api.post("Portfolio/AddOrder", payload=payload)
            if res.status_code == 200:
                logging.info(f"✅ 주문 제출 성공 [{ls}] {prod_id} 비중:{weight*100}% | 옵션: limitPrc={limit_prc}, stopPrc={stop_prc}, hm0={hm0_val}, hm1={hm1}")
                return res.json()
            logging.error(f"❌ 주문 제출 실패: {res.text}")
            return None
    
    def cancel_order(self, ord_id):
        today = datetime.now().strftime("%Y-%m-%d")
        payload = {"d": today, "pfId": self.pf_id, "ordId": ord_id}
        res = self.api.post("Portfolio/DeleteOrder", payload=payload)
        if res.status_code == 200:
            logging.info(f"🗑️ 주문 취소 성공 [주문번호: {ord_id}]")
            return res.json()
        return None

    def get_balance(self):
        today = datetime.now().strftime("%Y-%m-%d")
        params = {"pfId": self.pf_id, "d": today}
        res = self.api.get("Portfolio/Summary", params=params) # 임시 URL
        if res.status_code == 200:
            return res.json()
        return None