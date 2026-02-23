import backtrader as bt
from .position_sizer import PositionSizer

class Bol_Strat(bt.Strategy):
    """
    Bollinger Bands mean-reversion trading strategy with advanced position sizing.
    
    Signals:
    - BUY when price crosses below lower band (oversold)
    - SELL when price crosses above upper band (overbought)
    - Optional: Exit on middle band (SMA) crossover
    """
    
    params = (
        ('bb_period', 20),              # Bollinger Bands period
        ('bb_devfactor', 2.0),          # Number of standard deviations
        
        # Position sizing parameters
        ('position_method', 'fixed'),   # 'fixed', 'kelly'
        ('position_size', 0.02),        # Fixed fraction of cash (if method='fixed')
        ('kelly_fraction', 0.25),       # Fraction of Kelly to use (if method='kelly')
        
        ('exit_on_middle', True),       # Exit position when price crosses middle band
        ('stop_loss_pct', None),        # Stop loss percentage (None to disable)
        ('take_profit_pct', None),      # Take profit percentage (None to disable)
        ('printlog', False),            # Print trade logs
    )
    
    def __init__(self):
        """Initialize indicators and state variables."""
        # Calculate Bollinger Bands
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_devfactor
        )
        
        # Extract individual bands for easier reference
        self.bb_top = self.bb.lines.top
        self.bb_mid = self.bb.lines.mid
        self.bb_bot = self.bb.lines.bot
        
        # Track order and entry price for stop loss/take profit
        self.order = None
        self.entry_price = None
        self.entry_comm = None
        
        # Track trade history for Kelly Criterion
        self.wins = []
        self.losses = []
        self.min_trades_for_kelly = 20
        
    def notify_order(self, order):
        """Handle order notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.entry_comm = order.executed.comm
                if self.params.printlog:
                    self.log(f'BUY EXECUTED: Price: {order.executed.price:.5f}, '
                            f'Size: {order.executed.size:.2f}, Comm: {order.executed.comm:.2f}')
            else:  # Sell
                if self.params.printlog:
                    self.log(f'SELL EXECUTED: Price: {order.executed.price:.5f}, '
                            f'Size: {order.executed.size:.2f}, Comm: {order.executed.comm:.2f}')
                self.entry_price = None
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.params.printlog:
                self.log('Order Canceled/Margin/Rejected')
        
        self.order = None
    
    def notify_trade(self, trade):
        """Handle trade notifications for P&L tracking and Kelly calculation."""
        if not trade.isclosed:
            return
        
        # Track performance for Kelly Criterion
        trade_return = trade.pnlcomm / abs(trade.value) if trade.value != 0 else 0
        
        if trade.pnlcomm > 0:
            self.wins.append(trade_return)
        else:
            self.losses.append(trade_return)
        
        # Keep only recent history (last 100 trades)
        if len(self.wins) > 100:
            self.wins = self.wins[-100:]
        if len(self.losses) > 100:
            self.losses = self.losses[-100:]
        
        if self.params.printlog:
            self.log(f'TRADE PROFIT: Gross {trade.pnl:.2f}, Net {trade.pnlcomm:.2f}')
    
    def calculate_position_size(self):
        """
        Calculate position size based on configured method.
        
        Returns:
            Number of units to buy
        """
        cash = self.broker.get_cash()
        portfolio_value = self.broker.getvalue()
        current_price = self.data.close[0]
        
        if self.params.position_method == 'kelly':
            # Use Kelly Criterion if we have enough trade history
            total_trades = len(self.wins) + len(self.losses)
            
            if total_trades >= self.min_trades_for_kelly:
                win_rate = len(self.wins) / total_trades
                avg_win = sum(self.wins) / len(self.wins) if self.wins else 0.02
                avg_loss = sum(self.losses) / len(self.losses) if self.losses else -0.015
                
                kelly_fraction = PositionSizer.kelly_criterion(
                    win_rate, avg_win, avg_loss,
                    max_leverage=1.0,
                    fraction=self.params.kelly_fraction
                )
                
                # Fall back to fixed sizing if Kelly produces invalid result
                if kelly_fraction > 0:
                    position_value = portfolio_value * kelly_fraction
                    size = position_value / current_price
                    
                    if self.params.printlog:
                        self.log(f'Kelly: WinRate={win_rate:.2%}, Kelly={kelly_fraction:.2%}')
                else:
                    # Kelly returned 0 - fall back to fixed sizing
                    size = (cash * self.params.position_size) / current_price
                    if self.params.printlog:
                        self.log(f'Kelly returned 0 (WinRate={win_rate:.2%}), using fixed size')
            else:
                # Fall back to fixed size until we have enough history
                size = (cash * self.params.position_size) / current_price
        
        else:
            # Default: Fixed fractional position sizing
            size = (cash * self.params.position_size) / current_price
        
        return size
    
    def next(self):
        """Execute strategy logic on each bar."""
        # Check if an order is pending
        if self.order:
            return
        
        current_price = self.data.close[0]
        
        # Check if we are in the market
        if not self.position:
            # Not in market - look for BUY signal (price below lower band)
            if current_price < self.bb_bot[0]:
                # Calculate position size using configured method
                size = self.calculate_position_size()
                
                self.order = self.buy(size=size)
                if self.params.printlog:
                    self.log(f'BUY SIGNAL: Price {current_price:.5f} < Lower Band {self.bb_bot[0]:.5f}, Size={size:.2f}')
        
        else:
            # In market - check exit conditions
            should_exit = False
            exit_reason = ""
            
            # Check if price crossed above upper band (take profit on mean reversion)
            if current_price > self.bb_top[0]:
                should_exit = True
                exit_reason = f'Price {current_price:.5f} > Upper Band {self.bb_top[0]:.5f}'
            
            # Check if price crossed middle band (optional exit)
            elif self.params.exit_on_middle and current_price > self.bb_mid[0]:
                should_exit = True
                exit_reason = f'Price {current_price:.5f} > Middle Band {self.bb_mid[0]:.5f}'
            
            # Check stop loss
            elif self.params.stop_loss_pct and self.entry_price:
                stop_price = self.entry_price * (1 - self.params.stop_loss_pct / 100)
                if current_price < stop_price:
                    should_exit = True
                    exit_reason = f'Stop Loss: Price {current_price:.5f} < {stop_price:.5f}'
            
            # Check take profit
            elif self.params.take_profit_pct and self.entry_price:
                target_price = self.entry_price * (1 + self.params.take_profit_pct / 100)
                if current_price > target_price:
                    should_exit = True
                    exit_reason = f'Take Profit: Price {current_price:.5f} > {target_price:.5f}'
            
            # Execute exit if conditions met
            if should_exit:
                self.order = self.sell(size=self.position.size)
                if self.params.printlog:
                    self.log(f'SELL SIGNAL: {exit_reason}')
    
    def log(self, txt, dt=None):
        """Logging function."""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
    
    def stop(self):
        """Called when strategy finishes."""
        if self.params.printlog:
            self.log(f'Final Portfolio Value: {self.broker.getvalue():.2f}')
            self.log(f'(BB Period {self.params.bb_period}, '
                    f'Dev Factor {self.params.bb_devfactor}, '
                    f'Exit on Middle: {self.params.exit_on_middle})')

    