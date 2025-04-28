from decimal import Decimal

import pandas as pd
from calendar import month_name
import models, schemas

def compute_derived_fields(entry: models.TradeEntry) -> schemas.TradeEntryResponse:
    data = schemas.TradeEntryResponse.model_validate(entry, from_attributes=True).model_dump()

    try:
        entry_price = entry.entry_price
        stop = entry.stop_loss_price
        target = entry.target_price
        qty = entry.qty
        fx = Decimal('7.78') if entry.market.upper() == 'US' else Decimal('1')

        # Expected P&L %
        if entry_price and stop:
            data["expected_loss_pct"] = float(abs((entry_price - stop) / entry_price))
        if entry_price and target:
            data["expected_gain_pct"] = float(abs((target - entry_price) / entry_price))

        if data.get("expected_loss_pct") and data.get("expected_gain_pct"):
            loss = Decimal(str(data["expected_loss_pct"]))
            gain = Decimal(str(data["expected_gain_pct"]))
            if loss != 0:
                data["rr_ratio"] = float(gain / loss)

        # Total realized gain/loss
        total_realized = Decimal(0)
        for exit in entry.exits:
            if entry.position == "Long":
                delta = exit.exit_price - entry_price
            else:
                delta = entry_price - exit.exit_price

            total_realized += delta * exit.exit_qty * fx

        data["actual_gain_loss"] = float(total_realized)
        data["actual_gain_loss_pct"] = float(
            total_realized / (qty * entry_price * fx)) if qty > 0 else 0

        # Holding days: latest exit date - entry date
        if entry.exits:
            last_exit_date = max(e.exit_date for e in entry.exits)
            data["holding_days"] = (last_exit_date - entry.entry_date).days
        else:
            data["holding_days"] = 0

        data["total_cost"] = float(entry_price * qty)

    except Exception as e:
        print(f"Error computing derived fields for entry {entry.id}: {e}")

    print(data)
    return schemas.TradeEntryResponse(**data)

def generate_monthly_summary(trades):
    flat_records = []

    for trade in trades:
        for exit in trade["exits"]:
            flat_records.append({
                "stock": trade["stock"],
                "market": trade["market"],
                "position": trade["position"],
                "entry_date": trade["entry_date"],
                "exit_date": exit["exit_date"],
                "entry_price": float(trade["entry_price"]),
                "exit_price": float(exit["exit_price"]),
                "exit_qty": exit["exit_qty"],
                "actual_gain_loss_pct": trade.get("actual_gain_loss_pct"),
                "actual_gain_loss": trade.get("actual_gain_loss"),
                "holding_days": trade.get("holding_days"),
                "total_cost": trade.get("total_cost"),
            })

    df = pd.DataFrame(flat_records)
    df["exit_date"] = pd.to_datetime(df["exit_date"])
    df = df.dropna(subset=["exit_date"])
    df["month"] = df["exit_date"].dt.to_period("M")

    monthly_data = []

    for month, group in df.groupby("month"):
        wins = group[group["actual_gain_loss"] > 0]
        losses = group[group["actual_gain_loss"] < 0]

        avg_loss = losses["actual_gain_loss"].mean()
        avg_gain = wins["actual_gain_loss"].mean()
        avg_loss_pct = losses["actual_gain_loss_pct"].mean()
        avg_gain_pct = wins["actual_gain_loss_pct"].mean()
        freq_wins = len(wins)
        freq_losses = len(losses)

        win_rate = freq_wins / (freq_wins + freq_losses) if (freq_wins + freq_losses) > 0 else None
        rr_ratio = abs((avg_gain * freq_wins) / (avg_loss * freq_losses)) if (avg_loss and freq_losses) else None

        largest_gain = group["actual_gain_loss"].max()
        largest_loss = group["actual_gain_loss"].min()

        avg_days_gains = wins["holding_days"].mean()
        avg_days_losses = losses["holding_days"].mean()

        monthly_data.append({
            "Month": month.to_timestamp().strftime("%b %Y"),
            "Average Loss (HKD)": avg_loss,
            "Average Gain (HKD)": avg_gain,
            "Average Loss %": avg_loss_pct,
            "Average Gain %": avg_gain_pct,
            "Winning Trades": freq_wins,
            "Losing Trades": freq_losses,
            "Win Rate %": win_rate,
            "Actual RR Ratio": rr_ratio,
            "Largest Gain (HKD)": largest_gain,
            "Largest Loss (HKD)": largest_loss,
            "Avg Holding Days (Win)": avg_days_gains,
            "Avg Holding Days (Loss)": avg_days_losses
        })

    summary_df = pd.DataFrame(monthly_data)
    summary_df.set_index("Month", inplace=True)
    return summary_df
