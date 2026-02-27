# config.py
import os
from dotenv import load_dotenv

# .env 파일의 내용을 환경변수로 불러옵니다.
load_dotenv()

EMAIL = os.getenv("TIMEFOLIO_EMAIL")
PASSWORD = os.getenv("TIMEFOLIO_PASSWORD")
DEFAULT_PF_ID = int(os.getenv("TIMEFOLIO_PF_ID", 18762))