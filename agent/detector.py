import pandas as pd
import numpy as np
from scipy import stats
from sqlalchemy import text
from db import engine
from dotenv import load_dotenv

load_dotenv()

def get_sucursal_data(days: int = 30) -> pd.DataFrame:
    # Pulls the last N days of data from the Gold Layer for all sucursals
    query = text(f"""
        SELECT 
            sucursal_id,
            sucursal_name,
            report_date,
            total_sales,
            total_clients,
            clients_churned
        FROM gold_sucursal_daily
        WHERE report_date >= CURRENT_DATE - INTERVAL '{days} days'
        ORDER BY sucursal_id, report_date
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def detect_red_zones(df: pd.DataFrame) -> list:
    # Runs 3 detection methods on today's data for each sucursal
    # Returns a list of flagged sucursals with their detection reasons
    today = df["report_date"].max()
    today_data = df[df["report_date"] == today].copy()
    historical = df[df["report_date"] < today].copy()

    flagged = []

    for _, row in today_data.iterrows():
        sid = row["sucursal_id"]
        hist = historical[historical["sucursal_id"] == sid]

        if hist.empty:
            continue

        reasons = []
        metrics = {
            "sucursal_id": sid,
            "sucursal_name": row["sucursal_name"],
            "report_date": str(today),
            "total_sales": row["total_sales"],
            "total_clients": row["total_clients"],
            "clients_churned": row["clients_churned"],
        }

        # --- Method 1: Fixed Threshold ---
        # Flags if sales drop below an absolute floor
        SALES_THRESHOLD = 15000
        CHURN_THRESHOLD = 15
        if row["total_sales"] < SALES_THRESHOLD:
            reasons.append(f"Fixed threshold: sales ${row['total_sales']:,.0f} below ${SALES_THRESHOLD:,}")
        if row["clients_churned"] > CHURN_THRESHOLD:
            reasons.append(f"Fixed threshold: churn {row['clients_churned']} above {CHURN_THRESHOLD}")

        # --- Method 2: % Drop vs 7-day Rolling Average ---
        # Flags if today is more than 20% below the 7-day average
        last_7 = hist.tail(7)
        avg_sales_7d = last_7["total_sales"].mean()
        avg_churn_7d = last_7["clients_churned"].mean()

        sales_drop_pct = (avg_sales_7d - row["total_sales"]) / avg_sales_7d * 100
        churn_spike_pct = (row["clients_churned"] - avg_churn_7d) / avg_churn_7d * 100

        metrics["avg_sales_7d"] = round(avg_sales_7d, 2)
        metrics["avg_churn_7d"] = round(avg_churn_7d, 2)
        metrics["sales_drop_pct"] = round(sales_drop_pct, 2)
        metrics["churn_spike_pct"] = round(churn_spike_pct, 2)

        if sales_drop_pct > 20:
            reasons.append(f"Rolling avg: sales dropped {sales_drop_pct:.1f}% vs 7d avg ${avg_sales_7d:,.0f}")
        if churn_spike_pct > 50:
            reasons.append(f"Rolling avg: churn spiked {churn_spike_pct:.1f}% vs 7d avg {avg_churn_7d:.1f}")

        # --- Method 3: Z-Score ---
        # Flags if today is statistically abnormal vs full history
        sales_history = hist["total_sales"].values
        churn_history = hist["clients_churned"].values

        if len(sales_history) >= 5:
            sales_zscore = (row["total_sales"] - np.mean(sales_history)) / np.std(sales_history)
            churn_zscore = (row["clients_churned"] - np.mean(churn_history)) / np.std(churn_history)

            metrics["sales_zscore"] = round(sales_zscore, 2)
            metrics["churn_zscore"] = round(churn_zscore, 2)

            if sales_zscore < -2.0:
                reasons.append(f"Z-score: sales z={sales_zscore:.2f} (statistically abnormal low)")
            if churn_zscore > 2.0:
                reasons.append(f"Z-score: churn z={churn_zscore:.2f} (statistically abnormal high)")

        # Only flag if at least one method triggered
        if reasons:
            metrics["reasons"] = reasons
            flagged.append(metrics)

    return flagged


if __name__ == "__main__":
    df = get_sucursal_data()
    flagged = detect_red_zones(df)
    print(f"Flagged sucursals: {len(flagged)}")
    for s in flagged:
        print(f"\n{s['sucursal_name']} — {len(s['reasons'])} reasons:")
        for r in s["reasons"]:
            print(f"  • {r}")