# Trading Strategy Structure for Backtrader

## Overview
This document explains the structure of trading strategies for use with the Backtrader library in the FinTrader project.

## Strategy Architecture

### Core Components

Each strategy class inherits from `bt.Strategy` and implements the following key components:

#### 1. **Parameters (`params` tuple)**
```python
params = (
    ('parameter_name', default_value),  # Description
    ('position_size', 0.10),            # Risk management (10% of cash)
    ('printlog', False),                # Logging control
)
```
Parameters allow you to:
- Tune strategy sensitivity and risk
- Optimize via parameter sweeps
- Compare different configurations

#### 2. **Initialization (`__init__` method)**
```python
def __init__(self):
    # Define indicators
    self.indicator = bt.indicators.SomeIndicator(self.data.close)
    
    # Track state
    self.order = None
```
- Initialize indicators (calculated once efficiently)
- Set up state tracking variables
- Indicators are auto-calculated for all historical data

#### 3. **Signal Generation (`next` method)**
```python
def next(self):
    # Called on each new bar
    if not self.position:
        # Check BUY conditions
        if self.indicator[0] < threshold:
            self.order = self.buy(size=size)
    else:
        # Check SELL conditions
        if self.indicator[0] > threshold:
            self.order = self.sell(size=self.position.size)
```
- Executed for each bar in the dataset
- Implement your trading logic here
- Access current values with `[0]`, previous with `[-1]`, etc.

#### 4. **Order Management (`notify_order` method)**
```python
def notify_order(self, order):
    # Handle order status changes
    if order.status in [order.Completed]:
        if order.isbuy():
            # Track entry price, commission, etc.
        else:
            # Handle exit
```
- Monitors order execution
- Tracks entry prices for stop loss/take profit
- Handles failed orders

#### 5. **Trade Tracking (`notify_trade` method)**
```python
def notify_trade(self, trade):
    if trade.isclosed:
        # Log P&L
```
- Called when a complete trade (entry + exit) closes
- Useful for P&L tracking

## Implemented Strategies

### 1. RSI_Strat ([Strats/RSI_Strat.py](Strats/RSI_Strat.py))
**Logic:** Mean-reversion based on RSI indicator
- **BUY:** When RSI < oversold threshold (default: 30)
- **SELL:** When RSI > overbought threshold (default: 70)

**Key Parameters:**
- `rsi_period`: RSI calculation period (default: 14)
- `rsi_oversold`: Oversold threshold (default: 30)
- `rsi_overbought`: Overbought threshold (default: 70)
- `position_size`: Fraction of cash per trade (default: 0.10)

### 2. Bol_Strat ([Strats/Bol_Strat.py](Strats/Bol_Strat.py))
**Logic:** Mean-reversion using Bollinger Bands
- **BUY:** When price crosses below lower band
- **SELL:** When price crosses above upper band (or middle band)

**Key Parameters:**
- `bb_period`: Bollinger Bands period (default: 20)
- `bb_devfactor`: Standard deviation multiplier (default: 2.0)
- `exit_on_middle`: Exit when price crosses SMA (default: True)
- `stop_loss_pct`: Stop loss percentage (default: None)
- `take_profit_pct`: Take profit percentage (default: None)

### 3. Rand_Strat ([Strats/Rand_Strat.py](Strats/Rand_Strat.py))
**Logic:** Random trading (baseline for comparison)
- Randomly generates trades with specified probability
- Useful to verify other strategies beat random chance

**Key Parameters:**
- `trade_probability`: Chance of trading per bar (default: 0.01)
- `hold_bars`: Minimum holding period (default: 10)
- `seed`: Random seed for reproducibility

## Usage Examples

### Basic Backtest
```python
from Strats.RSI_Strat import RSI_Strat
import backtrader as bt

cerebro = bt.Cerebro()
cerebro.addstrategy(RSI_Strat, rsi_oversold=25, rsi_overbought=75)
# ... add data, set broker, run ...
results = cerebro.run()
```

### Parameter Optimization
```python
cerebro.optstrategy(
    RSI_Strat,
    rsi_period=range(10, 20),
    rsi_oversold=range(20, 35, 5)
)
results = cerebro.run()
```

### Complete Example
See [backtest_example.py](backtest_example.py) for comprehensive examples including:
- Single strategy backtests
- Parameter optimization
- Multi-strategy comparison
- Performance metrics

## Running Backtests

1. **Ensure data is processed:**
   ```bash
   # Run your DataExtract notebook to generate processed_eurgbp_m1.csv
   ```

2. **Run the example backtest:**
   ```bash
   python backtest_example.py
   ```

3. **Or create your own:**
   ```python
   from backtest_example import run_single_backtest
   from Strats.RSI_Strat import RSI_Strat
   
   params = {'rsi_oversold': 30, 'rsi_overbought': 70}
   run_single_backtest(RSI_Strat, params)
   ```

## Creating New Strategies

To create a new strategy:

1. **Create new file** in `Strats/` directory
2. **Import Backtrader:**
   ```python
   import backtrader as bt
   ```

3. **Define class inheriting from `bt.Strategy`:**
   ```python
   class MyStrategy(bt.Strategy):
       params = (
           ('my_param', default_value),
       )
       
       def __init__(self):
           self.my_indicator = bt.indicators.SMA(self.data.close, period=20)
           self.order = None
       
       def next(self):
           if not self.position:
               if self.data.close[0] > self.my_indicator[0]:
                   self.order = self.buy()
           else:
               if self.data.close[0] < self.my_indicator[0]:
                   self.order = self.sell(size=self.position.size)
       
       def notify_order(self, order):
           # Handle order notifications
           pass
   ```

4. **Test your strategy** using `backtest_example.py` framework

## Performance Metrics

Backtrader provides built-in analyzers:
- **SharpeRatio**: Risk-adjusted returns
- **DrawDown**: Maximum drawdown percentage
- **Returns**: Total and annualized returns
- **TradeAnalyzer**: Win rate, total trades, P&L

Access via:
```python
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
results = cerebro.run()
sharpe = results[0].analyzers.sharpe.get_analysis()
```

## Best Practices

1. **Parameter Tuning:**
   - Use optimization to find best parameters
   - Beware of overfitting - validate on different time periods
   - Use walk-forward analysis

2. **Risk Management:**
   - Implement position sizing (`position_size` parameter)
   - Add stop losses and take profits
   - Consider maximum drawdown limits

3. **Testing:**
   - Always compare against random strategy baseline
   - Test on out-of-sample data
   - Consider transaction costs (commission)

4. **Performance:**
   - Use Backtrader's built-in indicators (optimized)
   - Avoid loops in `next()` method
   - Pre-calculate what you can in `__init__()`

## Advanced Position Sizing

### Overview

Proper position sizing is crucial for risk management and long-term profitability. The strategies support two position sizing methods:

### 1. Fixed Fractional (Default)

Uses a fixed percentage of available cash for each trade.

```python
params = (
    ('position_method', 'fixed'),
    ('position_size', 0.10),  # Use 10% of cash per trade
)
```

**Pros:**
- Simple and predictable
- Easy to understand
- Consistent exposure

**Cons:**
- Doesn't adapt to market conditions
- Doesn't account for win rate or edge
- May be too aggressive or conservative

### 2. Kelly Criterion

Calculates optimal position size based on historical win rate and average win/loss ratio.

**Formula:** `Kelly % = W - [(1 - W) / R]`
- W = win rate
- R = average win / average loss

```python
params = (
    ('position_method', 'kelly'),
    ('kelly_fraction', 0.25),  # Use quarter-Kelly (conservative)
)
```

**Features:**
- Adapts to strategy performance
- Maximizes long-term growth
- Automatically tracks last 100 trades
- Requires minimum 20 trades before activating
- Uses fractional Kelly (0.25 = quarter-Kelly) for safety

**Pros:**
- Mathematically optimal for growth
- Adapts based on performance
- Increases size when winning, decreases when losing

**Cons:**
- Can be volatile with full Kelly
- Requires trading history to be effective
- Assumes consistent edge over time

**Best Practice:** Use quarter-Kelly (0.25) or half-Kelly (0.5) for conservative, stable growth.

### Position Sizing Module

The `position_sizer.py` module provides:

#### Static Utilities
```python
from Strats.position_sizer import PositionSizer

# Kelly Criterion
kelly_pct = PositionSizer.kelly_criterion(
    win_rate=0.55, 
    avg_win=0.02, 
    avg_loss=-0.015,
    fraction=0.25
)

# Fixed Fractional
size = PositionSizer.fixed_fractional(fraction=0.02)

```

### Usage Examples

#### Example 1: RSI with Kelly Criterion
```python
from Strats.RSI_Strat import RSI_Strat

cerebro.addstrategy(
    RSI_Strat,
    position_method='kelly',
    kelly_fraction=0.25,  # Quarter-Kelly
    rsi_oversold=30,
    rsi_overbought=70
)


#### Example 2: Comparing Position Sizing Methods
```python
# Run position_sizing_example.py to compare methods
python position_sizing_example.py
```

See [position_sizing_example.py](position_sizing_example.py) for comprehensive comparisons.

### How Kelly Criterion Works in Practice

1. **Initial Trades (< 20):** Uses fixed position sizing
2. **After 20 Trades:** Switches to Kelly Criterion
3. **Continuous Adaptation:** Recalculates Kelly % after each trade
4. **Safety First:** Uses fractional Kelly (default 0.25) to reduce volatility

**Example Calculation:**
- Win Rate: 60%
- Avg Win: +3%
- Avg Loss: -2%
- Win/Loss Ratio: 3% / 2% = 1.5
- Kelly %: 0.60 - (0.40 / 1.5) = 0.333 (33.3%)
- Quarter-Kelly: 0.333 × 0.25 = 0.083 (8.3% position size)

### Choosing the Right Method

| Situation | Recommended Method | Reason |
|-----------|-------------------|---------|
| **Starting out** | Fixed (10-20%) | Simple, predictable |
| **Proven strategy** | Kelly (0.25-0.5) | Optimal growth |
| **High volatility** | Fixed (smaller %) | Conservative approach |
| **Testing/development** | Fixed | Easier to compare results |
| **Live trading** | Kelly (0.25) | Adapts to conditions |

## Next Steps

- Implement more sophisticated strategies (MACD, moving average crossovers, etc.)
- Add risk management modules
- Implement walk-forward optimization
- Create ensemble strategies
- Add machine learning based strategies (integrate with PPO_Strat)
