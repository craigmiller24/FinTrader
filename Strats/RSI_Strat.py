import backtrader as bt
from .position_sizer import PositionSizer


class RSI_Strat(bt.Strategy):
    """
    RSI-based trading strategy with configurable parameters and advanced position sizing.
    
    Signals:
    - BUY when RSI crosses below oversold threshold
    - SELL when RSI crosses above overbought threshold
    """
    
    params = (
        ('rsi_period', 14),           # RSI calculation period
        ('rsi_oversold', 20),          # Oversold threshold for buy signals
        ('rsi_overbought', 80),        # Overbought threshold for sell signals
        
        # Position sizing parameters
        ('position_method', 'fixed'),  # 'fixed', 'kelly'
        ('position_size', 0.02),       # Fixed fraction of cash (if method='fixed')
        ('kelly_fraction', 0.25),      # Fraction of Kelly to use (if method='kelly')
        
        ('printlog', False),           # Print trade logs
    )
    
    def __init__(self):
        """Initialize indicators and state variables."""
        # Calculate RSI indicator
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )
        
        # Track order state
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        
        # Track trade history for Kelly Criterion
        self.wins = []
        self.losses = []
        self.min_trades_for_kelly = 20
        
    def notify_order(self, order):
        """Handle order notifications (filled, cancelled, etc.)."""
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted - nothing to do
            return
        
        # Check if order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
                if self.params.printlog:
                    self.log(f'BUY EXECUTED: Price: {order.executed.price:.5f}, '
                            f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            else:  # Sell
                if self.params.printlog:
                    self.log(f'SELL EXECUTED: Price: {order.executed.price:.5f}, '
                            f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.params.printlog:
                self.log('Order Canceled/Margin/Rejected')
        
        # Reset order
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
                        self.log(f'Kelly: WinRate={win_rate:.2%}, AvgWin={avg_win:.2%}, '
                                f'AvgLoss={avg_loss:.2%}, Kelly={kelly_fraction:.2%}')
                else:
                    # Kelly returned 0 - fall back to fixed sizing
                    size = (cash * self.params.position_size) / current_price
                    if self.params.printlog:
                        self.log(f'Kelly returned 0 (WinRate={win_rate:.2%}), using fixed size')
            else:
                # Fall back to fixed size until we have enough history
                size = (cash * self.params.position_size) / current_price
                if self.params.printlog:
                    self.log(f'Using fixed size (need {self.min_trades_for_kelly - total_trades} more trades for Kelly)')
        
        else:
            # Default: Fixed fractional position sizing
            size = (cash * self.params.position_size) / current_price
        
        return size
    
    def next(self):
        """Execute strategy logic on each bar."""
        # Check if an order is pending
        if self.order:
            return
        
        # Get current RSI value
        current_rsi = self.rsi[0]
        
        # Check if we are in the market
        if not self.position:
            # Not in market - look for BUY signal
            if current_rsi < self.params.rsi_oversold:
                # Calculate position size using configured method
                size = self.calculate_position_size()
                
                # Execute buy order
                self.order = self.buy(size=size)
                if self.params.printlog:
                    self.log(f'BUY SIGNAL: RSI {current_rsi:.2f} < {self.params.rsi_oversold}, Size={size:.2f}')
        
        else:
            # In market - look for SELL signal
            if current_rsi > self.params.rsi_overbought:
                # Execute sell order (close position)
                self.order = self.sell(size=self.position.size)
                if self.params.printlog:
                    self.log(f'SELL SIGNAL: RSI {current_rsi:.2f} > {self.params.rsi_overbought}')
    
    def log(self, txt, dt=None):
        """Logging function for strategy."""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
    
    def stop(self):
        """Called when strategy finishes."""
        if self.params.printlog:
            self.log(f'Final Portfolio Value: {self.broker.getvalue():.2f}')
            self.log(f'(RSI Period {self.params.rsi_period}, '
                    f'Oversold {self.params.rsi_oversold}, '
                    f'Overbought {self.params.rsi_overbought})')

    