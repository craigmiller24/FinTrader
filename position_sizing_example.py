"""
Example demonstrating advanced position sizing methods with Kelly Criterion.

This script shows how to:
1. Use fixed position sizing (default)
2. Use Kelly Criterion for optimal position sizing
3. Compare performance between methods
"""

import backtrader as bt
import pandas as pd
from Strats.RSI_Strat import RSI_Strat
from Strats.Bol_Strat import Bol_Strat


def run_backtest_with_position_method(strategy_class, method='fixed', data_path='.Data/processed_btcgbp_m5.csv'):
    """
    Run backtest with specified position sizing method.
    
    Args:
        strategy_class: Strategy class to test
        method: 'fixed' or 'kelly'
        data_path: Path to data
    """
    cerebro = bt.Cerebro()
    
    # Configure strategy with position sizing method
    if method == 'kelly':
        params = {
            'position_method': 'kelly',
            'kelly_fraction': 0.25,  # Quarter-Kelly for safety
            'printlog': False
        }
    else:  # fixed
        params = {
            'position_method': 'fixed',
            'position_size': 0.10,
            'printlog': False
        }
    
    cerebro.addstrategy(strategy_class, **params)
    
    # Load data
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    print(f"Date range: {df.index[0]} to {df.index[-1]}, {len(df):,} bars")
    
    # Create data feed
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1
    )
    
    cerebro.adddata(data)
    
    # Set broker parameters
    cerebro.broker.setcash(1000000.0)
    cerebro.broker.setcommission(commission=0.0001)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    print(f'Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}')
    
    # Run backtest
    results = cerebro.run()
    strat = results[0]
    
    print(f'Ending Portfolio Value: ${cerebro.broker.getvalue():.2f}')
    
    # Print performance metrics
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    
    total_trades = trades.get('total', {}).get('total', 0)
    won_trades = trades.get('won', {}).get('total', 0)
    lost_trades = trades.get('lost', {}).get('total', 0)
    
    return {
        'method': method.upper(),
        'final_value': cerebro.broker.getvalue(),
        'return_pct': returns.get('rtot', 0) * 100,
        'sharpe': sharpe.get('sharperatio', 'N/A'),
        'max_dd': drawdown.get('max', {}).get('drawdown', 0),
        'total_trades': total_trades,
        'win_rate': (won_trades/total_trades)*100 if total_trades > 0 else 0
    }


def compare_position_sizing_methods(strategy_class, data_path='.Data/processed_btcgbp_m5.csv'):
    """
    Compare all position sizing methods side by side.
    """
    print("\n" + "="*70)
    print(f"POSITION SIZING COMPARISON - {strategy_class.__name__}")
    print("="*70 + "\n")
    
    results = []
    
    # Test each method
    for method in ['fixed', 'kelly']:
        print(f"\n--- Testing {method.upper()} position sizing ---")
        result = run_backtest_with_position_method(strategy_class, method, data_path)
        results.append(result)
        print()
    
    # Print comparison table
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    df_results = pd.DataFrame(results)
    df_results = df_results[['method', 'final_value', 'return_pct', 'sharpe', 'max_dd', 'total_trades', 'win_rate']]
    df_results.columns = ['Method', 'Final Value ($)', 'Return (%)', 'Sharpe', 'Max DD (%)', 'Trades', 'Win Rate (%)']
    
    # Format for display
    df_results['Final Value ($)'] = df_results['Final Value ($)'].apply(lambda x: f'${x:.2f}')
    df_results['Return (%)'] = df_results['Return (%)'].apply(lambda x: f'{x:.2f}%')
    df_results['Max DD (%)'] = df_results['Max DD (%)'].apply(lambda x: f'{x:.2f}%')
    df_results['Win Rate (%)'] = df_results['Win Rate (%)'].apply(lambda x: f'{x:.1f}%')
    
    print(df_results.to_string(index=False))
    print()
    
    print("\nKEY INSIGHTS:")
    print("- FIXED: Simple, consistent position size (baseline)")
    print("- KELLY: Adapts based on historical win rate & avg win/loss")
    print("  * Starts with fixed sizing, switches to Kelly after 20 trades")
    print("  * Uses 25% (quarter-Kelly) for conservative risk management")
    print()


if __name__ == '__main__':
    # Example 1: Compare position sizing for RSI strategy
    print("\n" + "="*70)
    print("EXAMPLE 1: RSI Strategy Position Sizing Comparison")
    print("="*70)
    
    compare_position_sizing_methods(RSI_Strat)
    