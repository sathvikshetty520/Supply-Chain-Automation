"""Stochastic distribution generators for lead times and customer demand."""
from typing import Tuple
import numpy as np


def lognormal_parameters_from_mean_std(mean: float, std: float) -> Tuple[float, float]:
    """Convert normal mean and standard deviation to lognormal mu and sigma.
    
    Formula:
      sigma^2 = ln(1 + (std / mean)^2)
      mu = ln(mean) - 0.5 * sigma^2
    """
    if mean <= 0:
        raise ValueError(f"Mean must be strictly positive, got {mean}")
    if std <= 0:
        return np.log(mean), 0.0

    variance = std ** 2
    sigma_sq = np.log(1.0 + (variance / (mean ** 2)))
    sigma = np.sqrt(sigma_sq)
    mu = np.log(mean) - 0.5 * sigma_sq
    return float(mu), float(sigma)


def sample_lead_time(mean: float, std: float, rng: np.random.Generator, min_lead_time: float = 0.5) -> float:
    """Sample lead time from a lognormal distribution with mean and std."""
    if std <= 1e-6:
        return max(min_lead_time, float(mean))
    mu, sigma = lognormal_parameters_from_mean_std(mean, std)
    val = float(rng.lognormal(mean=mu, sigma=sigma))
    return max(min_lead_time, val)


def sample_demand(distribution: str, mean: float, std: float, rng: np.random.Generator) -> float:
    """Sample daily customer demand, bounded below by zero."""
    if mean <= 0:
        return 0.0
    
    if distribution == "poisson":
        return float(rng.poisson(lam=mean))
    elif distribution == "lognormal":
        if std <= 1e-6:
            return float(mean)
        mu, sigma = lognormal_parameters_from_mean_std(mean, std)
        return float(rng.lognormal(mean=mu, sigma=sigma))
    else:  # default normal
        if std <= 1e-6:
            return float(mean)
        val = float(rng.normal(loc=mean, scale=std))
        return max(0.0, val)
