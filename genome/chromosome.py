"""
genome/chromosome.py — Genome Dataclass & Genetic Operations

Defines the Genome data structure for BTCognitive's Alpha Genome subsystem.
Each Genome encodes a regime-specific exit/risk policy (TP, SL, hold time,
position sizing method). Entry direction is NEVER encoded here — that remains
owned by AdaptiveRegimeEnsemble in models/ensemble.py.

Genetic operations (mutate, crossover) are immutable: they always return a
new Genome object and never modify the original.
"""

import os
import sys
import json
import uuid
import random
import math
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

VALID_REGIMES = [
    'TRENDING_BULL',
    'TRENDING_BEAR',
    'RANGING',
    'BREAKOUT',
    'HIGH_VOLATILITY',
]

VALID_PSM = ['fixed', 'vol_target', 'prob_scaled']  # position_size_method choices

# Gene valid ranges (inclusive)
TP_ATR_MULT_RANGE   = (1.0, 5.0)
SL_ATR_MULT_RANGE   = (0.5, 3.0)
MAX_HOLD_BARS_RANGE = (4, 96)

# Mutation defaults
DEFAULT_MUTATION_SIGMA = 0.25   # continuous gene Gaussian std (shrinks each generation)
PSM_MUTATION_PROB      = 0.10   # probability of reassigning position_size_method per mutation


# -------------------------------------------------------------------
# Genome Dataclass
# -------------------------------------------------------------------

@dataclass
class Genome:
    """
    Encodes a regime-specific exit/risk policy for BTCognitive's Alpha Genome.

    Fields are split into two groups:
      - Gene fields (set at creation / by mutation / crossover)
      - Fitness fields (populated after evaluate_genome() runs, default to NaN)

    Immutability rule: mutate() and crossover() always return NEW Genome objects.
    Never modify a Genome in place after it has been saved to the registry.
    """

    # Identity
    genome_id:            str
    generation:           int
    parent_ids:           List[str]   # empty list [] for generation-0 seeds

    # Gene fields
    regime:               str         # one of VALID_REGIMES
    tp_atr_mult:          float       # TP = entry_price * (1 + tp_atr_mult * ATR)
    sl_atr_mult:          float       # SL = entry_price * (1 - sl_atr_mult * ATR)
    max_hold_bars:        int         # force-close position after this many bars
    position_size_method: str         # one of VALID_PSM

    # Lineage / audit
    mutation_log:         List[str]   # human-readable per-mutation descriptions
    born_at:              str         # ISO UTC string

    # Fitness fields (populated by fitness.evaluate_genome)
    sharpe:               float = float('nan')
    calmar:               float = float('nan')
    max_drawdown:         float = float('nan')
    win_rate:             float = float('nan')
    turnover:             float = float('nan')

    # Post-selection metadata (populated by population.run_generation)
    pareto_rank:          int   = 999
    deflated_sharpe:      float = float('nan')
    pbo_generation:       float = float('nan')

    # Lifecycle status
    status:               str   = 'candidate'  # candidate | quarantine | verified | dead


# -------------------------------------------------------------------
# Construction helpers
# -------------------------------------------------------------------

def _new_id() -> str:
    """Returns a short unique genome ID."""
    return str(uuid.uuid4())[:8]


def _now_utc() -> str:
    """Returns current UTC time as an ISO string."""
    return datetime.now(timezone.utc).isoformat()


def random_genome(regime: str, generation: int = 0) -> Genome:
    """
    Creates a uniformly random generation-0 seed Genome for the given regime.

    Args:
        regime:     One of VALID_REGIMES.
        generation: Generation index (0 for initial seeds).

    Returns:
        A new Genome with all genes sampled uniformly within valid ranges.
    """
    if regime not in VALID_REGIMES:
        raise ValueError(f"Invalid regime '{regime}'. Must be one of {VALID_REGIMES}")

    return Genome(
        genome_id            = _new_id(),
        generation           = generation,
        parent_ids           = [],
        regime               = regime,
        tp_atr_mult          = random.uniform(*TP_ATR_MULT_RANGE),
        sl_atr_mult          = random.uniform(*SL_ATR_MULT_RANGE),
        max_hold_bars        = random.randint(*MAX_HOLD_BARS_RANGE),
        position_size_method = random.choice(VALID_PSM),
        mutation_log         = [f"seed_gen{generation}"],
        born_at              = _now_utc(),
    )


# -------------------------------------------------------------------
# Mutation
# -------------------------------------------------------------------

def mutate(g: Genome, sigma_continuous: float = DEFAULT_MUTATION_SIGMA) -> Genome:
    """
    Returns a NEW Genome derived from g by applying random perturbations.
    Never modifies g in place — full immutability for safe lineage tracking.

    Mutation rules:
      - tp_atr_mult, sl_atr_mult: add Gaussian noise N(0, sigma_continuous),
        clip to valid range.
      - max_hold_bars: add uniform integer noise in [-4, +4], clip to [4, 96].
      - position_size_method: 10% chance of random reassignment.

    sigma_continuous should be reduced each generation by the caller (annealing):
      sigma = DEFAULT_MUTATION_SIGMA * (0.95 ** generation)
    This ensures early generations explore broadly and later generations fine-tune.

    Args:
        g:                Genome to derive from (unchanged).
        sigma_continuous: Std dev for Gaussian perturbation of float genes.

    Returns:
        A new Genome with parent_ids=[g.genome_id] and updated mutation_log.
    """
    log_entries = []

    # --- tp_atr_mult ---
    new_tp = g.tp_atr_mult + random.gauss(0, sigma_continuous)
    new_tp = float(max(TP_ATR_MULT_RANGE[0], min(TP_ATR_MULT_RANGE[1], new_tp)))
    if abs(new_tp - g.tp_atr_mult) > 1e-4:
        log_entries.append(f"tp_atr_mult {g.tp_atr_mult:.3f}→{new_tp:.3f}")

    # --- sl_atr_mult ---
    new_sl = g.sl_atr_mult + random.gauss(0, sigma_continuous)
    new_sl = float(max(SL_ATR_MULT_RANGE[0], min(SL_ATR_MULT_RANGE[1], new_sl)))
    if abs(new_sl - g.sl_atr_mult) > 1e-4:
        log_entries.append(f"sl_atr_mult {g.sl_atr_mult:.3f}→{new_sl:.3f}")

    # --- max_hold_bars ---
    delta_hold = random.randint(-4, 4)
    new_hold = int(max(MAX_HOLD_BARS_RANGE[0], min(MAX_HOLD_BARS_RANGE[1], g.max_hold_bars + delta_hold)))
    if new_hold != g.max_hold_bars:
        log_entries.append(f"max_hold_bars {g.max_hold_bars}→{new_hold}")

    # --- position_size_method ---
    new_psm = g.position_size_method
    if random.random() < PSM_MUTATION_PROB:
        new_psm = random.choice(VALID_PSM)
        if new_psm != g.position_size_method:
            log_entries.append(f"position_size_method {g.position_size_method}→{new_psm}")

    if not log_entries:
        log_entries.append("no_change")

    return Genome(
        genome_id            = _new_id(),
        generation           = g.generation + 1,
        parent_ids           = [g.genome_id],
        regime               = g.regime,
        tp_atr_mult          = new_tp,
        sl_atr_mult          = new_sl,
        max_hold_bars        = new_hold,
        position_size_method = new_psm,
        mutation_log         = g.mutation_log + log_entries,
        born_at              = _now_utc(),
    )


# -------------------------------------------------------------------
# Crossover
# -------------------------------------------------------------------

def crossover(a: Genome, b: Genome) -> Genome:
    """
    Single-point crossover: each gene is randomly inherited from parent a or b
    with equal probability (uniform crossover).

    Both parents must share the same regime — crossing regimes is undefined behaviour.

    Args:
        a: First parent Genome.
        b: Second parent Genome.

    Returns:
        A new child Genome with parent_ids=[a.genome_id, b.genome_id].

    Raises:
        ValueError: If parents have different regimes.
    """
    if a.regime != b.regime:
        raise ValueError(
            f"Cannot crossover genomes with different regimes: "
            f"'{a.regime}' vs '{b.regime}'"
        )

    def pick(gene_a, gene_b):
        return gene_a if random.random() < 0.5 else gene_b

    child_tp   = pick(a.tp_atr_mult, b.tp_atr_mult)
    child_sl   = pick(a.sl_atr_mult, b.sl_atr_mult)
    child_hold = pick(a.max_hold_bars, b.max_hold_bars)
    child_psm  = pick(a.position_size_method, b.position_size_method)

    return Genome(
        genome_id            = _new_id(),
        generation           = max(a.generation, b.generation) + 1,
        parent_ids           = [a.genome_id, b.genome_id],
        regime               = a.regime,
        tp_atr_mult          = child_tp,
        sl_atr_mult          = child_sl,
        max_hold_bars        = child_hold,
        position_size_method = child_psm,
        mutation_log         = [f"crossover({a.genome_id},{b.genome_id})"],
        born_at              = _now_utc(),
    )


# -------------------------------------------------------------------
# Serialization (flat dict ↔ Genome for SQLite storage)
# -------------------------------------------------------------------

def genome_to_dict(g: Genome) -> dict:
    """
    Serializes a Genome to a flat dict suitable for a SQLite INSERT / upsert.
    List fields (parent_ids, mutation_log) are JSON-encoded strings.
    """
    return {
        'genome_id':            g.genome_id,
        'generation':           g.generation,
        'parent_ids':           json.dumps(g.parent_ids),
        'regime':               g.regime,
        'tp_atr_mult':          g.tp_atr_mult,
        'sl_atr_mult':          g.sl_atr_mult,
        'max_hold_bars':        g.max_hold_bars,
        'position_size_method': g.position_size_method,
        'mutation_log':         json.dumps(g.mutation_log),
        'born_at':              g.born_at,
        'sharpe':               g.sharpe,
        'calmar':               g.calmar,
        'max_drawdown':         g.max_drawdown,
        'win_rate':             g.win_rate,
        'turnover':             g.turnover,
        'pareto_rank':          g.pareto_rank,
        'deflated_sharpe':      g.deflated_sharpe,
        'pbo_generation':       g.pbo_generation,
        'status':               g.status,
    }


def genome_from_dict(d: dict) -> Genome:
    """
    Deserializes a Genome from a flat dict (e.g. a SQLite row converted to dict).
    Handles JSON-decoding of list fields and missing fitness fields (defaults to NaN).
    """
    def _float(v):
        try:
            f = float(v)
            return f if not (f != f) else float('nan')  # re-nan check
        except (TypeError, ValueError):
            return float('nan')

    def _int(v, default):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    parent_ids = d.get('parent_ids', '[]')
    if isinstance(parent_ids, str):
        parent_ids = json.loads(parent_ids)

    mutation_log = d.get('mutation_log', '[]')
    if isinstance(mutation_log, str):
        mutation_log = json.loads(mutation_log)

    return Genome(
        genome_id            = str(d['genome_id']),
        generation           = _int(d.get('generation', 0), 0),
        parent_ids           = parent_ids,
        regime               = str(d.get('regime', '')),
        tp_atr_mult          = _float(d.get('tp_atr_mult', 2.0)),
        sl_atr_mult          = _float(d.get('sl_atr_mult', 1.0)),
        max_hold_bars        = _int(d.get('max_hold_bars', 24), 24),
        position_size_method = str(d.get('position_size_method', 'prob_scaled')),
        mutation_log         = mutation_log,
        born_at              = str(d.get('born_at', '')),
        sharpe               = _float(d.get('sharpe')),
        calmar               = _float(d.get('calmar')),
        max_drawdown         = _float(d.get('max_drawdown')),
        win_rate             = _float(d.get('win_rate')),
        turnover             = _float(d.get('turnover')),
        pareto_rank          = _int(d.get('pareto_rank', 999), 999),
        deflated_sharpe      = _float(d.get('deflated_sharpe')),
        pbo_generation       = _float(d.get('pbo_generation')),
        status               = str(d.get('status', 'candidate')),
    )


# -------------------------------------------------------------------
# Smoke test
# -------------------------------------------------------------------

if __name__ == "__main__":
    import math
    errors = []

    # 1. Random genome creation for every regime
    seeds = []
    for regime in VALID_REGIMES:
        g = random_genome(regime, generation=0)
        seeds.append(g)
        in_tp   = TP_ATR_MULT_RANGE[0] <= g.tp_atr_mult <= TP_ATR_MULT_RANGE[1]
        in_sl   = SL_ATR_MULT_RANGE[0] <= g.sl_atr_mult <= SL_ATR_MULT_RANGE[1]
        in_hold = MAX_HOLD_BARS_RANGE[0] <= g.max_hold_bars <= MAX_HOLD_BARS_RANGE[1]
        in_psm  = g.position_size_method in VALID_PSM
        if not (in_tp and in_sl and in_hold and in_psm):
            errors.append(f"FAIL: random_genome for {regime} out of range")

    print(f"Created {len(seeds)} seed genomes — {'PASS' if not errors else 'FAIL'}")

    # 2. Mutate two genomes, check immutability and ranges
    original_id = seeds[0].genome_id
    mutated = mutate(seeds[0], sigma_continuous=0.3)
    if mutated.genome_id == original_id:
        errors.append("FAIL: mutate() returned same genome_id")
    if seeds[0].genome_id != original_id:
        errors.append("FAIL: mutate() modified original genome")
    if mutated.parent_ids != [original_id]:
        errors.append("FAIL: mutated genome parent_ids incorrect")
    in_tp   = TP_ATR_MULT_RANGE[0] <= mutated.tp_atr_mult <= TP_ATR_MULT_RANGE[1]
    in_sl   = SL_ATR_MULT_RANGE[0] <= mutated.sl_atr_mult <= SL_ATR_MULT_RANGE[1]
    in_hold = MAX_HOLD_BARS_RANGE[0] <= mutated.max_hold_bars <= MAX_HOLD_BARS_RANGE[1]
    if not (in_tp and in_sl and in_hold):
        errors.append("FAIL: mutated genome genes out of range")
    print(f"Mutation immutability + range check — {'PASS' if not errors else 'FAIL: ' + str(errors)}")

    # 3. Crossover — use two TRENDING_BULL seeds (same regime)
    g_a = random_genome('TRENDING_BULL', generation=0)
    g_b = random_genome('TRENDING_BULL', generation=1)
    child = crossover(g_a, g_b)
    if set(child.parent_ids) != {g_a.genome_id, g_b.genome_id}:
        errors.append("FAIL: crossover parent_ids incorrect")
    if child.regime != g_a.regime:
        errors.append("FAIL: crossover changed regime")
    print(f"Crossover parent_ids + regime — {'PASS' if not errors else 'FAIL: ' + str(errors)}")

    # 4. Cross-regime crossover should raise (TRENDING_BULL vs RANGING)
    try:
        crossover(g_a, seeds[2])  # TRENDING_BULL vs RANGING
        errors.append("FAIL: crossover should raise on different regimes")
    except ValueError:
        pass
    print(f"Cross-regime crossover ValueError — PASS")

    # 5. Serialization round-trip
    original = seeds[0]
    d = genome_to_dict(original)
    restored = genome_from_dict(d)
    if restored.genome_id != original.genome_id:
        errors.append("FAIL: genome_id mismatch after round-trip")
    if abs(restored.tp_atr_mult - original.tp_atr_mult) > 1e-9:
        errors.append("FAIL: tp_atr_mult mismatch after round-trip")
    if restored.parent_ids != original.parent_ids:
        errors.append("FAIL: parent_ids mismatch after round-trip")
    print(f"Serialization round-trip — {'PASS' if not errors else 'FAIL'}")

    # 6. Genome ID uniqueness across 50 random genomes
    ids = [random_genome('TRENDING_BULL').genome_id for _ in range(50)]
    if len(set(ids)) != 50:
        errors.append("FAIL: genome_id collision detected")
    print(f"Genome ID uniqueness (50 samples) — {'PASS' if len(set(ids)) == 50 else 'FAIL'}")

    # Summary
    if not errors:
        print("\nPASS: All chromosome.py smoke checks passed.")
    else:
        print(f"\nFAIL: {len(errors)} check(s) failed:")
        for e in errors:
            print(f"  {e}")
