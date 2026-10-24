"""
research/first_passage_diffusion_model.py — Geometry-Aware First-Passage Diffusion Engine
========================================================================================
Replaces geometry-blind ad-hoc logistic formula with an analytical / PDE-calibrated
double-barrier first-passage diffusion baseline that natively depends on:
  - k_tp : Upper profit barrier multiplier
  - k_sl : Lower stop-loss barrier multiplier
  - H    : Trade horizon in hours
  - mu_t : Normalized drift parameter driven by causal market features (momentum, order flow)

Kolmogorov Backward Equation for Finite-Horizon Double Barrier:
  u_t = 0.5 * u_xx + mu * u_x on (-k_sl, k_tp)
  u(-k_sl, t) = 0,  u(k_tp, t) = 1,  u(x, 0) = 0 for x < k_tp
Dimensionless time T = 1.0 (standardized by sigma_H = sigma_1h * sqrt(H)).

Under zero drift (mu = 0, empirical null):
  P(TP first), P(SL first), and P(Timeout) are uniquely determined by geometry!
Under causal drift (mu_t = beta^T X_t):
  Probabilities shift continuously, coherently preserving P(TP) + P(SL) + P(TO) == 1.0.
"""

import math
from typing import Dict, Any, Tuple, Optional
import numpy as np
import scipy.linalg as la


class FirstPassageDiffusionModel:
    """
    Computes first-passage hitting probabilities for double barriers under Brownian motion with drift.
    """

    def __init__(self, nx: int = 150, nt: int = 250):
        self.nx = nx
        self.nt = nt
        self._cache: Dict[Tuple[float, float, float], Tuple[float, float, float]] = {}

    def solve_pde(
        self, k_tp: float, k_sl: float, mu: float = 0.0, c_sigma: float = 1.0
    ) -> Tuple[float, float, float]:
        """
        Solves Kolmogorov backward PDE to calculate:
        - P(TP first before H)
        - P(SL first before H)
        - P(Timeout) = 1.0 - P(TP) - P(SL)
        
        Args:
            k_tp: Upper profit barrier multiplier
            k_sl: Lower stop-loss barrier multiplier
            mu: Normalized drift parameter
            c_sigma: Empirical jump/fat-tail volatility scale factor (effective barrier k' = k / c_sigma).
                     Default is 1.0 (pure Gaussian diffusion); empirical BTC calibration is ~1.05-1.32.
        """
        # Scale barriers by empirical kurtosis / jump scale factor
        c_scale = max(0.1, float(c_sigma))
        k_tp_eff = k_tp / c_scale
        k_sl_eff = k_sl / c_scale

        # Quantize for caching
        cache_key = (round(k_tp_eff, 3), round(k_sl_eff, 3), round(mu, 3))
        if cache_key in self._cache:
            return self._cache[cache_key]

        a = max(0.1, float(k_sl_eff))
        b = max(0.1, float(k_tp_eff))
        L = a + b
        nx = self.nx
        nt = self.nt

        dx = L / float(nx)
        dt = 1.0 / float(nt)
        x0_idx = int(round(a / dx))

        # Solve for upper barrier hitting probability u(x, T=1) with u(b)=1, u(-a)=0
        r = 0.5 * dt / (dx ** 2)
        p = mu * dt / (2.0 * dx)

        # Crank-Nicolson tridiagonal matrices
        main_diag = np.full(nx - 1, 1.0 + r)
        lower_diag = np.full(nx - 2, -0.5 * (r - p))
        upper_diag = np.full(nx - 2, -0.5 * (r + p))

        ab = np.zeros((3, nx - 1))
        ab[0, 1:] = upper_diag
        ab[1, :] = main_diag
        ab[2, :-1] = lower_diag

        u = np.zeros(nx + 1)
        u[-1] = 1.0

        for _ in range(nt):
            rhs = 0.5 * (r - p) * u[:-2] + (1.0 - r) * u[1:-1] + 0.5 * (r + p) * u[2:]
            rhs[-1] += 0.5 * (r + p) * 1.0

            u_interior = la.solve_banded((1, 1), ab, rhs)
            u[1:nx] = u_interior
            u[0] = 0.0
            u[-1] = 1.0

        p_tp = float(np.clip(u[x0_idx], 0.0, 1.0))

        # By symmetry: lower barrier hitting probability with drift mu is equivalent
        # to upper barrier hitting probability with swapped barriers (a, b) and drift -mu.
        if abs(a - b) < 1e-4 and abs(mu) < 1e-4:
            p_sl = p_tp
        else:
            # Solve for lower barrier by reflection
            r_rev = 0.5 * dt / (dx ** 2)
            p_rev = (-mu) * dt / (2.0 * dx)
            main_diag_rev = np.full(nx - 1, 1.0 + r_rev)
            lower_diag_rev = np.full(nx - 2, -0.5 * (r_rev - p_rev))
            upper_diag_rev = np.full(nx - 2, -0.5 * (r_rev + p_rev))

            ab_rev = np.zeros((3, nx - 1))
            ab_rev[0, 1:] = upper_diag_rev
            ab_rev[1, :] = main_diag_rev
            ab_rev[2, :-1] = lower_diag_rev

            v = np.zeros(nx + 1)
            v[-1] = 1.0
            x0_rev_idx = int(round(b / dx))

            for _ in range(nt):
                rhs_rev = 0.5 * (r_rev - p_rev) * v[:-2] + (1.0 - r_rev) * v[1:-1] + 0.5 * (r_rev + p_rev) * v[2:]
                rhs_rev[-1] += 0.5 * (r_rev + p_rev) * 1.0

                v_int = la.solve_banded((1, 1), ab_rev, rhs_rev)
                v[1:nx] = v_int
                v[0] = 0.0
                v[-1] = 1.0

            p_sl = float(np.clip(v[x0_rev_idx], 0.0, 1.0))

        # Guarantee consistency: p_tp + p_sl <= 1.0
        if p_tp + p_sl > 0.999:
            tot = p_tp + p_sl
            p_tp = (p_tp / tot) * 0.999
            p_sl = (p_sl / tot) * 0.999

        p_timeout = max(0.0, 1.0 - p_tp - p_sl)

        res = (round(p_tp, 4), round(p_sl, 4), round(p_timeout, 4))
        self._cache[cache_key] = res
        return res

    def compute_excursion_expectancy_r(
        self,
        k_tp: float,
        k_sl: float,
        mu: float,
        friction_r: float = 0.0,
        c_sigma: float = 1.0,
    ) -> Dict[str, float]:
        """
        Computes expected return in units of R (stop distance):
        E[R_gross] = P(TP) * (k_tp / k_sl) - P(SL) * 1.0
        E[R_net] = E[R_gross] - friction_r
        """
        p_tp, p_sl, p_to = self.solve_pde(k_tp, k_sl, mu, c_sigma=c_sigma)
        r_mult = k_tp / k_sl
        ev_gross_r = p_tp * r_mult - p_sl * 1.0
        ev_net_r = ev_gross_r - friction_r
        return {
            "p_tp": p_tp,
            "p_sl": p_sl,
            "p_timeout": p_to,
            "reward_risk_ratio": round(r_mult, 2),
            "ev_gross_r": round(ev_gross_r, 4),
            "friction_r": round(friction_r, 4),
            "ev_net_r": round(ev_net_r, 4),
        }


if __name__ == "__main__":
    fp = FirstPassageDiffusionModel()
    print("Double Barrier First Passage under Brownian Motion:")
    for geom in [(1.5, 1.0), (1.0, 1.0), (0.9, 0.6), (1.05, 0.7)]:
        k_tp, k_sl = geom
        p_tp, p_sl, p_to = fp.solve_pde(k_tp, k_sl, 0.0)
        print(f"  Geom k_tp={k_tp}, k_sl={k_sl} (mu=0): P(TP)={p_tp*100:.1f}%, P(SL)={p_sl*100:.1f}%, P(TO)={p_to*100:.1f}%")

    print("\nDrift Sensitivity for (k_tp=1.5, k_sl=1.0):")
    for mu in [-0.5, -0.2, 0.0, +0.2, +0.5]:
        exp = fp.compute_excursion_expectancy_r(1.5, 1.0, mu, friction_r=0.16)
        print(f"  mu={mu:+.1f} -> P(TP)={exp['p_tp']*100:.1f}%, P(SL)={exp['p_sl']*100:.1f}%, P(TO)={exp['p_timeout']*100:.1f}%, EV_gross={exp['ev_gross_r']:+.3f}R, EV_net={exp['ev_net_r']:+.3f}R")
