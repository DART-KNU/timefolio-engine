# 📈 timefolio-engine

> DART(경북대) 내부 연구/교육 목적의 알고리즘 트레이딩 **프레임워크(껍데기)** 입니다.  
> 본 레포는 특정 플랫폼/대회와 **비공식(unofficial)** 으로 연동될 수 있는 어댑터 구조를 제공하되, 실제 사용은 **플랫폼의 이용약관·규정·허가된 인터페이스 범위 내**에서만 수행해야 합니다.

**Not affiliated with Timefolio.**  
자동매매/웹자동화/비공식 API 사용 여부는 대회 규정 및 서비스 약관을 우선합니다.

---

## ✅ Scope

이 프로젝트는 다음을 목표로 합니다.

- **Strategy-first**: `main.py`에서 전략 로직만 바꿔 끼우면 실행 가능
- **Adapter-based design**: 플랫폼/브로커/데이터 소스를 쉽게 교체
- **Operational hygiene**: `.env` 기반 시크릿 관리, 로깅/예외처리, 재현 가능한 실행

> ⚠️ 본 레포는 접근제어 회피, 우회 로직, 보안 취약점 악용 등 **비정상적 사용을 다루지 않습니다.**

---

## 🏗️ Architecture

확장성과 유지보수를 위해 “thin entrypoint + package core” 형태로 구성합니다.

```

.
├─ timefolio/                 # (Adapter Layer) 플랫폼/브로커 연동 모듈
│  ├─ api_client.py            # 인증/세션/요청 래퍼(허가된 범위 내 호출)
│  └─ trader.py                # 주문/조회 공통 인터페이스 + 구현체
├─ config.py                   # 환경변수 로딩 및 전역 설정
├─ main.py                     # 전략 실행 엔트리포인트
├─ .env.example                # 환경변수 템플릿 (커밋 OK)
└─ .env                        # 시크릿 (커밋 금지)

````

---

## 🛠️ Setup

### 1) Create venv
```bash
python -m venv .venv
# Windows Git Bash
source .venv/Scripts/activate
````

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

`.env.example`을 복사해서 `.env`를 만들고 값을 채웁니다.

```bash
cp .env.example .env   # Windows PowerShell이면 Copy-Item 사용
```

`.env` 예시:

```text
PLATFORM_EMAIL=your_email@example.com
PLATFORM_PASSWORD=your_password
PLATFORM_PF_ID=00000
```

> 🔐 `.env`는 절대 커밋하지 마세요. (이미 커밋했다면 히스토리 제거까지 필요)

---

## 🚀 Key Features

### 1) Trading primitives (strategy-ready)

* `order()` / `cancel()` / `positions()` / `balance()` 등 **전략에 필요한 최소 인터페이스**
* 주문 파라미터는 “전략 관점”으로 통일

  * **비중 기반 주문(weight)**: 총자산 대비 비중으로 포지션 사이징

### 2) Execution helpers (optional)

플랫폼이 허용하는 범위에서:

* 분할 집행(TWAP 등)과 같은 **집행 헬퍼 레이어**
* 주문 실패/부분 체결/재시도에 대한 **예외 처리와 로깅**

> 집행 알고리즘은 플랫폼 제약(주문 빈도/유형 제한)에 맞춰 구현되어야 합니다.

### 3) Data feed interface (planned)

* `pykrx` 등 외부 데이터 소스를 연결해

  * 실시간/준실시간 시세 조회(가능 범위 내)
  * 팩터/리밸런싱 입력 데이터 생성

---

## 🔒 Security & Ops

* `.env`로 시크릿 관리 (하드코딩 금지)
* `.gitignore`로 `.env`, `.venv`, 캐시/로그/데이터 아티팩트 제외
* 실행 로그/에러 로그를 남기고, 실패 시 안전하게 종료하도록 설계

---

## 🧪 Suggested Workflow

1. `main.py`에서 전략 정의
2. `timefolio/trader.py`가 제공하는 인터페이스로 주문/조회
3. 결과를 로그/리포트로 저장(추후 자동 리포팅 확장)

---

## 📅 Roadmap

* [x] Adapter 패키징 (`api_client`, `trader`)
* [x] `.env` 기반 시크릿 분리 및 기본 운영 구조
* [ ] 데이터 수집 모듈 연동 (`pykrx` 등)
* [ ] **Adaptive MVO Engine**: 공분산 추정/리밸런싱 자동화
* [ ] 백테스트/페이퍼트레이딩 모드(동일 전략 코드로 재현 가능하게)
* [ ] 리스크 관리 모듈(최대 익스포저, 손실 제한, 거래 제한)

---

## 📎 Disclaimer

* 본 프로젝트는 교육/연구 목적입니다.
* 자동매매/연동 사용은 해당 플랫폼의 정책과 규정을 준수해야 합니다.
* 본 레포는 특정 회사/대회와 무관합니다.