"""
api/genome_routes.py -- Read-Only FastAPI Endpoints for Alpha Genome

Exposes the genome registry to the frontend and monitoring tools.
ALL endpoints are read-only GET requests -- no mutations.
Evolution runs exclusively via the CLI: python genome/population.py --generation N

Endpoints:
  GET /genome/leaderboard            -- Top verified/quarantine genomes by deflated Sharpe
  GET /genome/latest_generation      -- Info about the most recent generation in the registry
  GET /genome/{genome_id}            -- Single genome detail by ID
  GET /genome/{genome_id}/lineage    -- Ancestor chain for a genome
  GET /genome/{genome_id}/quarantine -- Shadow quarantine trades for a genome

Response schema note (Correction 6/plan): deflated_sharpe and pbo_generation are
always included in genome responses alongside raw sharpe, so the API never presents
raw Sharpe alone without its statistical correction context.
"""

import math
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from genome.registry import (
    load_leaderboard,
    load_genome,
    get_lineage,
    load_quarantine_trades,
    get_latest_generation,
    load_generation,
)


router = APIRouter(prefix="/genome", tags=["genome"])


# -------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------

def _nan_to_null(v):
    """Convert Python NaN/Inf to None for JSON serialisation."""
    if isinstance(v, float) and (not math.isfinite(v)):
        return None
    return v


def _genome_to_response(g) -> dict:
    """
    Converts a Genome object to a JSON-safe dict.
    NaN fitness values are returned as null (not as the string 'nan').
    Includes both raw sharpe and deflated_sharpe for transparency.
    """
    return {
        'genome_id':            g.genome_id,
        'generation':           g.generation,
        'parent_ids':           g.parent_ids,
        'regime':               g.regime,
        'genes': {
            'tp_atr_mult':          round(g.tp_atr_mult, 4),
            'sl_atr_mult':          round(g.sl_atr_mult, 4),
            'max_hold_bars':        g.max_hold_bars,
            'position_size_method': g.position_size_method,
        },
        'fitness': {
            'sharpe':          _nan_to_null(g.sharpe),
            'calmar':          _nan_to_null(g.calmar),
            'max_drawdown':    _nan_to_null(g.max_drawdown),
            'win_rate':        _nan_to_null(g.win_rate),
            'turnover':        _nan_to_null(g.turnover),
        },
        'statistics': {
            'deflated_sharpe': _nan_to_null(g.deflated_sharpe),
            'pbo_generation':  _nan_to_null(g.pbo_generation),
            'pareto_rank':     g.pareto_rank,
        },
        'status':               g.status,
        'born_at':              g.born_at,
        'mutation_log':         g.mutation_log,
    }


# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------

@router.get("/leaderboard")
def get_leaderboard(
    status: str = "verified",
    limit: int = 20,
):
    """
    Returns the top genomes sorted by deflated_sharpe descending.

    Returns an empty list if no genomes with the given status exist (not a 404).
    DSR and PBO are included alongside raw Sharpe so consumers can see the
    statistical context, not just the headline number.
    """
    try:
        df = load_leaderboard(status=status, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Registry error: {exc}")

    if df.empty:
        return []

    # Parse genome rows from DataFrame back to response dicts
    result = []
    for _, row in df.iterrows():
        result.append({
            'genome_id':       row['genome_id'],
            'generation':      int(row['generation']),
            'regime':          row['regime'],
            'status':          row['status'],
            'fitness': {
                'sharpe':      _nan_to_null(row['sharpe']),
                'calmar':      _nan_to_null(row['calmar']),
                'max_drawdown': _nan_to_null(row['max_drawdown']),
                'win_rate':    _nan_to_null(row['win_rate']),
            },
            'statistics': {
                'deflated_sharpe': _nan_to_null(row['deflated_sharpe']),
                'pbo_generation':  _nan_to_null(row['pbo_generation']),
                'pareto_rank':     int(row['pareto_rank']),
            },
            'genes': {
                'tp_atr_mult':          round(float(row['tp_atr_mult']), 4),
                'sl_atr_mult':          round(float(row['sl_atr_mult']), 4),
                'max_hold_bars':        int(row['max_hold_bars']),
                'position_size_method': row['position_size_method'],
            },
            'born_at': row['born_at'],
        })
    return result


@router.get("/latest_generation")
def get_latest_gen_info():
    """
    Returns the latest generation number and count of genomes per regime and status.
    Useful for monitoring evolution progress without loading all genome data.
    """
    try:
        latest = get_latest_generation()
        if latest < 0:
            return {"latest_generation": -1, "message": "Registry is empty. Run evolution first."}

        population = load_generation(latest)
        by_regime  = {}
        by_status  = {}
        for g in population:
            by_regime[g.regime]  = by_regime.get(g.regime, 0) + 1
            by_status[g.status]  = by_status.get(g.status, 0) + 1

        return {
            "latest_generation": latest,
            "population_size":   len(population),
            "by_regime":         by_regime,
            "by_status":         by_status,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Registry error: {exc}")


@router.get("/{genome_id}")
def get_genome(genome_id: str):
    """
    Returns full detail for a single genome by ID.
    Returns 404 if the genome does not exist.
    """
    try:
        g = load_genome(genome_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Registry error: {exc}")

    if g is None:
        raise HTTPException(status_code=404, detail=f"Genome '{genome_id}' not found")

    return _genome_to_response(g)


@router.get("/{genome_id}/lineage")
def get_genome_lineage(genome_id: str, depth: int = 5):
    """
    Returns the ancestor chain for a genome, ordered oldest-to-newest.
    Returns an empty list if the genome doesn't exist (not a 404 -- lineage may be partial).
    """
    try:
        chain = get_lineage(genome_id, depth=depth)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Registry error: {exc}")

    return [
        {
            'genome_id':   entry['genome_id'],
            'generation':  entry['generation'],
            'regime':      entry['regime'],
            'status':      entry['status'],
            'sharpe':      _nan_to_null(entry['sharpe']),
            'deflated_sharpe': _nan_to_null(entry['deflated_sharpe']),
            'mutation_log': entry['mutation_log'],
        }
        for entry in chain
    ]


@router.get("/{genome_id}/quarantine")
def get_quarantine_trades(genome_id: str):
    """
    Returns the shadow quarantine trades logged for a genome.
    Returns an empty list if no trades have been logged yet.
    """
    try:
        df = load_quarantine_trades(genome_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Registry error: {exc}")

    if df.empty:
        return []

    return df.to_dict(orient='records')
