# Machine Learning & Reinforcement Learning in TraderSuit Pro

This directory contains the components for the intelligence layers of the trading system.

## 1. Machine Learning (ML)
We utilize ML for **Non-linear Filtering** and **Pattern Recognition**:

*   **Meta-Labeling (`src/ml/meta_labeling`)**: A secondary model that takes primary strategy signals and historical trade features to estimate the P(success). This allows the system to filter out "low confidence" trades, significantly improving the Profit Factor.
*   **Pattern Recognition (`src/ml/pattern_recognition`)**: Uses hybrid CNN (Convolutional Neural Networks) for candlestick shape detection and LSTM (Long Short-Term Memory) for temporal momentum dependencies.

## 2. Reinforcement Learning (RL)
RL is primarily explored for **Dynamic Portfolio Optimization**:

*   **Agent Environment (`src/rl/environment`)**: A custom OpenAI Gym-compatible environment that represents the portfolio state (exposure, equity, volatility).
*   **Policy Learning (`src/rl/agents`)**: PPO (Proximal Policy Optimization) agents are used to learn optimal position sizing and deleveraging rules in response to regime shifts, going beyond static Kelly-based sizing.

## 3. Bayesian Optimization
Located in `src/research/optimization`, this engine uses **Tree-structured Parzen Estimators (TPE)** to find the global optimum for:
*   Strategy windows (e.g., Donchian/Bollinger periods).
*   Risk-per-trade fractions.
*   Regime detection sensitivities.

This ensures the system parameters are not "manually tuned" but rather data-driven.
