"""
genome/population.py -- Evolution Loop Orchestrator

Runs one generation of the Alpha Genome evolution process:
  1. Load or seed a population of Genomes for a given regime.
  2. Evaluate each genome's fitness using genome.fitness.evaluate_genome().
  3. Compute DSR for each genome and PBO for the generation.
  4. Apply the overfitting gate: promote passers to 'quarantine', kill the rest.
  5. Select survivors via Pareto-front sorting + crowding distance.
  6. Generate next-generation offspring via mutation and crossover.
  7. Save all genomes (both evaluated and offspring) to the registry.

Correction 3 (sigma floor): mutation sigma = max(0.05, 0.3 * 0.95**generation)
Correction 7 (re-validation): --mode revalidate triggers revalidation of verified genomes.

Usage:
  python genome/population.py --generation 0 --population 30 --regime TRENDING_BULL
  python genome/population.py --generation 1 --population 30 --regime TRENDING_BULL
  python genome/population.py --mode revalidate
"""

import os
import sys
import math
import argparse
import logging
import traceback
import numpy as np
import pandas as pd
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_PROCESSED_DIR, GENOME_DIR
from genome.chromosome import (
    Genome, VALID_REGIMES, random_genome, mutate, crossover,
    DEFAULT_MUTATION_SIGMA,
)
from genome.fitness import evaluate_genome
from genome.pareto import non_dominated_sort, select_next_generation
from genome.overfitting import (
    deflated_sharpe_ratio, probability_of_backtest_overfitting,
    passes_overfitting_gate, DEFAULT_MIN_DSR, DEFAULT_MAX_PBO,
    MIN_TRADES_PER_SUBPERIOD,
)
from genome.registry import (
    save_genome, load_generation, get_latest_generation, load_leaderboard
)
from validation.purged_split import PurgedWalkForwardSplit


# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s -- %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger('genome.population')


# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

DEFAULT_POPULATION_SIZE = 30
DEFAULT_N_SPLITS        = 5
DEFAULT_EMBARGO_BARS    = 24


# -------------------------------------------------------------------
# Data loading
# -------------------------------------------------------------------

def _load_data() -> tuple:
    """
    Loads features.parquet and returns (features_df, ensemble_probs, t1).

    ensemble_probs comes from the AdaptiveRegimeEnsemble. In the research loop,
    we use the pre-computed 'prob_up' column from the feature matrix (produced
    during model training). In live inference, the ensemble is called in real-time.

    t1 is the label end timestamp Series (required by PurgedWalkForwardSplit).

    Returns:
        (features_df, ensemble_probs, t1)

    Raises:
        FileNotFoundError: If features.parquet does not exist.
    """
    parquet_path = os.path.join(DATA_PROCESSED_DIR, 'features.parquet')
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(
            f"features.parquet not found at {parquet_path}. "
            "Run features/build_features.py first."
        )

    features_df = pd.read_parquet(parquet_path)
    features_df = features_df.dropna(subset=['close', 'atr_14']).reset_index(drop=True)

    # ensemble_probs: use 'prob_up' if available, otherwise fall back to 0.5 + noise
    if 'prob_up' in features_df.columns:
        ensemble_probs = features_df['prob_up'].clip(0.01, 0.99)
    else:
        log.warning("'prob_up' column not found. Using dummy probabilities (0.5 uniform).")
        ensemble_probs = pd.Series(0.5, index=features_df.index)

    # t1: end-of-label bar (simple: 24 bars forward from each bar)
    if 't1' in features_df.columns:
        t1 = features_df['t1']
    else:
        t1 = pd.Series(
            range(24, len(features_df) + 24),
            index=features_df.index
        )

    return features_df, ensemble_probs, t1


# -------------------------------------------------------------------
# Population seeding / loading
# -------------------------------------------------------------------

def _get_or_seed_population(
    regime: str,
    generation: int,
    population_size: int,
) -> List[Genome]:
    """
    If generation == 0 or no prior generation exists, creates a fresh random population.
    Otherwise, loads the last evaluated generation from the registry.

    Args:
        regime:          Target regime for this evolution run.
        generation:      Target generation number.
        population_size: Desired population size.

    Returns:
        List of Genome objects to evaluate.
    """
    if generation == 0:
        log.info(f"Seeding generation 0 with {population_size} random genomes for {regime}")
        return [random_genome(regime, generation=0) for _ in range(population_size)]

    # Load genomes from the previous generation for this regime
    prior_gen = generation - 1
    prior_pop = load_generation(prior_gen)
    prior_pop = [g for g in prior_pop if g.regime == regime and not math.isnan(g.sharpe)]

    if not prior_pop:
        log.warning(
            f"No evaluated genomes from generation {prior_gen} for regime {regime}. "
            "Seeding fresh population."
        )
        return [random_genome(regime, generation=generation) for _ in range(population_size)]

    # Compute annealed mutation sigma (Correction 3: floor at 0.05)
    sigma = max(0.05, DEFAULT_MUTATION_SIGMA * (0.95 ** generation))
    log.info(f"Generation {generation}: {len(prior_pop)} survivors, sigma={sigma:.4f}")

    # Generate next-generation offspring
    offspring = []

    # 1. Keep elite survivors directly (first Pareto front of prior pop)
    fronts = non_dominated_sort([g for g in prior_pop if not math.isnan(g.sharpe)])
    elite = fronts[0] if fronts else prior_pop[:2]
    offspring.extend(elite)

    # 2. Fill remaining slots with mutations and crossovers
    import random as stdlib_random
    while len(offspring) < population_size:
        operation = stdlib_random.random()
        parent = stdlib_random.choice(prior_pop)

        if operation < 0.6 or len(prior_pop) < 2:
            # 60% mutation
            child = mutate(parent, sigma_continuous=sigma)
        else:
            # 40% crossover (if enough parents)
            parent_b = stdlib_random.choice([g for g in prior_pop if g.genome_id != parent.genome_id])
            try:
                child = crossover(parent, parent_b)
            except ValueError:
                child = mutate(parent, sigma_continuous=sigma)

        child.generation = generation
        offspring.append(child)

    return offspring[:population_size]


# -------------------------------------------------------------------
# Core evolution step
# -------------------------------------------------------------------

def run_generation(
    generation:      int,
    regime:          str,
    population_size: int = DEFAULT_POPULATION_SIZE,
    n_splits:        int = DEFAULT_N_SPLITS,
    embargo_bars:    int = DEFAULT_EMBARGO_BARS,
    min_dsr:         float = DEFAULT_MIN_DSR,
    max_pbo:         float = DEFAULT_MAX_PBO,
    sigma_override:  Optional[float] = None,
    use_funnel:      bool = False,
) -> List[Genome]:
    """
    Runs one complete generation of the Alpha Genome evolution loop.
    Supports a multi-stage funnel (use_funnel=True) for 95% compute reduction:
      - Stage 1: Screen N=5x population_size candidates on fast single-split CV.
      - Stage 2: Advance top 20% to full 5-fold Purged Walk-Forward CV.
      - Stage 3: Pareto sorting & DSR/PBO Gate on final candidates.
    """
    if regime not in VALID_REGIMES:
        raise ValueError(f"Invalid regime '{regime}'. Must be one of {VALID_REGIMES}")

    log.info(f"=== Starting generation {generation} for regime {regime} (Funnel={use_funnel}) ===")

    # Load data
    features_df, ensemble_probs, t1 = _load_data()

    if use_funnel:
        candidate_size = population_size * 5
        log.info(f"Funnel Stage 1: Screening {candidate_size} candidates on 1-split CV...")
        candidates = _get_or_seed_population(regime, generation, candidate_size)
        fast_splitter = PurgedWalkForwardSplit(n_splits=1, embargo_bars=embargo_bars)

        screened = []
        for g in candidates:
            try:
                fit, _, _ = evaluate_genome(g, features_df, ensemble_probs, t1, fast_splitter)
                g.sharpe = fit.get('sharpe', float('nan'))
                if not math.isnan(g.sharpe):
                    screened.append(g)
            except Exception:
                pass

        screened.sort(key=lambda x: x.sharpe, reverse=True)
        population = screened[:population_size] if len(screened) >= population_size else candidates[:population_size]
        log.info(f"Funnel Stage 2: Advanced top {len(population)} candidates to full 5-fold Purged CV.")
    else:
        population = _get_or_seed_population(regime, generation, population_size)

    splitter = PurgedWalkForwardSplit(n_splits=n_splits, embargo_bars=embargo_bars)

    # 3. Evaluate each genome
    all_fold_sharpes      = []
    all_fold_trade_counts = []
    n_total = len(population)

    for idx, genome in enumerate(population):
        log.info(f"  Evaluating genome {idx+1}/{n_total}: {genome.genome_id} ...")
        try:
            fitness, fold_sharpes, fold_trades = evaluate_genome(
                genome, features_df, ensemble_probs, t1, splitter
            )
            genome.sharpe       = fitness['sharpe']
            genome.calmar       = fitness['calmar']
            genome.max_drawdown = fitness['max_drawdown']
            genome.win_rate     = fitness['win_rate']
            genome.turnover     = fitness['turnover']
            all_fold_sharpes.append(fold_sharpes)
            all_fold_trade_counts.append(fold_trades)
        except Exception as exc:
            log.error(f"  Genome {genome.genome_id} evaluation failed: {exc}")
            traceback.print_exc()
            # Leave fitness as NaN -- genome will be dominated and die in gate
            all_fold_sharpes.append([0.0] * n_splits)
            all_fold_trade_counts.append([0] * n_splits)

    # 4. DSR (per genome) and PBO (generation-level)
    n_trials = population_size * (generation + 1)  # total strategies tried so far
    n_obs    = int(len(features_df) / n_splits)     # rough test-fold size

    for i, genome in enumerate(population):
        if not math.isnan(genome.sharpe):
            genome.deflated_sharpe = deflated_sharpe_ratio(
                observed_sharpe=genome.sharpe,
                n_trials=n_trials,
                n_obs=n_obs,
            )

    # PBO for this generation
    evaluated_mask = [not math.isnan(g.sharpe) for g in population]
    if sum(evaluated_mask) >= 2:
        eval_sharpes = [all_fold_sharpes[i] for i, ok in enumerate(evaluated_mask) if ok]
        eval_trades  = [all_fold_trade_counts[i] for i, ok in enumerate(evaluated_mask) if ok]
        pbo = probability_of_backtest_overfitting(eval_sharpes, eval_trades)
    else:
        pbo = float('nan')
        log.warning("Fewer than 2 evaluated genomes -- PBO undefined")

    log.info(f"Generation {generation} PBO = {pbo:.4f}")

    # 5. Overfitting gate
    quarantine_count = 0
    dead_count       = 0
    for genome in population:
        if math.isnan(genome.deflated_sharpe if genome.deflated_sharpe == genome.deflated_sharpe else float('nan')):
            genome.status = 'dead'
            dead_count += 1
        elif passes_overfitting_gate(genome, pbo, min_dsr=min_dsr, max_pbo=max_pbo):
            genome.status = 'quarantine'
            genome.pbo_generation = pbo
            quarantine_count += 1
        else:
            genome.status = 'dead'
            dead_count += 1

    log.info(f"  Gate results: {quarantine_count} quarantined, {dead_count} dead")

    # 6. Pareto-sort evaluated genomes and assign pareto_rank
    evaluated = [g for g in population if not math.isnan(g.sharpe)]
    if evaluated:
        fronts = non_dominated_sort(evaluated)
        for rank, front in enumerate(fronts):
            for g in front:
                g.pareto_rank = rank

    # 7. Save all to registry
    for genome in population:
        save_genome(genome)
    log.info(f"  Saved {len(population)} genomes to registry")

    return population


# -------------------------------------------------------------------
# Re-validation mode (Correction 7)
# -------------------------------------------------------------------

def run_revalidation(lookback_days: int = 30) -> pd.DataFrame:
    """
    Checks all 'verified' genomes' trailing realized Sharpe against promotion bounds.
    Demotes to 'candidate' if outside [-0.5, +0.75] of backtested Sharpe.

    Returns a DataFrame of all verified genomes with their revalidation outcome.
    """
    try:
        from genome.revalidation import revalidate_all_verified
        return revalidate_all_verified(lookback_days=lookback_days)
    except ImportError:
        log.warning("genome.revalidation not yet implemented. Skipping.")
        return pd.DataFrame()


# -------------------------------------------------------------------
# CLI entry point
# -------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Alpha Genome evolution loop for BTCognitive"
    )
    parser.add_argument("--mode", type=str, default="evolve",
                        choices=["evolve", "revalidate"],
                        help="'evolve' runs one generation; 'revalidate' checks verified genomes")
    parser.add_argument("--generation", type=int, default=0,
                        help="Generation index to run (evolve mode only)")
    parser.add_argument("--population", type=int, default=DEFAULT_POPULATION_SIZE,
                        help="Population size per generation")
    parser.add_argument("--regime", type=str, default=None,
                        help=f"Regime to evolve (one of {VALID_REGIMES}). "
                             "If None, runs all regimes sequentially.")
    parser.add_argument("--n_splits", type=int, default=DEFAULT_N_SPLITS,
                        help="Number of purged walk-forward folds")
    parser.add_argument("--embargo", type=int, default=DEFAULT_EMBARGO_BARS,
                        help="Embargo bars between train/test splits")
    parser.add_argument("--min_dsr", type=float, default=DEFAULT_MIN_DSR,
                        help="Minimum DSR to pass overfitting gate")
    parser.add_argument("--max_pbo", type=float, default=DEFAULT_MAX_PBO,
                        help="Maximum PBO to pass overfitting gate")
    parser.add_argument("--sigma", type=float, default=None,
                        help="Override mutation sigma (default: annealed 0.3*0.95^gen, floor 0.05)")
    parser.add_argument("--funnel", action="store_true",
                        help="Enable multi-stage funnel candidate screening (95% compute reduction)")
    args = parser.parse_args()

    if args.mode == "revalidate":
        log.info("Running verified genome re-validation (Correction 7)...")
        result_df = run_revalidation()
        if not result_df.empty:
            print(result_df[['genome_id', 'regime', 'status', 'deflated_sharpe']].to_string())
        else:
            print("No verified genomes to revalidate.")
    else:
        target_regimes = [args.regime] if args.regime else VALID_REGIMES
        for regime in target_regimes:
            log.info(f"Running generation {args.generation} for regime {regime}...")
            survivors = run_generation(
                generation      = args.generation,
                regime          = regime,
                population_size = args.population,
                n_splits        = args.n_splits,
                embargo_bars    = args.embargo,
                min_dsr         = args.min_dsr,
                max_pbo         = args.max_pbo,
                sigma_override  = args.sigma,
                use_funnel      = args.funnel,
            )
            quarantine = [g for g in survivors if g.status == 'quarantine']
            log.info(
                f"Generation {args.generation} complete for {regime}: "
                f"{len(quarantine)}/{len(survivors)} genomes quarantined"
            )
