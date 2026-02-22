## Strategy Backtester for Financial Markets

This project aims to develop, test and evaluate a range of trading strategies on historical financial data

PPO_Strat.py - Contains the code for a Reinforcement Learning (RL) based strategy called Proximal Policy Optimisation (PPO). This strategy aims to use general market indicators to learn a profitable action policy in a range of market environments.

RSI_Strat.py - Contains the code for a simple Relative Strength Index (RSI) only algorithm where trades are actioned upon a heuristic signal being where the market RSI deviates above/below the concensus 80/20 limits.

Bol_Strat.py - Contains the code for a simple Bollinger bands based strategy where signals are made based on the pre-defined rules set by the Bollinger bands.

Rand_Strat.py - Contains the code for a baseline strategy in which agents will make trades at random. This baseline will provide an effective comparison during the evaluation stage.

Ultimately, the strategies will be tested and evaluated on a range of unseen historical market data. We can then perform the analysis providing measures such as maximum drawdown (Max_DD), win rate, total returns, and a variety of other commonly used metrics.

The true goal is to develop a somewhat competent RL-based trading model that takes care to be realistically implementable (i.e takes into account real life constraints/factors, and does not utilise future data (Data Leakage)).

### Historical Financial Data Retrieval - Dukascopy-node

All historic data was obtained free from the dukascopy-node api. Follow this link to thier Github repository for documentation: https://github.com/Leo4815162342/dukascopy-node