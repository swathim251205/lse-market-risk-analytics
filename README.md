# LSE Market Risk Mini-Project (PostgreSQL → Python)

A small front-office risk analytics project using London Stock Exchange historical prices.  
Data is stored in PostgreSQL and visualized in Python (Matplotlib). The project computes **rolling historical VaR (95%, 250-day window)** and highlights **VaR breaches**.

## What this shows (interview focus)
- SQL + Python integration (pulling risk series from a DB view)
- Return series understanding (distribution + volatility)
- VaR backtesting concept (breach rate vs expected ~5%)

## Setup

### 1) Create and activate venv (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
