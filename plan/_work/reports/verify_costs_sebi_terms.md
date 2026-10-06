# Verification Report: Indian Costs, SEBI Regulations & Terms of Use

**Research Topic**: Indian Transaction Costs, SEBI Algo Framework, Fyers Redistribution Terms  
**Date of Research**: 2026-10-05  
**Reviewer/Researcher**: Stage A Quant Architect Researcher  

---

## 1. Indian Equity Transaction Costs & Taxes (Statutory Breakdown)
- **Status**: VERIFIED
- **Source**: Fyers Brokerage Schedule (effective Oct 1, 2024), Union Budget Statutory Rates, NSE Circular on Transaction Charges
- **Detailed Structure**:
  1. **Brokerage (Fyers)**:
     - Equity Delivery: ₹20 or 0.3% per executed order, whichever is lower.
     - Equity Intraday: ₹20 or 0.03% per executed order, whichever is lower.
  2. **Securities Transaction Tax (STT)**:
     - Equity Delivery: **0.1%** on Both Buy and Sell turnover.
     - Equity Intraday: **0.025%** on Sell turnover only.
  3. **Exchange Transaction Charges (NSE Cash)**:
     - **0.00297%** of trade turnover.
  4. **SEBI Turnover Fee**:
     - **₹10 per crore** (0.0001% of turnover) on both Buy and Sell.
  5. **GST (Goods & Services Tax)**:
     - **18%** levied on: `Brokerage + Exchange Transaction Charges + SEBI Turnover Fee`.
  6. **Stamp Duty (Indian Stamp Act)**:
     - Equity Delivery: **0.015%** on Buy turnover only.
     - Equity Intraday: **0.003%** on Buy turnover only.
  7. **Investor Protection Fund Trust (IPFT)**:
     - ₹10 per crore on equity cash turnover.
- **Architectural Implementation**:
  - Phase 14 (Backtesting Engine) must implement a versioned, parameterized cost model (`IndianEquityCostModel`) that computes these exact fees per trade with arithmetic traceability, rather than an arbitrary flat percentage assumption.

---

## 2. SEBI Retail Algorithmic Trading Framework
- **Status**: VERIFIED
- **Source**: SEBI Retail Algorithmic Trading Circulars (effective framework)
- **Key Provisions**:
  - **Static IP Whitelisting**: Mandatory for API-based automated order routing.
  - **Orders Per Second (OPS)**: 10 OPS limit for retail API orders; exceeding 10 OPS requires institutional-grade strategy approval.
  - **Exchange Algo ID**: Unique identifier required for every automated order routed to the exchange.
  - **Daily 2FA**: Mandatory daily interactive authentication.
- **Applicability to this Platform**:
  - **NOT APPLICABLE to current scope**: This application is strictly an **NSE Equity Data & Research Platform** (Find $\rightarrow$ Analyze $\rightarrow$ Test $\rightarrow$ Monitor $\rightarrow$ Review). Order placement and execution are strictly **OUT OF SCOPE**.
  - **Compliance Boundary (Phase 19)**: If order execution is ever proposed in future versions, SEBI's static IP, algo ID registration, and broker risk management framework constitute an uncompromisable regulatory hard gate.

---

## 3. Fyers Terms of Service on Data Redistribution
- **Status**: VERIFIED
- **Source**: Fyers API Terms of Service & End-User License Agreement
- **Paraphrase**: Market data accessed via Fyers API is licensed solely for the personal, non-commercial use of the account holder. Commercial redistribution, reselling, or public sublicensing of downloaded raw data to third parties is strictly prohibited.
- **System Compliance**:
  - Exports (Parquet, CSV, Excel) are strictly for local personal analysis.
  - Exported files must include metadata specifying: Source (Fyers API), personal non-commercial license note, survivorship bias disclosure, and corporate action adjustment status.
