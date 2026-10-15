"""Random number generation and seed management utilities."""
from typing import Optional
import numpy as np


DEFAULT_SEED: int = 42


def get_rng(seed: Optional[int] = None) -> np.random.Generator:
    """Return a NumPy default_rng with the given or default fixed seed.
    
    Guarantees reproducibility across simulation runs.
    """
    if seed is None:
        seed = DEFAULT_SEED
    return np.random.default_rng(seed)
