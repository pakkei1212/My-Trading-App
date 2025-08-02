import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import requests
import pandas as pd
from datetime import date
from utils import generate_monthly_summary
import matplotlib.pyplot as plt

API_URL = "http://127.0.0.1:8002"

st.set_page_config(page_title="Trading Journal", layout="wide")
st.title("📘 Trading Journal Dashboard")

# ========== Sidebar Filter Section ==========
st.sidebar.header("🔍 Filter Trades")

filter_stock = st.sidebar.text_input("Stock Code")
filter_market = st.sidebar.selectbox("Market", ["", "HK", "US"])
filter_start_date = st.sidebar.date_input("Start Entry Date", value=None)
filter_end_date = st.sidebar.date_input("End Entry Date", value=None)
show_closed = st.sidebar.checkbox("Show Closed Positions", value=False)

# ===== Tabs Section =====
tab1, tab2, tab3 = st.tabs(["📄 All Trades", "📈 Monthly Performance Summary", "CSV Import"])

# ===== Tab 1: All Trades =====
with tab1:
    st.subheader("📄 All Trades")
    response = requests.get(f"{API_URL}/entries")
    if response.status_code == 200:
        trades = response.json()

        # Apply filters
        if not show_closed:
            trades = [t for t in trades if t["is_open"] is True]
        if filter_stock:
            trades = [t for t in trades if filter_stock.lower() in t["stock"].lower()]
        if filter_market:
            trades = [t for t in trades if t["market"] == filter_market]
        if filter_start_date:
            trades = [t for t in trades if t["entry_date"] >= str(filter_start_date)]
        if filter_end_date:
            trades = [t for t in trades if t["entry_date"] <= str(filter_end_date)]

        for t in trades:
            currency = "HKD" if t["market"] == "HK" else "USD"
            header = f"{t['entry_date']} - {t['stock']} ({t['position']}) {t['remaining_qty']}/{t['qty']} - {'Open' if t['is_open'] else 'Closed'}"
            with st.expander(header, expanded=False):
                col1, col2, col3 = st.columns(3)

                if t["exits"]:
                    gain_pct = f"{100 * (t.get('actual_gain_loss_pct') or 0):.2f}%"
                    pnl = f"{t.get('actual_gain_loss') or 0.0:,.2f} {currency}"
                    holding_days = t.get('holding_days', 'N.A.')
                else:
                    gain_pct = pnl = holding_days = "N.A."

                with col1:
                    st.markdown(f"**Market**: {t['market']}")
                    st.markdown(f"**Entry**: {t['entry_price']} {currency}")
                    st.markdown(f"**Stop**: {t['stop_loss_price']} {currency}")
                    st.markdown(f"**Target**: {t['target_price']} {currency}")

                with col2:
                    st.markdown(f"**Total Cost**: {t.get('total_cost', 0.0):,.2f} {currency}")
                    st.markdown(f"**Expected RR**: {t.get('rr_ratio', '-')}")
                    st.markdown(f"**Gain %**: {gain_pct}")
                    st.markdown(f"**PnL**: {pnl}")

                with col3:
                    st.markdown(f"**Holding Days**: {holding_days}")
                    st.markdown(f"**Qty Remaining**: {t['remaining_qty']} / {t['qty']}")

                # Inline close form
                if t["is_open"]:
                    with st.form(f"close_form_{t['id']}"):
                        st.markdown("**📉 Close This Position**")
                        exit_qty = st.number_input("Exit Qty", min_value=1, value=int(t['remaining_qty']),
                                                   max_value=t["remaining_qty"], key=f"qty_{t['id']}")
                        exit_price = st.number_input("Exit Price", min_value=0.0, value=float(t['entry_price']),
                                                     format="%.2f", step=1.0,
                                                     key=f"price_{t['id']}")
                        exit_date = st.date_input("Exit Date", value=date.today(),
                                                  key=f"date_{t['id']}")
                        exit_submit = st.form_submit_button("Submit Exit")
                        if exit_submit:
                            if exit_date < date.fromisoformat(t["entry_date"]):
                                st.error("Exit date cannot be before entry date.")
                            else:
                                exit_data = {
                                    "entry_id": t["id"],
                                    "exit_qty": exit_qty,
                                    "exit_price": exit_price,
                                    "exit_date": str(exit_date)
                                }
                                r = requests.post(f"{API_URL}/exits", json=exit_data)
                                if r.status_code == 200:
                                    st.success("Exit recorded!")
                                    st.rerun()
                                else:
                                    st.error(r.json().get("detail", "Failed to add exit"))

                if t["exits"]:
                    st.markdown("### 📜 Exit History")
                    for e in t["exits"]:
                        st.markdown(f"- {e['exit_qty']} @ {e['exit_price']} on {e['exit_date']}")

    # ========== Add Trade Entry ==========
    st.subheader("➕ Add Trade Entry")
    with st.form("entry_form"):
        col1, col2 = st.columns(2)
        stock = col1.text_input("Stock Code", value="9988")
        market = col2.selectbox("Market", ["HK", "US"])
        position = col1.selectbox("Position", ["Long", "Short"])
        entry_date = col2.date_input("Entry Date", value=date.today())
        entry_price = col1.number_input("Entry Price", min_value=0.01, format="%.2f")
        qty = col2.number_input("Quantity", min_value=1)
        stop_loss_input = col1.text_input("Stop Loss Price (Optional)", value="")
        target_price_input = col2.text_input("Target Price (Optional)", value="")

        submitted = st.form_submit_button("Add Entry")
        if submitted:
            valid = True
            stop_loss = None
            target_price = None

            # Parse and validate Stop Loss
            if stop_loss_input.strip() != "":
                try:
                    stop_loss = float(stop_loss_input)
                    if position == "Long" and stop_loss >= entry_price:
                        st.error("For Long, Stop Loss must be less than Entry Price.")
                        valid = False
                    elif position == "Short" and stop_loss <= entry_price:
                        st.error("For Short, Stop Loss must be greater than Entry Price.")
                        valid = False
                except ValueError:
                    st.error("Stop Loss must be a valid number.")
                    valid = False

            # Parse and validate Target Price
            if target_price_input.strip() != "":
                try:
                    target_price = float(target_price_input)
                    if position == "Long" and target_price <= entry_price:
                        st.error("For Long, Target Price must be greater than Entry Price.")
                        valid = False
                    elif position == "Short" and target_price >= entry_price:
                        st.error("For Short, Target Price must be less than Entry Price.")
                        valid = False
                except ValueError:
                    st.error("Target Price must be a valid number.")
                    valid = False

            # Validate full range if both provided
            if valid and stop_loss is not None and target_price is not None:
                if position == "Long" and not (stop_loss < entry_price < target_price):
                    st.error("For Long: Stop Loss < Entry Price < Target Price.")
                    valid = False
                elif position == "Short" and not (stop_loss > entry_price > target_price):
                    st.error("For Short: Stop Loss > Entry Price > Target Price.")
                    valid = False

            if valid:
                new_trade = {
                    "stock": stock,
                    "market": market,
                    "position": position,
                    "entry_date": str(entry_date),
                    "entry_price": entry_price,
                    "qty": qty,
                    "stop_loss_price": stop_loss,
                    "target_price": target_price
                }
                resp = requests.post(f"{API_URL}/entries", json=new_trade)
                if resp.status_code == 200:
                    st.success("Trade entry added!")
                    st.rerun()
                else:
                    st.error(f"Failed to add trade: {resp.text}")

# ===== Tab 2: Monthly Performance =====
with tab2:
    st.subheader("Monthly Performance Summary")

    response_closed = requests.get(f"{API_URL}/entries/closed")
    if response_closed.status_code == 200:
        closed_trades = response_closed.json()
        monthly_df = generate_monthly_summary(closed_trades)

        # Set Period index and get available years
        monthly_df.index = pd.PeriodIndex(monthly_df.index, freq="M")
        available_years = sorted(list(set([m.year for m in monthly_df.index])))

        selected_year = st.selectbox("Select Year", available_years)

        filtered_df = monthly_df[monthly_df.index.year == selected_year]

        if not filtered_df.empty:
            # Shorten month names
            month_mapping = {
                1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
            }

            # After filtering
            filtered_df.index = filtered_df.index.to_timestamp()  # Convert Period to Timestamp
            filtered_df["Month"] = filtered_df.index.month.map(month_mapping)

            # Pivot so month names are columns
            pivot_df = filtered_df.set_index("Month")
            # pivot_df = pivot_df.sort_index()  # Jan to Dec order
            pivot_df = pivot_df.transpose()  # Metrics as rows

            formatted_data = {}

            for metric_name in pivot_df.index:
                values = pivot_df.loc[metric_name]
                if "HKD" in metric_name:
                    formatted_data[metric_name] = [f"HKD {v:,.0f}" if pd.notnull(v) else "-" for v
                                                   in values]
                elif "%" in metric_name:
                    formatted_data[metric_name] = [f"{v:.2%}" if pd.notnull(v) else "-" for v in
                                                   values]
                elif "Trades" in metric_name:
                    formatted_data[metric_name] = [f"{int(round(v))}" if pd.notnull(v) else "-" for
                                                   v in values]
                elif "RR Ratio" in metric_name or "Avg Holding" in metric_name:
                    formatted_data[metric_name] = [f"{v:.2f}" if pd.notnull(v) else "-" for v in
                                                   values]
                else:
                    formatted_data[metric_name] = [f"{v:.2f}" if pd.notnull(v) else "-" for v in
                                                   values]

            formatted_df = pd.DataFrame(formatted_data, index=pivot_df.columns).transpose()

            # Styling
            styled_table = (
                formatted_df.style
                .set_properties(**{
                    'text-align': 'center',
                    'font-size': '14px'
                })
                .set_table_styles([
                    {'selector': 'th', 'props': [('font-size', '15px'), ('text-align', 'center')]},
                    {'selector': 'td', 'props': [('text-align', 'center')]},
                ])
                .highlight_null(color='lightgray')  # better visual for missing months
                .applymap(lambda v: 'font-weight: bold' if isinstance(v, str) and (
                            "HKD" in v or "%" in v) else '')
                .background_gradient(cmap="Greys", axis=None)  # gentle background
            )

            st.dataframe(styled_table, use_container_width=True)

            st.subheader("📈 Win Rate Over Months")

            # Extract raw numeric data (not formatted text!)
            if "Win Rate %" in pivot_df.index and "Actual RR Ratio" in pivot_df.index:
                # Win Rate %
                win_rate = pivot_df.loc["Win Rate %"]
                # RR Ratio
                rr_ratio = pivot_df.loc["Actual RR Ratio"]

                months = win_rate.index.tolist()  # ['Jan', 'Feb', ...]

                # --- Plot Win Rate ---
                fig1, ax1 = plt.subplots(figsize=(10, 4))
                ax1.plot(months, win_rate.values, marker='o', linestyle='-', color='royalblue',
                         label="Win Rate %")
                ax1.set_title(f"Win Rate % Trend - {selected_year}", fontsize=16)
                ax1.set_ylabel("Win Rate (%)", fontsize=12)
                ax1.set_ylim(0, 1)  # 0% to 100%
                ax1.grid(True, linestyle="--", alpha=0.5)
                ax1.legend()
                st.pyplot(fig1)

                # --- Plot Actual RR Ratio ---
                fig2, ax2 = plt.subplots(figsize=(10, 4))
                ax2.plot(months, rr_ratio.values, marker='s', linestyle='-', color='darkorange',
                         label="Actual RR Ratio")
                ax2.set_title(f"Actual RR Ratio Trend - {selected_year}", fontsize=16)
                ax2.set_ylabel("RR Ratio", fontsize=12)
                ax2.grid(True, linestyle="--", alpha=0.5)
                ax2.legend()
                st.pyplot(fig2)
            else:
                st.info("Insufficient data to plot Win Rate and RR Ratio charts.")

        else:
            st.info("No data for selected year.")
    else:
        st.error("Failed to fetch closed trades for summary.")

# ===== Tab 3: CSV Import =====
with tab3:
    st.subheader("📥 Import Trades from CSV")
    uploaded_file = st.file_uploader("Upload a CSV file with trade entries and exits", type="csv")
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Preview:", df.head())

        if st.button("Import to Database"):
            success, failed = 0, 0
            for i, row in df.iterrows():
                try:
                    # Parse entry data
                    entry = {
                        "stock": row["Stock"],
                        "market": row["Market"],
                        "position": row["Position"],
                        "entry_date": pd.to_datetime(row["Entry Date"], dayfirst=True).date().isoformat(),
                        "entry_price": float(row["Entry Price"]),
                        "qty": int(row["Qty"]),
                        "stop_loss_price": float(row["Stop Loss Price"]) if pd.notna(row["Stop Loss Price"]) else None,
                        "target_price": float(row["Target Price"]) if pd.notna(row["Target Price"]) else None
                    }
                    r = requests.post(f"{API_URL}/entries", json=entry)
                    if r.status_code == 200:
                        success += 1
                        entry_id = r.json().get("id")

                        # Handle exit if present
                        if pd.notna(row.get("Exit Price")) and pd.notna(row.get("Exit Date")):
                            exit_data = {
                                "entry_id": entry_id,
                                "exit_price": float(row["Exit Price"]),
                                "exit_qty": int(row["Qty"]),
                                "exit_date": pd.to_datetime(row["Exit Date"], dayfirst=True).date(

                                ).isoformat()
                            }
                            rex = requests.post(f"{API_URL}/exits", json=exit_data)
                            if rex.status_code != 200:
                                st.warning(f"❌ Exit failed for row {i+2}: {rex.json().get('detail', 'Unknown error')}")
                    else:
                        failed += 1
                        st.warning(f"❌ Row {i+2} failed: {r.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    failed += 1
                    st.warning(f"❌ Row {i+2} failed: {e}")

            st.success(f"Imported {success} entries, Failed: {failed}")