"""
Example backtest script demonstrating how to use trading strategies with Backtrader.

This script shows:
1. Loading processed data
2. Running single strategy backtests
3. Parameter optimization
4. Comparing multiple strategies
"""

import matplotlib
matplotlib.use('Agg')  # Use before importing pyplot
import backtrader as bt
import pandas as pd
from datetime import datetime
import sys
import os

# Import custom strategies
from Strats.RSI_Strat import RSI_Strat
from Strats.Bol_Strat import Bol_Strat
from Strats.Rand_Strat import Rand_Strat


def run_single_backtest(strategy_class, strategy_params=None, data_path='.Data/processed_btcgbp_m5.csv'):
    """
    Run a single backtest with specified strategy and parameters.
    
    Args:
        strategy_class: The strategy class to backtest
        strategy_params: Dictionary of strategy parameters (optional)
        data_path: Path to processed data CSV
    
    Returns:
        cerebro: Backtrader Cerebro instance with results
    """
    # Create a cerebro instance
    cerebro = bt.Cerebro()
    
    # Add strategy with parameters
    if strategy_params:
        cerebro.addstrategy(strategy_class, **strategy_params)
    else:
        cerebro.addstrategy(strategy_class)
    
    # Load data
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Create Backtrader data feed
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,  # Index is datetime
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1  # Not used for forex
    )
    
    # Add data to cerebro
    cerebro.adddata(data)
    
    # Set broker parameters
    cerebro.broker.setcash(10000.0)  # Starting cash
    cerebro.broker.setcommission(commission=0.0001)  # 1 pip spread for forex (~0.01%)
    
    # Add analyzers for performance metrics
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Print starting conditions
    print(f'Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}')
    
    # Run backtest
    results = cerebro.run()
    strat = results[0]
    
    # Print ending conditions
    print(f'Ending Portfolio Value: ${cerebro.broker.getvalue():.2f}')
    
    # Print performance metrics
    print('\n--- Performance Metrics ---')
    
    # Sharpe Ratio
    sharpe = strat.analyzers.sharpe.get_analysis()
    print(f"Sharpe Ratio: {sharpe.get('sharperatio', 'N/A')}")
    
    # Drawdown
    drawdown = strat.analyzers.drawdown.get_analysis()
    print(f"Max Drawdown: {drawdown.get('max', {}).get('drawdown', 'N/A'):.2f}%")
    
    # Returns
    returns = strat.analyzers.returns.get_analysis()
    print(f"Total Return: {returns.get('rtot', 0) * 100:.2f}%")
    
    # Trade Statistics
    trades = strat.analyzers.trades.get_analysis()
    total_trades = trades.get('total', {}).get('total', 0)
    won_trades = trades.get('won', {}).get('total', 0)
    lost_trades = trades.get('lost', {}).get('total', 0)
    
    print(f"\nTotal Trades: {total_trades}")
    if total_trades > 0:
        print(f"Won: {won_trades} | Lost: {lost_trades}")
        print(f"Win Rate: {(won_trades/total_trades)*100:.2f}%")
    
    # Plot results disabled due to tkinter GUI requirements
    #cerebro.plot(style='candlestick', savefig='backtest_result.png')
    
    return cerebro


def optimize_strategy(strategy_class, param_ranges, data_path='.Data/processed_btcgbp_m5.csv'):
    """
    Run parameter optimization for a strategy.
    
    Args:
        strategy_class: The strategy class to optimize
        param_ranges: Dictionary of parameter ranges, e.g., {'rsi_period': range(10, 20)}
        data_path: Path to processed data CSV
    
    Returns:
        List of results
    """
    cerebro = bt.Cerebro(optreturn=True)
    
    # Add strategy with parameter ranges
    cerebro.optstrategy(strategy_class, **param_ranges)
    
    # Load data
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
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
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0001)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    results = cerebro.run(maxcpus=10)
    
    # Display results
    print("\n--- Optimization Results ---")
    for result in results:
        strat = result[0]
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 'N/A')
        returns = strat.analyzers.returns.get_analysis().get('rtot', 0) * 100
        
        # Extract parameters
        params_str = ", ".join([f"{k}={v}" for k, v in strat.params._getkwargs().items()])
        print(f"{params_str} | Sharpe: {sharpe} | Return: {returns:.2f}%")
    
    return results


def compare_strategies(strategies_config, data_path='.Data/processed_btcgbp_m5.csv'):
    """
    Compare multiple strategies side by side.
    
    Args:
        strategies_config: List of tuples (strategy_class, params_dict, name)
        data_path: Path to processed data CSV
    """
    print("\n=== Strategy Comparison ===\n")
    
    results_summary = []
    
    for strategy_class, params, name in strategies_config:
        print(f"\n--- Testing {name} ---")
        cerebro = run_single_backtest(strategy_class, params, data_path)
        
        # Store results
        strat = cerebro.runstrats[0][0]
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 'N/A')
        returns = strat.analyzers.returns.get_analysis().get('rtot', 0) * 100
        drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 'N/A')
        
        results_summary.append({
            'Strategy': name,
            'Return (%)': f"{returns:.2f}",
            'Sharpe Ratio': sharpe,
            'Max Drawdown (%)': f"{drawdown:.2f}" if drawdown != 'N/A' else 'N/A',
            'Final Value': f"${cerebro.broker.getvalue():.2f}"
        })
    
    # Print comparison table
    print("\n\n=== Summary ===")
    df_results = pd.DataFrame(results_summary)
    print(df_results.to_string(index=False))


if __name__ == '__main__':
    # # Example 1: Run single backtest with RSI strategy
    # print("\n" + "="*60)
    # print("EXAMPLE 1: Single RSI Strategy Backtest")
    # print("="*60)
    
    # rsi_params = {
    #     'rsi_period': 14,
    #     'rsi_oversold': 30,
    #     'rsi_overbought': 70,
    #     'position_size': 0.10,
    #     'printlog': True
    # }
    
    # run_single_backtest(RSI_Strat, rsi_params)
    
    # # Example 2: Run single backtest with Bollinger Bands strategy
    # print("\n" + "="*60)
    # print("EXAMPLE 2: Single Bollinger Bands Strategy Backtest")
    # print("="*60)
    
    # bb_params = {
    #     'bb_period': 20,
    #     'bb_devfactor': 2.0,
    #     'exit_on_middle': True,
    #     'position_size': 0.10,
    #     'printlog': True
    # }
    
    # run_single_backtest(Bol_Strat, bb_params)
    
    # # Example 3: Optimize RSI parameters
    # print("\n" + "="*60)
    # print("EXAMPLE 3: RSI Parameter Optimization")
    # print("="*60)
    
    # # Note: This can be slow on large datasets - reduce ranges for testing
    # optimize_strategy(
    #     RSI_Strat,
    #     param_ranges={
    #         'rsi_period': range(10, 20, 2),
    #         'rsi_oversold': range(25, 35, 5),
    #         'rsi_overbought': range(65, 75, 5),
    #     }
    # )
    
    # # Example 4: Compare multiple strategies
    # print("\n" + "="*60)
    # print("EXAMPLE 4: Strategy Comparison")
    # print("="*60)
    
    # strategies_to_compare = [
    #     (RSI_Strat, {'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70}, 'RSI (14, 30, 70)'),
    #     (RSI_Strat, {'rsi_period': 14, 'rsi_oversold': 25, 'rsi_overbought': 75}, 'RSI (14, 25, 75)'),
    #     (Bol_Strat, {'bb_period': 20, 'exit_on_middle': True}, 'BB (20, exit mid)'),
    #     (Bol_Strat, {'bb_period': 20, 'exit_on_middle': False}, 'BB (20, no exit mid)'),
    # ]
    
    # compare_strategies(strategies_to_compare)

    # Example 5: Run single backtest with Bollinger Bands strategy
    print("\n" + "="*60)
    print("EXAMPLE 5: Backtest Random Strategy")
    print("="*60)

    rand_params = {
        'trade_probability': 0.01,  # 1% chance to trade each bar
        'position_size': 0.10,
        'hold_bars': 10,
        'seed': 42,  # Set seed for reproducibility
        'printlog': True
    }

    run_single_backtest(Rand_Strat, rand_params)


    