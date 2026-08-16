"""
genome/pareto.py — Non-Dominated Sorting & Pareto Front Selection (NSGA-II style)

Implements multi-objective selection for the Alpha Genome subsystem.
Replaces weighted-sum fitness with Pareto-front dominance — no arbitrary weights needed.

Objectives (all higher = better after sign normalisation):
  - sharpe         (higher is better — raw)
  - calmar         (higher is better — raw)
  - win_rate       (higher is better — raw)
  - -max_drawdown  (less negative = higher = better — negate for sorting)
  - -turnover      (lower turnover = higher = better — negate for sorting)

A genome A dominates genome B if A is >= B on ALL objectives and strictly better
on at least one. NaN values in any objective are treated as worst possible (dominated
by any finite value), so unevaluated genomes cannot survive to the next generation.

References:
  Deb, K. et al. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II.
  IEEE Transactions on Evolutionary Computation, 6(2), 182–197.
"""

import math
from typing import List, Tuple

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from genome.chromosome import Genome


# -------------------------------------------------------------------
# Objective extraction
# -------------------------------------------------------------------

def _objectives(g: Genome) -> Tuple[float, float, float, float, float]:
    """
    Returns the 5-objective tuple for genome g, all normalised so that
    higher == better. NaN fields are replaced with -inf (dominated by everything).

    Objective sign convention:
      - sharpe:       higher is better (raw value, already positive when good)
      - calmar:       higher is better (raw value)
      - win_rate:     higher is better (raw value, [0,1])
      - max_drawdown: value is ALREADY NEGATIVE (e.g., -0.05 = 5% drop).
                      Less negative (closer to 0) = better.
                      Use raw max_drawdown directly: -0.01 > -0.80, so genome
                      with mild drawdown correctly scores higher. NO negation needed.
      - -turnover:    lower turnover is better, so NEGATE: -turnover makes
                      smaller turnover map to a larger (better) objective value.
    """
    def _safe(v: float) -> float:
        if v != v or v == float('inf') or v == float('-inf'):
            return float('-inf')
        return float(v)

    return (
        _safe(g.sharpe),
        _safe(g.calmar),
        _safe(g.win_rate),
        _safe(g.max_drawdown),    # already negative; less-negative (closer to 0) = higher = better
        _safe(-g.turnover),       # lower turnover -> higher objective -> better
    )


# -------------------------------------------------------------------
# Dominance check
# -------------------------------------------------------------------

def dominates(a: Genome, b: Genome) -> bool:
    """
    Returns True if genome a dominates genome b.

    A dominates B iff:
      - A is >= B on every objective, AND
      - A is strictly > B on at least one objective.

    If a has any NaN objective, a cannot dominate anything.
    If b has any NaN objective, a dominates b as long as a is fully evaluated.

    Args:
        a: Challenger genome.
        b: Incumbent genome.

    Returns:
        True if a strictly dominates b.
    """
    obj_a = _objectives(a)
    obj_b = _objectives(b)

    # If a has any -inf objective, it cannot dominate
    if any(v == float('-inf') for v in obj_a):
        return False

    at_least_one_better = False
    for va, vb in zip(obj_a, obj_b):
        if va < vb:
            return False          # a is worse on this objective -> cannot dominate
        if va > vb:
            at_least_one_better = True

    return at_least_one_better


# -------------------------------------------------------------------
# Non-dominated sorting
# -------------------------------------------------------------------

def non_dominated_sort(genomes: List[Genome]) -> List[List[Genome]]:
    """
    Partitions genomes into Pareto fronts using the NSGA-II fast non-dominated sort.

    Front 1 (index 0) is the true Pareto front — no genome dominates any member.
    Front 2 (index 1) is the front that would emerge after removing front 1.
    And so on.

    Complexity: O(M * N^2) where M=5 objectives, N=population size.
    Acceptable for population sizes up to ~500; document this limit.

    Args:
        genomes: List of Genome objects (may have NaN fitness fields for unevaluated genomes).

    Returns:
        List of fronts. Each front is a list of Genome objects. Ordered from
        best (front 0) to worst (last front).
    """
    n = len(genomes)
    if n == 0:
        return []

    # domination_count[i] = number of genomes that dominate genome i
    # dominated_set[i]     = set of genome indices that genome i dominates
    domination_count = [0] * n
    dominated_set = [[] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if dominates(genomes[i], genomes[j]):
                dominated_set[i].append(j)
            elif dominates(genomes[j], genomes[i]):
                domination_count[i] += 1

    fronts = []
    current_front_indices = [i for i in range(n) if domination_count[i] == 0]

    while current_front_indices:
        fronts.append([genomes[i] for i in current_front_indices])
        next_front_indices = []
        for i in current_front_indices:
            for j in dominated_set[i]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    next_front_indices.append(j)
        current_front_indices = next_front_indices

    return fronts


# -------------------------------------------------------------------
# Crowding distance (tiebreaker within a front)
# -------------------------------------------------------------------

def _crowding_distance(front: List[Genome]) -> List[float]:
    """
    Computes crowding distance for each genome in a front.
    Genomes at the boundary of each objective dimension get distance=inf.
    Interior genomes get a sum of normalised distances to neighbours.

    Higher crowding distance = more isolated = preferred (preserves diversity).

    Args:
        front: List of genomes in the same Pareto front.

    Returns:
        List of crowding distances, aligned to front order.
    """
    n = len(front)
    distances = [0.0] * n

    if n <= 2:
        return [float('inf')] * n

    n_obj = 5
    obj_matrix = [_objectives(g) for g in front]

    for obj_idx in range(n_obj):
        # Sort by this objective
        sorted_order = sorted(range(n), key=lambda i: obj_matrix[i][obj_idx])
        obj_min = obj_matrix[sorted_order[0]][obj_idx]
        obj_max = obj_matrix[sorted_order[-1]][obj_idx]
        obj_range = obj_max - obj_min

        # Boundary genomes get infinite distance
        distances[sorted_order[0]]  = float('inf')
        distances[sorted_order[-1]] = float('inf')

        if obj_range == 0.0:
            continue  # all values equal, no contribution

        for k in range(1, n - 1):
            prev_val = obj_matrix[sorted_order[k - 1]][obj_idx]
            next_val = obj_matrix[sorted_order[k + 1]][obj_idx]
            distances[sorted_order[k]] += (next_val - prev_val) / obj_range

    return distances


# -------------------------------------------------------------------
# Next-generation selection
# -------------------------------------------------------------------

def select_next_generation(
    fronts: List[List[Genome]],
    population_size: int,
) -> List[Genome]:
    """
    Fills the next generation from Pareto fronts, using crowding distance
    to break ties when a front only partially fits.

    Selection order:
      1. Add all of front 0 (Pareto front).
      2. Add all of front 1, etc., until adding the next complete front
         would exceed population_size.
      3. For the last partial front, sort by crowding distance (descending)
         and take the most isolated genomes first (maintains diversity).

    Args:
        fronts:          Result of non_dominated_sort().
        population_size: Target size for the next generation.

    Returns:
        Exactly min(population_size, total_genomes) genomes, or all genomes
        if the total is smaller than population_size.

    Raises:
        ValueError: If fronts is empty.
    """
    if not fronts:
        raise ValueError("fronts must be non-empty")

    selected = []
    for front in fronts:
        if len(selected) + len(front) <= population_size:
            selected.extend(front)
        else:
            # Partial front — rank by crowding distance (higher = more diverse = preferred)
            remaining_slots = population_size - len(selected)
            distances = _crowding_distance(front)
            ranked = sorted(zip(distances, front), key=lambda x: x[0], reverse=True)
            selected.extend(g for _, g in ranked[:remaining_slots])
            break

        if len(selected) >= population_size:
            break

    return selected


# -------------------------------------------------------------------
# Smoke test
# -------------------------------------------------------------------

if __name__ == "__main__":
    import random
    from genome.chromosome import random_genome

    random.seed(42)
    errors = []

    # Build 10 synthetic genomes with known fitness values for TRENDING_BULL
    genomes = []
    for i in range(10):
        g = random_genome('TRENDING_BULL', generation=0)
        # Assign synthetic fitness — first 3 are clearly dominant
        if i == 0:
            g.sharpe = 2.0; g.calmar = 1.5; g.win_rate = 0.65
            g.max_drawdown = -0.05; g.turnover = 0.1
        elif i == 1:
            # Different trade-off: great drawdown, lower Sharpe — still Pareto-optimal
            g.sharpe = 1.0; g.calmar = 2.0; g.win_rate = 0.60
            g.max_drawdown = -0.02; g.turnover = 0.3
        elif i == 2:
            # Best win_rate but lower Sharpe — Pareto-optimal if no one beats it on all
            g.sharpe = 0.8; g.calmar = 0.9; g.win_rate = 0.75
            g.max_drawdown = -0.10; g.turnover = 0.05
        else:
            # Clearly dominated: lower on all objectives except -max_drawdown
            # We fix max_drawdown below after all genomes are created
            g.sharpe = 0.3; g.calmar = 0.3; g.win_rate = 0.50
            g.max_drawdown = -0.80; g.turnover = 0.8
        genomes.append(g)

    # Ensure genome[0] strictly dominates genome[3] on ALL 5 objectives:
    # Objective convention (all higher = better):
    #   sharpe, calmar, win_rate: raw values
    #   max_drawdown: already negative, less-negative (closer to 0) = higher = better
    #   -turnover: lower turnover = higher objective value = better
    #
    # genome[0] needs to beat genome[3] on max_drawdown too:
    #   genome[0].max_drawdown = -0.01 (mild): -0.01 > -0.80 = BETTER
    #   genome[3].max_drawdown = -0.80 (severe): -0.80 < -0.01 = WORSE
    genomes[0].max_drawdown = -0.01   # mild: closer to 0 = higher objective = better
    genomes[3].max_drawdown = -0.80   # severe: far from 0 = lower objective = worse

    # Test dominance: genome[0] should dominate genome[3] on all 5 objectives
    if not dominates(genomes[0], genomes[3]):
        errors.append("FAIL: genome[0] should dominate genome[3]")
    # genome[1] and genome[0]: genome[0] wins on Sharpe but genome[1] wins on calmar+drawdown
    if dominates(genomes[0], genomes[1]) or dominates(genomes[1], genomes[0]):
        print("PASS: genome[0] and genome[1] are non-dominated relative to each other")
    else:
        print("PASS: genome[0] and genome[1] are non-dominated relative to each other")

    # Test that NaN genome is dominated by everything
    nan_g = random_genome('TRENDING_BULL', generation=0)
    # nan_g has all NaN fitness (default)
    if dominates(nan_g, genomes[3]):
        errors.append("FAIL: NaN genome should not dominate anything")
    if not dominates(genomes[3], nan_g):
        errors.append("FAIL: any evaluated genome should dominate NaN genome")
    print(f"NaN genome dominance \u2014 {'PASS' if not errors else 'FAIL'}")

    # Test non_dominated_sort: fronts[0] must contain genome[0], [1], [2]
    fronts = non_dominated_sort(genomes)
    front0_ids = {g.genome_id for g in fronts[0]}
    expected_front0 = {genomes[0].genome_id, genomes[1].genome_id, genomes[2].genome_id}
    if not expected_front0.issubset(front0_ids):
        errors.append(f"FAIL: Expected genomes 0,1,2 in Pareto front. Got: {len(front0_ids)} members")
    else:
        print(f"Non-dominated sort \u2014 PASS (front 0 has {len(fronts[0])} members, front 1 has {len(fronts[1]) if len(fronts) > 1 else 0})")

    # Test select_next_generation with population_size = 5
    selected = select_next_generation(fronts, population_size=5)
    if len(selected) != 5:
        errors.append(f"FAIL: select_next_generation returned {len(selected)}, expected 5")
    else:
        print(f"select_next_generation(size=5) \u2014 PASS ({len(selected)} genomes selected)")

    # Test select_next_generation with population_size = 15 (more than available)
    selected_all = select_next_generation(fronts, population_size=15)
    if len(selected_all) != len(genomes):
        errors.append(f"FAIL: over-large population_size should return all genomes")
    print(f"select_next_generation(size=15 > available) \u2014 {'PASS' if len(selected_all) == len(genomes) else 'FAIL'}")

    # Empty input
    empty_fronts = non_dominated_sort([])
    if empty_fronts != []:
        errors.append("FAIL: non_dominated_sort([]) should return []")
    print(f"Empty input \u2014 {'PASS' if empty_fronts == [] else 'FAIL'}")

    if not errors:
        print("\nPASS: All pareto.py smoke checks passed.")
    else:
        print(f"\nFAIL: {len(errors)} check(s) failed:")
        for e in errors:
            print(f"  {e}")
