# api_client.py
import requests
import logging

class TimefolioAPIClient:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.base_url = "https://contest.timefolio.net/api"
        self.session = requests.Session()
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://contest.timefolio.net",
            "Referer": "https://contest.timefolio.net/"
        }

    def login(self):
        """서버에 로그인하고 토큰(입장권)을 헤더에 장착합니다."""
        logging.info("로그인을 시도합니다...")
        url = f"{self.base_url}/Auth/Login"
        payload = {"email": self.email, "password": self.password}
        
        res = self.session.post(url, json=payload, headers=self.headers)
        if res.status_code == 200:
            token = res.json().get("token") or res.json().get("accessToken")
            if token:
                self.headers["Authorization"] = f"Bearer {token}"
                logging.info("✅ 서버 인증(로그인) 성공!")
                return True
        logging.error(f"❌ 로그인 실패: {res.text}")
        return False

    def post(self, endpoint, payload=None):
        """POST 요청을 전담합니다."""
        url = f"{self.base_url}/{endpoint}"
        return self.session.post(url, json=payload, headers=self.headers)

    def get(self, endpoint, params=None):
        """GET 요청을 전담합니다."""
        url = f"{self.base_url}/{endpoint}"
        return self.session.get(url, params=params, headers=self.headers)