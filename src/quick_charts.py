import os
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

VIEW_NAME = "fo.v_risk_series"
OUTDIR = "charts"
WINDOW_VAR = 250          # 250 trading days ~ 1 year
ALPHA_VAR = 0.05          # 5% left tail -> 95% VaR

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def show_non_blocking(pause: float = 0.3) -> None:
    plt.show(block=False)
    plt.pause(pause)

def make_engine():
    load_dotenv()

    pguser = os.getenv("PGUSER")
    pgpassword = os.getenv("PGPASSWORD")
    pgdatabase = os.getenv("PGDATABASE")
    pghost = os.getenv("PGHOST", "localhost")
    pgport = int(os.getenv("PGPORT", "5432"))

    missing = [k for k, v in {
        "PGUSER": pguser,
        "PGPASSWORD": pgpassword,
        "PGDATABASE": pgdatabase
    }.items() if not v]

    if missing:
        raise ValueError(f"Missing env vars in .env: {missing}")

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=pguser,
        password=pgpassword,   # safe with @ in password
        host=pghost,
        port=pgport,
        database=pgdatabase,
    )
    return create_engine(url)

def load_data(engine) -> pd.DataFrame:
    sql = f"""
    SELECT
        trade_date,
        close_price,
        daily_return,
        vol_20d
    FROM {VIEW_NAME}
    ORDER BY trade_date;
    """
    df = pd.read_sql(sql, engine)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df

def plot_close(df: pd.DataFrame) -> None:
    d = df.dropna(subset=["trade_date", "close_price"])
    plt.figure()
    plt.plot(d["trade_date"], d["close_price"])
    plt.title("Close Price")
    plt.xlabel("Trade Date")
    plt.ylabel("Close Price")
    plt.tight_layout()
    plt.savefig(f"{OUTDIR}/01_close_price.png", dpi=150)
    show_non_blocking()

def plot_returns_hist(df: pd.DataFrame) -> None:
    r = df["daily_return"].dropna()
    plt.figure()
    plt.hist(r, bins=60)
    plt.title("Daily Returns Histogram")
    plt.xlabel("Daily Return")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(f"{OUTDIR}/02_returns_hist.png", dpi=150)
    show_non_blocking()

def plot_vol(df: pd.DataFrame) -> None:
    d = df.dropna(subset=["trade_date", "vol_20d"])
    if d.empty:
        print("vol_20d is empty — skipping vol chart.")
        return
    plt.figure()
    plt.plot(d["trade_date"], d["vol_20d"])
    plt.title("Rolling Volatility (20d)")
    plt.xlabel("Trade Date")
    plt.ylabel("Volatility")
    plt.tight_layout()
    plt.savefig(f"{OUTDIR}/03_rolling_vol_20d.png", dpi=150)
    show_non_blocking()

def plot_var_breaches(df: pd.DataFrame) -> dict:
    d = df[["trade_date", "daily_return"]].dropna().copy()
    d = d.sort_values("trade_date")

    # Historical VaR via rolling quantile
    d["var_95_250d"] = d["daily_return"].rolling(WINDOW_VAR).quantile(ALPHA_VAR)
    d = d.dropna(subset=["var_95_250d"])

    d["is_breach"] = d["daily_return"] < d["var_95_250d"]

    days_tested = len(d)
    breaches = int(d["is_breach"].sum())
    breach_pct = 100.0 * breaches / days_tested if days_tested else 0.0

    # Expected breaches ≈ 5% for well-calibrated VaR
    expected_pct = 100.0 * ALPHA_VAR

    plt.figure()
    plt.plot(d["trade_date"], d["var_95_250d"], label=f"VaR {int((1-ALPHA_VAR)*100)}% ({WINDOW_VAR}d)")
    plt.plot(d["trade_date"], d["daily_return"], label="Daily Return", linewidth=0.8)
    plt.scatter(
        d.loc[d["is_breach"], "trade_date"],
        d.loc[d["is_breach"], "daily_return"],
        marker="x",
        label="Breaches"
    )
    plt.title(f"VaR vs Returns | Breach%={breach_pct:.2f}% (Expected~{expected_pct:.0f}%)")
    plt.xlabel("Trade Date")
    plt.ylabel("Return")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTDIR}/04_var_breaches_250d.png", dpi=150)
    show_non_blocking()

    stats = {
        "days_tested": days_tested,
        "breaches": breaches,
        "breach_pct": round(breach_pct, 2),
        "expected_breach_pct": expected_pct,
    }
    return stats

def main():
    ensure_dir(OUTDIR)

    engine = make_engine()
    df = load_data(engine)

    print("Rows:", len(df))
    print("Date range:", df["trade_date"].min().date(), "→", df["trade_date"].max().date())

    plot_close(df)
    plot_returns_hist(df)
    plot_vol(df)

    stats = plot_var_breaches(df)
    print("\nBacktest summary (rolling historical VaR):")
    print(stats)

    input("\nCharts saved to ./charts. Press Enter to exit...")

if __name__ == "__main__":
    main()
