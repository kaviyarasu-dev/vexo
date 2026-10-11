# Phase 18: Beginner Learning Layer, Glossary & Contextual Education

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/08_FRONTEND_CHARTING_AND_DASHBOARD.md"
    - "plan/11_PERSONAS_AND_SIMPLE_PRO_UX.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md"
    - "plan/VERIFICATION_REPORT.md"
  produces:
    - "config/glossary.json"
    - "static/js/glossary_tooltip.js"
    - "static/js/guided_tutorial.js"
    - "static/css/education.css"
  exposes: []
  must_not_modify:
    - "plan/*"
    - "services/*"
    - "db/*"
  test_plan:
    unit_tests: "tests/unit/test_glossary_integrity.py"
    integration_tests: "tests/integration/test_tutorial_overlay.py"
    contract_tests: "tests/contract/test_glossary_schema.py"
    fixtures: "config/glossary.json"
    command: "pytest tests/unit/test_glossary_integrity.py tests/contract/test_glossary_schema.py -v"
  definition_of_done:
    - item: 1
      command: "python -c 'import json; g = json.load(open(\"config/glossary.json\")); terms = [\"vwap\", \"rsi\", \"macd\", \"bollinger_bands\", \"atr\", \"stt\", \"r_multiple\", \"max_pain\"]; assert all(t in g for t in terms)'"
      result: "Glossary registry contains verified, structured entries for all core platform terms."
    - item: 2
      command: "python -c 'import json; g = json.load(open(\"config/glossary.json\")); assert all(all(k in v for k in [\"definition\", \"analogy\", \"risk_warning\"]) for v in g.values())'"
      result: "100% of glossary entries possess the mandatory three-part schema: definition, analogy, and risk warning."
    - item: 3
      command: "pytest tests/integration/test_tutorial_overlay.py"
      result: "Guided first-scan tutorial sequence advances from Step 1 to Step 4 without DOM or JavaScript errors."
  failure_modes_and_recovery:
    - failure: "Missing glossary translation key on UI hover"
      detection: "Console warning: 'Glossary key [xyz] not found in config/glossary.json'"
      recovery: "Display fallback tooltip using humanized title casing and prompt administrator to update glossary.json"
    - failure: "Tutorial modal blocks interactive chart controls"
      detection: "User unable to click chart canvas during active tutorial"
      recovery: "Provide prominent 'Skip Tutorial' and 'Close' button with keyboard Esc shortcut"
  handoff:
    - "Structured educational glossary compiled and verified."
    - "Contextual tooltip engine and guided first-scan tutorial operational."
    - "Ready for Phase 19 regulatory compliance and safety."
```

---

## 1. Goal & User Jobs Served
Establish an educational, jargon-free learning layer embedded directly into the application interface adhering to the 00A Canonical Registry.

### Core User Jobs:
1. **Learn & Understand (Beginner)**: "Explain what these technical terms mean in simple Hindi/English analogies without treating me like a fool or overwhelming me with calculus."
2. **Contextual Clarity**: "When I hover over an indicator badge or metric on a chart, explain what it means, why it matters, and how misinterpreting it could lose me money."
3. **Safe Guided Start**: "Walk me step-by-step through my first stock scan so I understand how to interpret the results with realistic expectations."

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `GlossaryRegistry`: Solely responsible for storing, validating, and serving structured educational definitions.
  - `GlossaryTooltipController`: Solely responsible for binding hover events and rendering glassmorphic tooltip popovers.
  - `GuidedTutorialController`: Solely responsible for stepping users through the interactive first-scan onboarding walkthrough.
- **Open/Closed Principle (OCP)**:
  - Glossary content is completely decoupled in `config/glossary.json`. Adding new educational topics requires adding JSON entries without altering JavaScript rendering code.

---

## 3. Comprehensive Quantitative Glossary Architecture

### 3.1. Standardized Three-Part Educational Schema
Every glossary entry is strictly required to implement a three-part pedagogical schema:
1. **Plain Definition**: 1-2 sentence plain-language description eliminating confusing financial acronyms.
2. **Real-World Analogy**: An intuitive metaphor relatable to everyday life in India.
3. **Risk Warning ("How this can lose you money")**: A sobering, practical caution preventing false confidence.

### 3.2. Curated Content Registry (`config/glossary.json`)
```json
{
  "vwap": {
    "term": "Session VWAP (Volume Weighted Average Price)",
    "plain_label": "Intraday Average Price",
    "definition": "The true average price paid for all shares traded today, giving more weight to transactions with large volume.",
    "analogy": "Like the wholesale market price of onions over a full morning. If retail shops are selling far above it, you're paying a premium; if selling below, you're buying at a discount.",
    "risk_warning": "Buying when the price is far above VWAP means you are paying significantly more than the day's average buyer, making you vulnerable to sharp pullbacks."
  },
  "rsi": {
    "term": "RSI (Relative Strength Index)",
    "plain_label": "Momentum Meter",
    "definition": "A gauge measuring the speed and size of recent price changes on a scale of 0 to 100 to identify when a move is stretched.",
    "analogy": "Like a car's speedometer. If you drive at 120 km/h in city traffic (RSI > 70), the engine is overheating; if crawling in first gear (RSI < 30), it is heavily slowed down.",
    "risk_warning": "An 'oversold' stock (RSI < 30) can easily drop another 20% or 30%. Never buy blindly just because the RSI number is low; wait for confirmation."
  },
  "r_multiple": {
    "term": "R-Multiple",
    "plain_label": "Risk-to-Reward Ratio",
    "definition": "A measurement of trade profit or loss expressed as a multiple of your initial planned risk (Stop Loss).",
    "analogy": "If you wager ₹1,000 on a coin flip to win ₹3,000, you are making +3.0R. If you lose your ₹1,000, you lost -1.0R.",
    "risk_warning": "Focusing only on win rate while ignoring R-multiples is why many traders go broke: winning 9 trades of 0.2R (total +1.8R) and losing 1 trade of -5.0R wipes out your account."
  },
  "stt": {
    "term": "Securities Transaction Tax (STT)",
    "plain_label": "Government Trade Tax",
    "definition": "A direct tax levied by the Government of India on every purchase and sale of equity shares on stock exchanges.",
    "analogy": "Like GST paid at a restaurant, you must pay STT on delivery trades regardless of whether you made a profit or suffered a loss.",
    "risk_warning": "Overtrading small gains can result in taxes exceeding your gross profit. Always evaluate after-tax returns."
  },
  "max_pain": {
    "term": "Options Max Pain Strike",
    "plain_label": "Options Settlement Magnet",
    "definition": "The strike price where option sellers (typically large institutions) would lose the least money if the market closes there on expiry day.",
    "analogy": "Like a gravitational center on weekly expiry Thursdays where price often gets pulled to minimize institutional payouts.",
    "risk_warning": "Max Pain is a dynamic calculation, not a crystal ball. Sudden news or global market moves can violently push prices far away from the Max Pain level."
  }
}
```

### 3.3. Content Verification Process
- All glossary definitions are grounded in accredited financial education curriculum (National Institute of Securities Markets / NISM Certification modules and Zerodha Varsity).
- Definitions avoid speculative promotional language (e.g. "guaranteed returns", "foolproof setups") and emphasize capital protection.

---

## 4. Contextual "What Does This Mean?" Tooltip Engine

### 4.1. DOM Integration
- Any HTML element annotated with `data-glossary="vwap"` automatically receives hover and tap listeners:
```html
<span class="indicator-tag" data-glossary="vwap">Intraday Average (VWAP) ℹ️</span>
```

### 4.2. Glassmorphic Popover Card
Hovering renders an interactive popover:
```
┌────────────────────────────────────────────────────────┐
│ 📘 Intraday Average Price (VWAP)                       │
├────────────────────────────────────────────────────────┤
│ The average price paid for all shares traded today,    │
│ giving more weight to transactions with large volume.   │
│                                                        │
│ 💡 Everyday Analogy:                                   │
│ Like the wholesale market price of onions. If prices   │
│ are far above, retail buyers are paying a premium.     │
│                                                        │
│ ⚠️ Risk Caution:                                        │
│ Buying far above VWAP increases your risk of buying    │
│ at the top.                                            │
└────────────────────────────────────────────────────────┘
```

---

## 5. Guided First-Scan Interactive Tutorial

An interactive 4-step spotlight overlay for first-time visitors:
1. **Step 1: The Universe (Where we look)**:
   - Highlights the Index selector: *"We start by scanning the Nifty 500 — the top 500 largest companies in India. This avoids illiquid penny stocks."*
2. **Step 2: The Setup (What we look for)**:
   - Points to the 1-Click "Volume Surge" card: *"We look for unusual activity. When volume spikes 2x above normal, it often indicates institutional buying."*
3. **Step 3: The Result (What it found)**:
   - Focuses on the top matching stock in the screener table: *"Clicking this stock opens its chart instantly."*
4. **Step 4: The Risk (How to stay safe)**:
   - Highlights the Stop Loss entry box and survivorship bias banner: *"Before thinking about profit, always decide where you will exit if you are wrong."*

---

## 6. Implementation Steps
1. Create `config/glossary.json` compiling the standardized three-part dictionary.
2. Implement `static/js/glossary_tooltip.js`:
   - Queries `config/glossary.json`.
   - Listens to `mouseenter` / `mouseleave` / `touchstart` events on `[data-glossary]`.
   - Positions glassmorphic popover with viewport boundary detection.
3. Implement `static/js/guided_tutorial.js` managing step progression and local storage completion flags.
4. Style popover cards in `static/css/education.css`.

---

## 7. Verification & Acceptance Criteria
- `config/glossary.json` parses cleanly and contains all mandatory terms (VWAP, RSI, MACD, Bollinger Bands, ATR, 52W High, Volume Z-Score, Slippage, STT, Bhavcopy, R-Multiple, Max Pain).
- 100% of glossary entries possess `definition`, `analogy`, and `risk_warning` fields without empty strings.
- In Simple Mode, hovering any indicator label displays the popover card within $< 100\text{ ms}$.
- Completing the guided tutorial marks `quant_tutorial_completed: true` in `localStorage`, preventing annoying recurring popups.
- Mobile/Touch verification: Tapping a glossary badge on mobile displays the popover; tapping outside dismisses it cleanly.
