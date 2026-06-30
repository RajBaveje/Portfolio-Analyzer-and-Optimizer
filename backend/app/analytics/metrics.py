import numpy as np
import pandas as pd
from scipy.optimize import minimize

def calculate_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    if std_return == 0:
        return 0.0
    
    # Annualize: daily mean * 252 / (daily std * sqrt(252)) -> (mean/std) * sqrt(252)
    sharpe = ((mean_return - risk_free_rate) / (std_return + 1e-8)) * np.sqrt(252)
    return float(sharpe)

def calculate_sortino_ratio(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    mean_return = np.mean(returns)
    
    downside_returns = returns[returns < risk_free_rate]
    if len(downside_returns) < 2:
        return 0.0
        
    downside_std = np.std(downside_returns)
    if downside_std == 0:
        return 0.0
        
    sortino = ((mean_return - risk_free_rate) / (downside_std + 1e-8)) * np.sqrt(252)
    return float(sortino)

def calculate_max_drawdown(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    # Convert returns to a compounding equity curve starting at 1.0
    equity_curve = np.cumprod(1.0 + returns)
    
    # Track the running maximum peak
    running_max = np.maximum.accumulate(equity_curve)
    
    # Avoid division by zero if running_max drops out
    running_max = np.where(running_max == 0, 1e-8, running_max)
    
    drawdowns = (equity_curve - running_max) / running_max
    return float(np.min(drawdowns))

def calculate_var_and_cvar(returns: np.ndarray, confidence_level: float = 0.95) -> tuple[float, float]:
    """
    Computes Value at Risk (VaR) and Conditional VaR (CVaR / Expected Shortfall).
    """
    if len(returns) == 0:
        return 0.0, 0.0
    sorted_returns = np.sort(returns)
    index = int((1.0 - confidence_level) * len(sorted_returns))
    
    index = max(0, min(index, len(sorted_returns) - 1))
    
    var = float(sorted_returns[index])
    
    # CVaR is the mean of all losses exceeding the VaR threshold boundary
    tail_losses = sorted_returns[:index + 1]
    cvar = float(np.mean(tail_losses)) if len(tail_losses) > 0 else var
    
    return var, cvar

def calculate_beta_and_correlation(portfolio_returns: np.ndarray, market_returns: np.ndarray) -> tuple[float, float]:
    """
    Computes systematic market exposure (Beta) and Pearson correlation coefficient.
    """
    if len(portfolio_returns) < 2 or len(market_returns) < 2:
        return 1.0, 0.0
        
    # Align shapes if mismatched during lookback gaps
    min_len = min(len(portfolio_returns), len(market_returns))
    p_ret = portfolio_returns[-min_len:]
    m_ret = market_returns[-min_len:]
    
    covariance_matrix = np.cov(p_ret, m_ret)
    covariance = covariance_matrix[0, 1]
    market_variance = covariance_matrix[1, 1]
    
    beta = covariance / (market_variance + 1e-8)
    
    correlation_matrix = np.corrcoef(p_ret, m_ret)
    correlation = correlation_matrix[0, 1]
    
    if np.isnan(correlation):
        correlation = 0.0
        
    return float(beta), float(correlation)

def markowitz_optimize(returns: np.ndarray, risk_free_rate: float = 0.0) -> np.ndarray:
    """
    Classic Mean-Variance optimization baseline maximizing the Sharpe ratio.
    Enforces a strict 30% asset allocation cap to prevent single-ticker concentration.
    returns: shape (T, N) - T days, N assets
    """
    num_assets = returns.shape[1]
    mean_returns = np.mean(returns, axis=0)
    covariance_matrix = np.cov(returns.T)

    # Minimize the negative Sharpe ratio to maximize actual Sharpe
    def negative_sharpe(weights):
        portfolio_return = np.dot(weights, mean_returns) * 252
        portfolio_volatility = np.sqrt(np.dot(weights, np.dot(covariance_matrix, weights))) * np.sqrt(252)
        return -(portfolio_return - risk_free_rate) / (portfolio_volatility + 1e-8)

    # Constraints: Weights must sum to exactly 1.0
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    
    # Bounds: No short selling (0.0), max 30% in any single asset
    bounds = [(0.0, 0.3)] * num_assets
    
    initial_weights = np.ones(num_assets) / num_assets

    result = minimize(
        negative_sharpe, 
        initial_weights, 
        method="SLSQP",
        bounds=bounds, 
        constraints=constraints
    )
    
    if not result.success:
        return initial_weights 
        
    return result.x