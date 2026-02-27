# 📈 Timefolio Algorithm Trading Bot (AdaptiveMVO-Engine)

타임폴리오자산운용의 'Road to Fund Manager' 모의투자 대회 API를 리버스 엔지니어링하여 구축한 알고리즘 트레이딩 엔진입니다. 
객체지향(OOP) 구조와 가상환경 기반 보안 설정을 통해 안정적인 포트폴리오 운용 및 자동 매매를 지원합니다.

## 🏗️ 시스템 아키텍처
본 프로젝트는 확장성과 유지보수를 위해 **4-Files System**으로 설계되었습니다.

* `timefolio/`: 핵심 라이브러리 패키지
    * `api_client.py`: 서버 통신 및 Bearer 토큰 인증 전담
    * `trader.py`: 알고리즘 주문(TWAP, Limit, Stop) 및 조회 로직 전담
* `config.py`: `.env` 파일을 로드하여 전역 설정을 관리하는 브릿지
* `main.py`: 전략(MVO 등)을 실행하고 봇을 구동하는 엔트리 포인트
* `.env`: 계정 및 비밀번호 등 민감 정보를 보관 (Git 제외 대상)

## 🛠️ 설치 및 설정 가이드 (Setup)

### 1. 가상환경 생성 및 활성화
```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (Windows Git Bash 기준)
source .venv/Scripts/activate

```

### 2. 라이브방 설치

```bash
pip install -r requirements.txt

```

### 3. 환경변수 세팅 (`.env`)

최상위 폴더에 `.env` 파일을 생성하고 본인의 계정 정보를 입력합니다.

```text
TIMEFOLIO_EMAIL=cmschs03@naver.com
TIMEFOLIO_PASSWORD=your_password
TIMEFOLIO_PF_ID=18762  # 연습용 대회 ID

```

---

## 🚀 주요 기능 (Key Features)

### 1. 기관급 알고리즘 주문

단순 매수/매도가 아닌, 시간 분할(TWAP) 및 호가 제어 기능을 지원합니다.

* **비중 주문 (`wei`)**: 총자산 대비 %로 주문 (0.05 = 5%)
* **시간 분할 (`hm0`, `hm1`)**: 장중 평균가 매집을 위한 TWAP 로직
* **호가 제어 (`limit_idx`)**: 1~10 단계의 상대/자기호가 설정

### 2. 주말 및 공휴일 예약 우회

서버의 개장일 체크 로직을 우회하여 주말에도 차주 개장일(예: 3월 3일)로 예약 주문을 생성할 수 있습니다.

```python
# 사용 예시: 화요일 개장일 예약
bot.order(
    prod_id="A005380", weight=0.05, 
    hm0="09:00", target_date="2026-03-03"
)

```

---

## 🛡️ 보안 (Security)

* **`.env` 관리**: 본 프로젝트는 계정 정보를 소스코드에 하드코딩하지 않습니다.
* **`.gitignore`**: `.env`, `.venv`, `__pycache__` 등은 Git 추적에서 제외되어 안전한 공유가 가능합니다.

---

## 📅 로드맵 (Roadmap)

* [x] API 객체지향 패키징
* [x] 가상환경 및 `.env` 보안 강화
* [ ] `pykrx` 기반 주가 및 시가총액 데이터 수집기 연동
* [ ] **Adaptive MVO Engine**: 수집 데이터 기반 공분산 행렬 계산 및 최적 비중 산출 자동화