from pathlib import Path
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Fixed Income Monitor",
    page_icon="📊",
    layout="wide"
)
ROOT = Path(__file__).resolve().parent

@st.cache_data
def load_fred_data():
    path = ROOT / "data" / "fred_history.csv"
    df = pd.read_csv(path, parse_dates=["DATE"])
    df = df.set_index("DATE").sort_index()
    return df

fred = load_fred_data()


@st.cache_data(ttl=3600)
def load_etf_data():
    tickers = [
        "AGG", "GOVT", "LQD",
        "MUB", "TIP", "IAGG"
    ]

    data = yf.download(
        tickers,
        period="3y",
        auto_adjust=True,
        progress=False,
        threads=False
    )

    prices = data["Close"].copy()
    prices = prices.dropna(how="all").sort_index()

    if prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)

    return prices

@st.cache_data
def load_etf_characteristics():
    path = ROOT / "data" / "official_etf_characteristics.csv"
    df = pd.read_csv(path)
    return df

@st.cache_data
def load_portfolio_prices():
    path = ROOT / "data" / "adjusted_prices_used.csv"

    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index.name = "Date"

    required = ["AGG", "SHY", "IGSB"]

    missing = [ticker for ticker in required if ticker not in df.columns]
    if missing:
        raise ValueError(f"Missing ETF columns: {missing}")

    return df[required].sort_index().dropna()


def calculate_portfolio_performance(prices, weights):
    # Calculate daily ETF returns
    returns = prices.pct_change().dropna()

    target_weights = pd.Series(weights).reindex(
        returns.columns, fill_value=0.0
    )

    # Start with the selected allocation
    current_weights = target_weights.copy()
    portfolio_returns = []

    previous_month = None

    for date, daily_returns in returns.iterrows():

        current_month = date.to_period("M")

        # Rebalance at the start of each new month
        if previous_month is not None:
            if current_month != previous_month:
                current_weights = target_weights.copy()

        # Calculate daily portfolio return
        portfolio_return = (
            current_weights * daily_returns
        ).sum()

        portfolio_returns.append(portfolio_return)

        # Update weights after daily price movements
        current_weights = current_weights * (1 + daily_returns)

        current_weights = (
            current_weights / current_weights.sum()
        )

        previous_month = current_month

    return pd.Series(
        portfolio_returns,
        index=returns.index,
        name="Portfolio"
    )


st.title("Fixed Income Benchmark & Portfolio Monitor")

st.caption(
    "Market data | Benchmark monitoring | Portfolio analytics"
)

st.divider()

tab1, tab2, tab3 = st.tabs([
    "Market Overview",
    "Benchmark Monitor",
    "Portfolio Risk"
])


with tab1:
    st.header("US Fixed Income Market Overview")

    # Latest available values for each indicator
    col1, col2, col3 = st.columns(3)

    indicators = [
        ("10Y Treasury", "DGS10", "%"),
        ("10Y Real Yield", "DFII10", "%"),
        ("IG Credit OAS", "BAMLC0A0CM", " bp"),
    ]

    for col, (label, series, unit) in zip(
        [col1, col2, col3], indicators
    ):
        values = fred[series].dropna()
        latest = values.iloc[-1]

        if unit == " bp":
            latest *= 100

        col.metric(
            label=label,
            value=f"{latest:.2f}{unit}"
        )
        col.caption(
            f"As of {values.index[-1]:%d %b %Y}"
        )

    st.divider()

    st.subheader("US Treasury Yield Curve")

    period = st.selectbox(
        "Compare current curve with:",
        ["3 months ago", "12 months ago"]
    )

    maturities = {
        "2Y": "DGS2",
        "5Y": "DGS5",
        "10Y": "DGS10",
        "30Y": "DGS30"
    }

    latest_date = fred[list(maturities.values())].dropna().index[-1]

    months_back = 3 if period == "3 months ago" else 12
    target_date = latest_date - pd.DateOffset(months=months_back)

    historical = fred.loc[
        fred.index <= target_date,
        list(maturities.values())
    ].dropna()

    if historical.empty:
        st.warning("No historical data for this period.")
    else:
        historical_date = historical.index[-1]

        current_yields = fred.loc[
            latest_date, list(maturities.values())
        ]

        historical_yields = historical.iloc[-1]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=list(maturities.keys()),
            y=current_yields.values,
            mode="lines+markers",
            name=f"Current ({latest_date:%d %b %Y})"
        ))

        fig.add_trace(go.Scatter(
            x=list(maturities.keys()),
            y=historical_yields.values,
            mode="lines+markers",
            name=f"Previous ({historical_date:%d %b %Y})"
        ))

        fig.update_layout(
            xaxis_title="Maturity",
            yaxis_title="Yield (%)",
            hovermode="x unified",
            height=440,
            margin=dict(l=30, r=30, t=30, b=30)
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Source: FRED | Nominal Treasury yields"
        )
        
    st.divider()

    st.subheader("Inflation & Credit Monitor")

    lookback = st.selectbox(
        "Historical period",
        ["3 Months", "6 Months", "1 Year", "All Available"],
        index=2
    )

    months = {
        "3 Months": 3,
        "6 Months": 6,
        "1 Year": 12
    }

    data = fred.copy()

    if lookback != "All Available":
        cutoff = data.index.max() - pd.DateOffset(
            months=months[lookback]
        )
        data = data.loc[data.index >= cutoff]

    col_inflation, col_credit = st.columns(2)

    # Inflation chart
    with col_inflation:
        st.markdown("**10Y Treasury Yield Components - Real Yield & Breakeven Inflation**")

        fig_inflation = go.Figure()

        for series, label in [
            ("DFII10", "10Y Real Yield"),
            ("T10YIE", "10Y Breakeven")
        ]:
            fig_inflation.add_trace(go.Scatter(
                x=data.index,
                y=data[series],
                mode="lines",
                name=label,
                connectgaps=True
            ))

        fig_inflation.update_layout(
            yaxis_title="Yield (%)",
            height=380,
            hovermode="x unified"
        )

        st.plotly_chart(
            fig_inflation,
            use_container_width=True
        )

    # Credit spreads chart
    
    with col_credit:
        st.markdown("**US Corporate Credit Spreads**")

        spread_view = st.session_state.get(
            "spread_view",
            "Absolute OAS (bp)"
        )  

        fig_credit = go.Figure()

        for series, label in [
            ("BAMLC0A0CM", "Investment Grade"),
            ("BAMLH0A0HYM2", "High Yield")
        ]:
            spread = data[series].dropna() * 100

            if spread_view == "Change from start (bp)":
                spread = spread - spread.iloc[0]

            fig_credit.add_trace(go.Scatter(
                x=spread.index,
                y=spread,
                mode="lines",
                name=label,
                connectgaps=True
            ))

        fig_credit.update_layout(
            yaxis_title=(
                "Change in OAS (bp)"
                if spread_view == "Change from start (bp)"
                else "OAS (bp)"
            ),
            height=380,
            hovermode="x unified"
        )

        st.plotly_chart(
            fig_credit,
            use_container_width=True
        )

        st.radio(
            "Credit spread view",
            ["Absolute OAS (bp)", "Change from start (bp)"],
            horizontal=True,
            label_visibility="collapsed",
            key="spread_view"
        )

    st.caption(
        "Source: FRED | Treasury inflation-linked yields "
        "and ICE BofA corporate option-adjusted spreads."
    )


with tab2:
    st.header("Fixed Income Benchmark Monitor")

    st.caption(
        "ETF proxies for major fixed income market segments"
    )

    etf_names = {
        "AGG": "US Aggregate",
        "GOVT": "US Treasury",
        "LQD": "US Corporate IG",
        "MUB": "US Municipal",
        "TIP": "US TIPS",
        "IAGG": "Global Aggregate ex-US (USD Hedged)"
    }

    try:
        prices = load_etf_data()
    except Exception as error:
        st.error(f"Unable to download ETF data: {error}")
        st.stop()

    if prices.empty:
        st.warning("No ETF prices available.")
        st.stop()

    st.subheader("ETF Performance Comparison")

    # Calculate total returns over different periods
    def calculate_return(series, target_date):
        series = series.dropna()

        if series.empty:
            return float("nan")

        history = series.loc[series.index <= target_date]

        if history.empty:
            return float("nan")

        start_price = history.iloc[-1]
        end_price = series.iloc[-1]

        return (end_price / start_price - 1) * 100

    performance = []

    for ticker, name in etf_names.items():

        if ticker not in prices.columns:
            continue

        series = prices[ticker].dropna()

        if series.empty:
            continue

        latest_date = series.index[-1]

        returns = {
            "Segment": name,
            "ETF": ticker,
            "1M": calculate_return(
                series, latest_date - pd.DateOffset(months=1)
            ),
            "3M": calculate_return(
                series, latest_date - pd.DateOffset(months=3)
            ),
            "YTD": calculate_return(
                series, pd.Timestamp(latest_date.year - 1, 12, 31)
            ),
            "1Y": calculate_return(
                series, latest_date - pd.DateOffset(years=1)
            )
        }

        performance.append(returns)

    performance_df = pd.DataFrame(performance)

    if performance_df.empty:
        st.warning("No performance data available.")
        st.stop()

    st.dataframe(
        performance_df.style.format({
            "1M": "{:+.2f}%",
            "3M": "{:+.2f}%",
            "YTD": "{:+.2f}%",
            "1Y": "{:+.2f}%"
        }, na_rep="N/A"),
        hide_index=True,
        use_container_width=True
    )

    st.divider()

    st.subheader("Relative Performance")

    selected_etfs = st.multiselect(
        "Select ETFs to compare",
        options=list(etf_names.keys()),
        default=["AGG", "GOVT", "LQD"]
    )

    period = st.selectbox(
        "Performance period",
        ["1 Month", "3 Months", "1 Year", "All Available"],
        index=2
    )

    months_map = {
        "1 Month": 1,
        "3 Months": 3,
        "1 Year": 12
    }

    if selected_etfs:

        chart_data = prices[selected_etfs].copy()

        if period != "All Available":
            cutoff = (
                chart_data.index.max()
                - pd.DateOffset(months=months_map[period])
            )
            chart_data = chart_data.loc[
                chart_data.index >= cutoff
            ]

        chart_data = chart_data.ffill().dropna()

        if chart_data.empty:
            st.warning("Insufficient data for this comparison.")
        else:
            normalized = (
                chart_data / chart_data.iloc[0] - 1
            ) * 100

            fig = go.Figure()

            for ticker in selected_etfs:
                fig.add_trace(go.Scatter(
                    x=normalized.index,
                    y=normalized[ticker],
                    name=ticker,
                    mode="lines"
                ))

            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Cumulative return (%)",
                hovermode="x unified",
                height=470
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    st.caption(
        "Source: Yahoo Finance | Adjusted ETF market prices. "
        "Returns are ETF proxies, not official benchmark returns."
    )

    st.divider()

    st.subheader("ETF Characteristics")

    characteristics = load_etf_characteristics()

    benchmark_tickers = [
        "AGG", "GOVT", "LQD",
        "MUB", "TIP", "IAGG"
    ]

    characteristics = characteristics[
        characteristics["ticker"].isin(benchmark_tickers)
    ].copy()

    characteristics = characteristics[[
        "ticker",
        "effective_duration_years",
        "sec_yield_pct",
        "expense_ratio_pct",
        "as_of"
    ]]

    characteristics = characteristics.rename(columns={
        "ticker": "ETF",
        "effective_duration_years": "Duration (years)",
        "sec_yield_pct": "30-Day SEC Yield (%)",
        "expense_ratio_pct": "Expense Ratio (%)",
        "as_of": "Data as of"
    })

    st.dataframe(
        characteristics,
        hide_index=True,
        use_container_width=True
    )

    st.caption(
        "Source: iShares | ETF characteristics are based "
        "on the indicated reporting dates."
    )


with tab3:
    st.header("Portfolio Risk & Allocation")

    st.caption(
        "Illustrative fixed income portfolio vs AGG benchmark proxy"
    )

    st.subheader("Portfolio Allocation")

    col1, col2 = st.columns(2)

    with col1:
        weight_shy = st.slider(
            "SHY — Short Treasury (%)",
            min_value=0,
            max_value=50,
            value=15,
            step=5
        )

    with col2:
        weight_igsb = st.slider(
            "IGSB — Short IG Corporate (%)",
            min_value=0,
            max_value=50,
            value=10,
            step=5
        )

    weight_agg = 100 - weight_shy - weight_igsb

    if weight_agg < 0:
        st.error("Total allocation cannot exceed 100%.")
        st.stop()

    weights = {
        "AGG": weight_agg / 100,
        "SHY": weight_shy / 100,
        "IGSB": weight_igsb / 100
    }

    st.write(
        f"**Current allocation:** "
        f"{weight_agg}% AGG / "
        f"{weight_shy}% SHY / "
        f"{weight_igsb}% IGSB"
    )

    st.divider()

    # Load ETF characteristics
    etf_data = load_etf_characteristics()
    etf_data = etf_data.set_index("ticker")

    # Portfolio effective duration
    portfolio_duration = sum(
        weights[ticker] *
        etf_data.loc[ticker, "effective_duration_years"]
        for ticker in weights
    )

    benchmark_duration = etf_data.loc[
        "AGG", "effective_duration_years"
    ]

    duration_gap = portfolio_duration - benchmark_duration

    # DV01 per $1 million
    portfolio_dv01 = portfolio_duration * 1_000_000 * 0.0001
    benchmark_dv01 = benchmark_duration * 1_000_000 * 0.0001

    col_duration, col_gap, col_dv01 = st.columns(3)

    col_duration.metric(
        "Portfolio Duration",
        f"{portfolio_duration:.2f} years"
    )

    col_gap.metric(
        "Duration vs AGG",
        f"{duration_gap:+.2f} years"
    )

    col_dv01.metric(
        "DV01 per $1M",
        f"${portfolio_dv01:,.0f}"
    )

    st.caption(
        f"AGG benchmark duration: {benchmark_duration:.2f} years | "
        f"Benchmark DV01: ${benchmark_dv01:,.0f} per $1M. "
        "First-order interest-rate sensitivity using ETF effective duration."
    )

    st.divider()

    st.subheader("Historical Performance & Active Risk")

    # Load historical adjusted ETF prices
    portfolio_prices = load_portfolio_prices()

    # Calculate portfolio returns using selected weights
    portfolio_returns = calculate_portfolio_performance(
        portfolio_prices,
        weights
    )

    # AGG benchmark returns
    benchmark_returns = portfolio_prices["AGG"].pct_change().dropna()

    # Align portfolio and benchmark dates
    comparison = pd.concat(
        [
            portfolio_returns.rename("Portfolio"),
            benchmark_returns.rename("Benchmark")
        ],
        axis=1
    ).dropna()

    # Daily active returns
    comparison["Active"] = (
        comparison["Portfolio"] - comparison["Benchmark"]
    )

    # Cumulative growth of $1
    portfolio_growth = (
        1 + comparison["Portfolio"]
    ).cumprod()

    benchmark_growth = (
        1 + comparison["Benchmark"]
    ).cumprod()

    # Cumulative returns
    portfolio_total_return = (
        portfolio_growth.iloc[-1] - 1
    ) * 100

    benchmark_total_return = (
        benchmark_growth.iloc[-1] - 1
    ) * 100

    # Annualized ex-post tracking error
    tracking_error = (
        comparison["Active"].std(ddof=1)
        * (252 ** 0.5)
        * 100
    )

    # Maximum drawdown
    portfolio_drawdown = (
        portfolio_growth / portfolio_growth.cummax() - 1
    ).min() * 100

    benchmark_drawdown = (
        benchmark_growth / benchmark_growth.cummax() - 1
    ).min() * 100

    # Display performance metrics
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Portfolio Total Return",
        f"{portfolio_total_return:+.2f}%"
    )

    col2.metric(
        "Active Cumulative Return",
        f"{portfolio_total_return - benchmark_total_return:+.2f} pp"
    )

    col3.metric(
        "Annualized Tracking Error",
        f"{tracking_error:.2f}%"
    )

    st.caption(
        f"AGG cumulative return: {benchmark_total_return:+.2f}% | "
        f"Portfolio max drawdown: {portfolio_drawdown:.2f}% | "
        f"AGG max drawdown: {benchmark_drawdown:.2f}%"
    )

    st.divider()

    # Historical performance chart
    st.subheader("Portfolio vs Benchmark")

    fig_performance = go.Figure()

    fig_performance.add_trace(go.Scatter(
        x=portfolio_growth.index,
        y=(portfolio_growth - 1) * 100,
        name="Candidate Portfolio",
        mode="lines"
    ))

    fig_performance.add_trace(go.Scatter(
        x=benchmark_growth.index,
        y=(benchmark_growth - 1) * 100,
        name="AGG Benchmark",
        mode="lines"
    ))

    fig_performance.update_layout(
        xaxis_title="Date",
        yaxis_title="Cumulative Return (%)",
        hovermode="x unified",
        height=440
    )

    st.plotly_chart(
        fig_performance,
        use_container_width=True
    )

    st.divider()

    # Rolling tracking error
    st.subheader("Rolling 12-Month Tracking Error")

    rolling_te = (
        comparison["Active"]
        .rolling(window=252, min_periods=252)
        .std(ddof=1)
        * (252 ** 0.5)
        * 100
    )

    fig_te = go.Figure()

    fig_te.add_trace(go.Scatter(
        x=rolling_te.index,
        y=rolling_te,
        name="Rolling Tracking Error",
        mode="lines",
        connectgaps=True
    ))

    fig_te.update_layout(
        xaxis_title="Date",
        yaxis_title="Annualized Tracking Error (%)",
        height=380,
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_te,
        use_container_width=True
    )

    st.caption(
        "Source: Yahoo Finance adjusted ETF prices. "
        "Monthly portfolio rebalancing. "
        "Historical tracking error is calculated against AGG "
        "using daily active returns and 252 trading days."
    )


    st.divider()

    st.subheader("Duration Sensitivity Analysis")

    st.caption(
        "Estimate the immediate price impact of a parallel "
        "Treasury yield movement using effective duration."
    )

    rate_shock = st.slider(
        "Parallel Treasury yield shock (basis points)",
        min_value=-100,
        max_value=100,
        value=50,
        step=25
    )

    # Convert basis points into decimal yield change
    delta_yield = rate_shock / 10000

    # Approximate price changes using effective duration
    portfolio_impact = -portfolio_duration * delta_yield * 100
    benchmark_impact = -benchmark_duration * delta_yield * 100

    active_impact = (
        portfolio_impact - benchmark_impact
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Portfolio Price Impact",
        f"{portfolio_impact:+.2f}%"
    )

    col2.metric(
        "AGG Price Impact",
        f"{benchmark_impact:+.2f}%"
    )

    col3.metric(
        "Active Price Impact",
        f"{active_impact * 100:+.1f} bp"
    )

    st.divider()

    # Compare several parallel yield shocks
    scenarios = [-100, -75, -50, -25, 0, 25, 50, 75, 100]

    scenario_df = pd.DataFrame({
        "Shock (bp)": scenarios
    })

    scenario_df["Portfolio (%)"] = (
        -portfolio_duration
        * scenario_df["Shock (bp)"]
        / 100
    )

    scenario_df["AGG (%)"] = (
        -benchmark_duration
        * scenario_df["Shock (bp)"]
        / 100
    )

    scenario_df["Active (bp)"] = (
        scenario_df["Portfolio (%)"]
        - scenario_df["AGG (%)"]
    ) * 100

    fig_scenarios = go.Figure()

    fig_scenarios.add_trace(go.Bar(
        x=scenario_df["Shock (bp)"],
        y=scenario_df["Active (bp)"],
        name="Active Price Impact"
    ))

    fig_scenarios.update_layout(
        xaxis_title="Parallel Yield Shock (bp)",
        yaxis_title="Active Price Impact (bp)",
        height=380,
        xaxis=dict(
            tickmode="array",
            tickvals=scenarios,
            ticktext=[f"{x:+d}" if x != 0 else "0" for x in scenarios]
        )
    )

    st.plotly_chart(
        fig_scenarios,
        use_container_width=True
    )

    st.caption(
        "Duration-based estimates assuming parallel yield shifts "
        "and unchanged credit spreads. "
        "Excludes convexity, carry, roll-down and trading costs."
    )
