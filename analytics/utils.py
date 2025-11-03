from __future__ import annotations

# imports
from typing import Iterable, List
import math
import random


# two-sample permutation test for difference in proportions between groups A and B
def permutation_test(
    success_a: int,
    total_a: int,
    success_b: int,
    total_b: int,
    iters: int = 10000,
) -> float:
    """
    Conduct a two-sample permutation test for difference in proportions (A vs B).
    Returns a two-sided p-value without relying on normal approximation assumptions.

    Parameters:
        success_a, total_a: successes / total in group A
        success_b, total_b: successes / total in group B
        iters: number of permutation iterations

    This test is useful for small samples where z-tests may be unreliable.
    """
    # handle invalid input
    if total_a <= 0 or total_b <= 0:
        return 1.0

    # observed difference in proportions
    p_obs = (success_a / total_a) - (success_b / total_b)

    # pooled binary outcomes (1 = success, 0 = failure)
    pooled: List[int] = (
        [1] * success_a
        + [0] * (total_a - success_a)
        + [1] * success_b
        + [0] * (total_b - success_b)
    )

    count = 0
    for _ in range(iters):
        # shuffle outcomes between groups
        random.shuffle(pooled)
        a_slice = pooled[:total_a]
        b_slice = pooled[total_a:]
        # compute permuted difference
        p_diff = (sum(a_slice) / total_a) - (sum(b_slice) / total_b)
        # count extreme outcomes relative to observed difference
        if abs(p_diff) >= abs(p_obs):
            count += 1

    # empirical two-sided p-value
    return count / iters


# compute simple arithmetic mean
def _mean(xs: Iterable[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


# compute sample variance (unbiased)
def _variance(xs: Iterable[float]) -> float:
    xs = list(xs)
    m = _mean(xs)
    return (
        sum((x - m) ** 2 for x in xs) / (len(xs) - 1) if len(xs) > 1 else float("nan")
    )


# quick VIF calculator for lightweight multicollinearity screening
def quick_vif(columns: list[list[float]]) -> list[float]:
    """
    Compute a simplified variance inflation factor (VIF) per predictor column.
    Used to detect potential multicollinearity (VIF > ~10 suggests strong correlation).

    Parameters:
        columns: list of predictor columns, each column being a list of floats

    Returns:
        list of approximate VIF values (same order as input columns)

    Note:
        This is an approximate method — it normalizes predictors and estimates R²
        via average pairwise correlations. For accurate values, use statsmodels.
    """

    vifs: list[float] = []
    n_cols = len(columns)
    if n_cols <= 1:
        return [1.0] * n_cols  # trivial case: no multicollinearity possible

    # normalize columns (z-score) to remove scale effects
    zcols = []
    for col in columns:
        m = _mean(col)
        s2 = _variance(col)
        sd = math.sqrt(s2) if s2 > 0 else 1.0
        zcols.append([(x - m) / sd for x in col])

    # compute approximate VIF per predictor
    for i in range(n_cols):
        xi = zcols[i]
        others = [zcols[j] for j in range(n_cols) if j != i]

        # helper: compute Pearson correlation between two vectors
        def pearson(a, b):
            m = _mean(a)
            n = _mean(b)
            num = sum((x - m) * (y - n) for x, y in zip(a, b))
            da = math.sqrt(sum((x - m) ** 2 for x in a))
            db = math.sqrt(sum((y - n) ** 2 for y in b))
            return num / (da * db) if da > 0 and db > 0 else 0.0

        if not others:
            vifs.append(1.0)
            continue

        # average absolute correlation between predictor and all others
        avg_abs_corr = sum(abs(pearson(xi, oj)) for oj in others) / len(others)

        # proxy R^2 and corresponding VIF (bounded to avoid infinite results)
        r2 = min(0.99, max(0.0, avg_abs_corr**2))
        vif = 1.0 / (1.0 - r2)
        vifs.append(vif)

    return vifs
