# timefolio-engine

> DART(경북대) 내부 연구/교육 목적의 타임폴리오 대회 API 래퍼입니다.
> 본 레포는 비공식(unofficial) 연동 구조를 제공하며, 실제 사용은 **플랫폼의 이용약관·규정·허가된 인터페이스 범위 내**에서만 수행해야 합니다.

**Not affiliated with Timefolio.**

---

## 구조

```
timefolio-engine/
├── timefolio/               # 라이브러리 본체
│   ├── __init__.py          # TimefolioAPIClient, TimefolioTrader, TimefolioCollector export
│   ├── api_client.py        # 인증·세션·HTTP 래퍼
│   ├── trader.py            # 주문·취소·잔고 조회
│   └── collector.py         # 리더보드·포트폴리오 수집
├── execution/               # 실행 스크립트
│   └── sell_all.py          # 보유 주식 전량 매도
├── examples/
│   └── quickstart.ipynb     # 사용 예제 노트북
├── requirements.txt
├── setup.py
└── .env                     # 시크릿 (커밋 금지, gitignore 처리됨)
```

---

## 설치

```bash
# 1. (권장) 가상환경 생성 — 버전 충돌 방지
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# source .venv/bin/activate     # macOS / Linux

# 2. 패키지 설치
pip install -r requirements.txt

# 라이브러리로 사용할 경우 (import timefolio)
pip install -e .
```

> 가상환경 없이 `pip install -r requirements.txt`로 바로 설치해도 됩니다.
> 다만 다른 프로젝트와 패키지 버전이 충돌할 수 있으니 가상환경 사용을 권장합니다.

---

## 환경변수 설정

프로젝트 루트에 `.env` 파일을 만들고 아래 내용을 채웁니다.

```text
TIMEFOLIO_EMAIL=your_email@example.com
TIMEFOLIO_PASSWORD=your_password
TIMEFOLIO_PF_ID=18762
```

> `.env`는 절대 커밋하지 마세요. (이미 `.gitignore`에 포함되어 있습니다.)

---

## 빠른 시작

```python
from timefolio import TimefolioAPIClient, TimefolioTrader

api = TimefolioAPIClient(email="you@example.com", password="secret")
api.login()

trader = TimefolioTrader(api_client=api, pf_id=18762)

# 삼성전자 5% 즉시 매수
trader.order(prod_id="A005930", weight=5, ls="L")

# 현대차 10% TWAP 매수 (09:00~12:20)
trader.order(prod_id="A005380", weight=10, ls="L", hm0="09:00", hm1="12:20")

# 잔고 조회
trader.get_balance()
```

더 자세한 예제는 **`examples/quickstart.ipynb`** 를 참고하세요.

---

## 실행 스크립트

### 전량 매도 (`execution/sell_all.py`)

보유 종목을 한 번에 전량 매도하는 스크립트입니다.

```bash
python execution/sell_all.py
```

동작 순서:
1. `.env`에서 계정 정보 로드 → 로그인
2. SignalR 실시간 연결로 현재 포지션/잔고 조회
3. 미채결 주문 종목 제외 후 나머지 전량 EXIT 주문 실행

> 배치 단위(5건)로 주문하며, 503 에러 시 자동 재시도합니다.

---

## API 주요 파라미터

| 파라미터 | 설명 |
|---|---|
| `prod_id` | 종목코드 (`A` 접두 필수, 예: `A005930`) |
| `weight` | 포트폴리오 비중 (`5` = 5%) |
| `ls` | `"L"` 매수 / `"S"` 매도 |
| `limit_idx` | 호가 공격성 1–10 (기본 5) |
| `limit_prc` | 지정가 — `None` 시 알고리즘 가격 |
| `stop_prc` | STOP 가격 — `None` 시 미사용 |
| `hm0` / `hm1` | 주문 시작/종료 시간 (`"HH:MM"`) — TWAP 실행 |
| `target_date` | 기준 영업일 (`"YYYY-MM-DD"`) — `None` 시 오늘 |

---

## v1.0 범위

- [x] `TimefolioAPIClient` — 인증, GET/POST 래퍼
- [x] `TimefolioTrader` — 주문, 취소, 잔고 조회
- [x] TWAP / 지정가 / STOP 주문 옵션
- [x] `.env` 기반 시크릿 분리
- [ ] 계좌 데이터 상세 조회 (v1.x 예정)
- [ ] pykrx 데이터 피드 연동
- [ ] MVO 리밸런싱 예제

---

## 주의사항

- 본 프로젝트는 교육·연구 목적입니다.
- 자동매매·API 연동 사용은 해당 플랫폼의 정책과 규정을 준수해야 합니다.
- 본 레포는 Timefolio와 무관합니다.
