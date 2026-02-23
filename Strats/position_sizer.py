"""
Advanced position sizing methods for risk management.

Includes:
- Kelly Criterion
- Fixed fractional size
"""

import backtrader as bt
import numpy as np


class PositionSizer:
    """
    Advanced position sizing calculator for trading strategies.
    """
    
    @staticmethod
    def kelly_criterion(win_rate, avg_win, avg_loss, max_leverage=1.0, fraction=0.5):
        """
        Calculate position size using Kelly Criterion.
        
        Kelly % = W - [(1 - W) / R]
        where W = win rate, R = average win / average loss
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade return (e.g., 0.02 for 2%)
            avg_loss: Average losing trade return (e.g., -0.015 for -1.5%)
            max_leverage: Maximum leverage allowed (default: 1.0)
            fraction: Fraction of Kelly to use (0.5 = half-Kelly, safer)
        
        Returns:
            Position size as fraction of capital (0-1)
        """
        # Handle invalid inputs
        if win_rate < 0 or win_rate > 1:
            return 0.0
        
        if avg_loss >= 0 or avg_win <= 0:
            return 0.0
        
        # Handle edge cases
        if win_rate == 0:  # Never wins
            return 0.0
        
        if win_rate == 1.0:  # Always wins - use max leverage
            kelly = max_leverage
        else:
            # Win/Loss ratio
            win_loss_ratio = abs(avg_win / avg_loss)
            
            # Kelly formula
            kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        # Apply fractional Kelly for safety
        kelly = kelly * fraction
        
        # Ensure non-negative and within max leverage
        kelly = max(0.0, min(kelly, max_leverage))
        
        return kelly
    
    @staticmethod
    def fixed_fractional(fraction=0.02):
        """
        Fixed fractional position sizing - risk fixed % of capital per trade.
        
        Args:
            fraction: Fraction of capital to risk (default: 0.02 = 2%)
        
        Returns:
            Position size as fraction of capital
        """
        return max(0.0, min(fraction, 1.0))


class AdaptivePositionSizer(bt.Sizer):
    """
    Backtrader Sizer that uses historical performance to calculate Kelly Criterion.
    
    Automatically tracks win rate and average win/loss to calculate optimal position size.
    """
    
    params = (
        ('method', 'kelly'),           # 'kelly', 'fixed'
        ('kelly_fraction', 0.25),      # Fraction of Kelly (0.25 = quarter-Kelly, very conservative)
        ('fixed_size', 0.1),           # Fixed fractional size if method='fixed'
        ('min_trades', 20),            # Minimum trades before using Kelly
        ('max_position', 0.3),         # Maximum position size (30% of capital)
        ('min_position', 0.05),        # Minimum position size (5% of capital)
    )
    
    def __init__(self):
        super(AdaptivePositionSizer, self).__init__()
        self.wins = []
        self.losses = []
    
    def _getsizing(self, comminfo, cash, data, isbuy):
        """
        Calculate position size based on configured method.
        """
        if not isbuy:
            # For sell orders, return current position size
            return self.strategy.position.size
        
        # Get current portfolio value
        portfolio_value = self.broker.getvalue()
        
        if self.params.method == 'kelly' and len(self.wins) + len(self.losses) >= self.params.min_trades:
            # Calculate Kelly position size
            total_trades = len(self.wins) + len(self.losses)
            win_rate = len(self.wins) / total_trades if total_trades > 0 else 0.5
            
            avg_win = np.mean(self.wins) if self.wins else 0.02
            avg_loss = np.mean(self.losses) if self.losses else -0.015
            
            position_fraction = PositionSizer.kelly_criterion(
                win_rate, avg_win, avg_loss, 
                max_leverage=self.params.max_position,
                fraction=self.params.kelly_fraction
            )
        else:
            # Default to fixed fractional
            position_fraction = self.params.fixed_size
        
        # Ensure within bounds
        position_fraction = max(self.params.min_position, 
                               min(position_fraction, self.params.max_position))
        
        # Calculate number of units
        position_value = portfolio_value * position_fraction
        size = position_value / data.close[0]
        
        return int(size)
    
    def notify_trade(self, trade):
        """
        Track trade results for Kelly calculation.
        """
        if not trade.isclosed:
            return
        
        # Calculate return as percentage
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
