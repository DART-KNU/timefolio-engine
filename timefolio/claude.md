# Developer Context & System Architecture for AI Assistant

Hello, AI Assistant! This document provides the architectural context, strictly reverse-engineered API specifications, and the exact constraints of the `Timefolio Algorithm Trading Bot`. 
Please read this carefully before generating code, especially when integrating the **Adaptive Mean-Variance Optimization (MVO) Engine** or advanced execution algorithms.

## 1. Core Architecture (OOP Design)
The project strictly separates concerns into 4 files to isolate HTTP complexities from quantitative strategies.

* **`config.py`**: Holds credentials (`EMAIL`, `PASSWORD`) and `DEFAULT_PF_ID`.
* **`api_client.py`**: `TimefolioAPIClient` class. Manages `requests.Session()`, injects the Bearer token into headers, and handles raw `GET`/`POST` methods.
* **`trader.py`**: `TimefolioTrader` class. Uses the API client to construct specific endpoint payloads. Handles business logic (Orders, Cancellations, Check Violations).
* **`main.py`**: The strategy execution layer.

## 2. API Endpoint & Payload Specifications
The server provides internal endpoints for a mock investment competition ("Road to Fund Manager"). It does **NOT** provide real-time or historical market data (external libraries like `pykrx` must be used for price feeds).

### 2.1 Add Order (`POST /api/Portfolio/AddOrder`)
This is the most critical endpoint. It supports advanced algorithmic execution (TWAP, Limit, Stop, Order Book Depth) natively handled by the server. 

**Payload JSON Structure & Advanced Options:**
```json
{
    "d": "2026-02-27",      // String: Target business date (YYYY-MM-DD). Must NOT be a weekend.
    "pfId": 18762,          // Integer: Portfolio ID.
    "prodId": "A005930",    // String: Ticker symbol prefixed with 'A' (e.g., A + 005930).
    "ls": "L",              // String: 'L' for Long (Buy), 'S' for Short/Sell.
    "ex": "E",              // String: Execution type ('E' is standard algorithm).
    "wei": 0.05,            // Float: Weight of total portfolio (0.05 = 5%).
    "exitAll": false,       // Boolean: True if liquidating the entire position.
    
    // --- Advanced Execution Parameters ---
    "hm0": "09:00",         // String or Null: Order Start Time (HH:MM). Null = immediate execution.
    "hm1": "15:20",         // String or Null: Order End Time (HH:MM). Used with hm0 for TWAP (Time-Weighted Average Price) execution.
    "limitIdx": 5,          // Integer (1~10): Relative/Own order book depth (상대호가/자기호가). Higher = more aggressive.
    "limitPrc": 80000,      // Float or Null: Specific Limit Price (지정가). Set to Null for algo/market price.
    "stopPrc": 75000        // Float or Null: Stop-loss / Stop-limit trigger price (STOP가). Set to Null if not used.
}