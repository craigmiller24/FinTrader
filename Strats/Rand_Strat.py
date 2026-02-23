import backtrader as bt
import random


class Rand_Strat(bt.Strategy):
    """
    Random trading strategy (baseline for comparison).
    
    Randomly generates buy/sell signals with configurable probability.
    Useful as a baseline to ensure other strategies outperform random trading.
    """
    
    params = (
        ('trade_probability', 0.01),   # Probability of trading on any given bar (0-1)
        ('position_size', 0.02),       # Fraction of cash to use per trade
        ('hold_bars', 10),             # Minimum bars to hold position before random exit
        ('seed', None),                # Random seed for reproducibility (None = random)
        ('printlog', False),           # Print trade logs
    )
    
    def __init__(self):
        """Initialize strategy state."""
        # Set random seed if provided
        if self.params.seed is not None:
            random.seed(self.params.seed)
        
        # Track order and holding period
        self.order = None
        self.bar_count_in_position = 0
        
    def notify_order(self, order):
        """Handle order notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                if self.params.printlog:
                    self.log(f'BUY EXECUTED: Price: {order.executed.price:.5f}')
                self.bar_count_in_position = 0
            else:
                if self.params.printlog:
                    self.log(f'SELL EXECUTED: Price: {order.executed.price:.5f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.params.printlog:
                self.log('Order Canceled/Margin/Rejected')
        
        self.order = None
    
    def notify_trade(self, trade):
        """Handle trade notifications."""
        if not trade.isclosed:
            return
        
        if self.params.printlog:
            self.log(f'TRADE PROFIT: Net {trade.pnlcomm:.2f}')
    
    def next(self):
        """Execute random trading logic."""
        # Check if an order is pending
        if self.order:
            return
        
        # Increment bar count if in position
        if self.position:
            self.bar_count_in_position += 1
        
        # Random decision
        should_trade = random.random() < self.params.trade_probability
        
        if not should_trade:
            return
        
        # Check if we are in the market
        if not self.position:
            # Random BUY
            cash = self.broker.get_cash()
            size = (cash * self.params.position_size) / self.data.close[0]
            
            self.order = self.buy(size=size)
            if self.params.printlog:
                self.log('RANDOM BUY SIGNAL')
        
        else:
            # Only allow random SELL after minimum holding period
            if self.bar_count_in_position >= self.params.hold_bars:
                self.order = self.sell(size=self.position.size)
                if self.params.printlog:
                    self.log('RANDOM SELL SIGNAL')
    
    def log(self, txt, dt=None):
        """Logging function."""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
    
    def stop(self):
        """Called when strategy finishes."""
        if self.params.printlog:
            self.log(f'Final Portfolio Value: {self.broker.getvalue():.2f}')
            self.log(f'(Random Strategy with probability {self.params.trade_probability})')

    