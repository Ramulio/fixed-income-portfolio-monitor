# Fixed Income Benchmark & Portfolio Monitor

An interactive Python dashboard designed to monitor fixed income markets, compare ETF benchmarks, and analyze portfolio risk and performance.

**[Launch Interactive Dashboard](https://fixed-income-portfolio-monitor.streamlit.app/)**

## Overview

This project combines fixed income market data with portfolio analytics to explore how different allocations affect interest rate exposure, historical performance, and risk relative to a benchmark.

The dashboard is built with Python, Streamlit, and Plotly, using publicly available market data.

## Dashboard Features

### 1. Market Overview

- US Treasury yield curve monitoring across 2Y, 5Y, 10Y, and 30Y maturities.
- Historical comparison of 10Y real yields and breakeven inflation.
- Investment Grade and High Yield credit spread monitoring, including absolute levels and changes over time.

### 2. Benchmark Monitor

- Historical performance comparison across six fixed income ETFs: AGG, GOVT, LQD, MUB, TIP, and IAGG.
- Interactive cumulative return charts.
- ETF characteristics, including effective duration, SEC yield, and expense ratio.

### 3. Portfolio Risk

- Adjustable portfolio allocation across AGG, SHY, and IGSB.
- Weighted effective duration and DV01 analysis.
- Historical portfolio performance versus AGG, assuming monthly rebalancing.
- Annualized tracking error and maximum drawdown.
- Rolling 12-month tracking error.
- Duration sensitivity analysis under parallel yield shocks.

The default portfolio allocation is 75% AGG, 15% SHY, and 10% IGSB, with AGG used as the benchmark proxy.

## Data Sources

- **FRED:** US Treasury yields, real yields, breakeven inflation, and corporate credit spreads.
- **Yahoo Finance:** Historical adjusted ETF prices.
- **iShares:** ETF characteristics and fund information.

Market data availability and observation dates may differ across sources. The dashboard combines locally stored market data with Yahoo Finance downloads for ETF benchmark monitoring.

## Methodology

Historical portfolio performance is calculated using adjusted ETF prices and monthly portfolio rebalancing.

Tracking error is calculated from the standard deviation of daily active returns, annualized using 252 trading days.

Interest rate scenario analysis uses effective duration to estimate first-order price sensitivity, assuming parallel yield movements and unchanged credit spreads. The estimates exclude convexity, carry, roll-down, and trading costs.

## Technology

Python · Streamlit · Pandas · NumPy · Plotly · yfinance

## Author

**Giulio Ramunno**

Fixed Income Research & Portfolio Analytics | November 2026
