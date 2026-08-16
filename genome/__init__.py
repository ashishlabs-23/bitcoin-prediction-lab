"""
genome/__init__.py -- Alpha Genome Package

Re-exports the key public API for the genome subsystem.
This keeps external imports clean:
  from genome import Genome, random_genome, mutate, crossover
  from genome import non_dominated_sort, select_next_generation
  from genome import deflated_sharpe_ratio, passes_overfitting_gate
  from genome import save_genome, load_genome, load_leaderboard
"""

from genome.chromosome import (
    Genome,
    VALID_REGIMES,
    VALID_PSM,
    random_genome,
    mutate,
    crossover,
    genome_to_dict,
    genome_from_dict,
)

from genome.pareto import (
    dominates,
    non_dominated_sort,
    select_next_generation,
)

from genome.overfitting import (
    deflated_sharpe_ratio,
    probability_of_backtest_overfitting,
    passes_overfitting_gate,
    DEFAULT_MIN_DSR,
    DEFAULT_MAX_PBO,
    MIN_TRADES_PER_SUBPERIOD,
)

from genome.registry import (
    get_registry_path,
    save_genome,
    load_genome,
    load_generation,
    load_leaderboard,
    get_latest_generation,
    record_quarantine_trade,
    load_quarantine_trades,
    get_lineage,
)

__all__ = [
    # chromosome
    'Genome', 'VALID_REGIMES', 'VALID_PSM',
    'random_genome', 'mutate', 'crossover',
    'genome_to_dict', 'genome_from_dict',
    # pareto
    'dominates', 'non_dominated_sort', 'select_next_generation',
    # overfitting
    'deflated_sharpe_ratio', 'probability_of_backtest_overfitting',
    'passes_overfitting_gate',
    'DEFAULT_MIN_DSR', 'DEFAULT_MAX_PBO', 'MIN_TRADES_PER_SUBPERIOD',
    # registry
    'get_registry_path', 'save_genome', 'load_genome', 'load_generation',
    'load_leaderboard', 'get_latest_generation',
    'record_quarantine_trade', 'load_quarantine_trades', 'get_lineage',
]
