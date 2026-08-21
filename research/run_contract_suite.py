"""
research/run_contract_suite.py — Master Contract & Rebaseline Test Suite Runner
==============================================================================
Runs all 26 unit and integration test suites:
1. Regime Contract
2. Regime Runtime Path
3. Market Memory Path
4. Horizon Contract
5. Symbol Contract
6. Unresolved Outcomes & was_correct NULL Invariant
7. Master System Contracts Suite
8. Post-Repair Boundary Tests
9. Post-Repair Blocks Tests
10. Post-Repair Metrics Tests
11. Post-Repair Restart Gate Tests
12. Pre/Post Separation Integrity
13. Hawkes Shadow Post-Migration Verification
14. Post-Repair Monitoring Engine
15. Post-Repair 5-Block Milestone Gate
16. Post-Repair Milestone Sequence Integrity
17. Post-Repair Live Production Smoke Test
18. Forecast Quality Contract
19. Degraded Forecast Monitor
20. Block Quality Stratification
21. Valid 5-Block Milestone Gate
22. Post-Repair Outcome Resolver
23. Outcome Point-In-Time Windows
24. Block Completion Integrity
25. Resolution Database Integrity
26. Resolution Health API Payload
"""

import sys
import os
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests import test_regime_contract
from tests import test_regime_runtime_path
from tests import test_market_memory_path
from tests import test_horizon_contract
from tests import test_symbol_contract
from tests import test_unresolved_outcomes
from tests import test_system_contracts
from tests import test_post_repair_boundary
from tests import test_post_repair_blocks
from tests import test_post_repair_metrics
from tests import test_post_repair_restart
from tests import test_pre_post_separation
from tests import test_hawkes_post_migration
from tests import test_post_repair_monitoring
from tests import test_post_repair_5_block_gate
from tests import test_post_repair_milestone_integrity
from tests import test_post_repair_live_smoke
from tests import test_forecast_quality_contract
from tests import test_degraded_forecast_monitor
from tests import test_block_quality
from tests import test_valid_5_block_gate
from tests import test_post_repair_outcome_resolver
from tests import test_outcome_point_in_time
from tests import test_block_completion
from tests import test_resolution_integrity
from tests import test_resolution_health

TEST_MODULES = [
    ("1. Regime Contract Tests", test_regime_contract),
    ("2. Regime Runtime Path Tests", test_regime_runtime_path),
    ("3. Market Memory Path Tests", test_market_memory_path),
    ("4. Horizon Contract Tests", test_horizon_contract),
    ("5. Symbol Contract Tests", test_symbol_contract),
    ("6. Unresolved Outcomes Tests", test_unresolved_outcomes),
    ("7. Master System Contracts Suite", test_system_contracts),
    ("8. Post-Repair Boundary Tests", test_post_repair_boundary),
    ("9. Post-Repair Blocks Tests", test_post_repair_blocks),
    ("10. Post-Repair Metrics Tests", test_post_repair_metrics),
    ("11. Post-Repair Restart Gate Tests", test_post_repair_restart),
    ("12. Pre/Post Separation Tests", test_pre_post_separation),
    ("13. Hawkes Post-Migration Tests", test_hawkes_post_migration),
    ("14. Post-Repair Monitoring Tests", test_post_repair_monitoring),
    ("15. Post-Repair 5-Block Gate Tests", test_post_repair_5_block_gate),
    ("16. Post-Repair Milestone Integrity Tests", test_post_repair_milestone_integrity),
    ("17. Post-Repair Live Smoke Tests", test_post_repair_live_smoke),
    ("18. Forecast Quality Contract Tests", test_forecast_quality_contract),
    ("19. Degraded Forecast Monitor Tests", test_degraded_forecast_monitor),
    ("20. Block Quality Tests", test_block_quality),
    ("21. Valid 5-Block Gate Tests", test_valid_5_block_gate),
    ("22. Outcome Resolver Tests", test_post_repair_outcome_resolver),
    ("23. Outcome Point-In-Time Tests", test_outcome_point_in_time),
    ("24. Block Completion Tests", test_block_completion),
    ("25. Resolution Integrity Tests", test_resolution_integrity),
    ("26. Resolution Health Tests", test_resolution_health),
]

def run_all_tests():
    total_run = 0
    total_passed = 0
    failures = []

    print("=" * 70)
    print("  BTCognitive — MASTER SYSTEM & REBASELINE TEST SUITE (26 SUITES)")
    print("=" * 70)

    for mod_name, mod in TEST_MODULES:
        print(f"\n>> Running: {mod_name}")
        test_funcs = [getattr(mod, name) for name in dir(mod) if name.startswith("test_") and callable(getattr(mod, name))]
        for fn in test_funcs:
            total_run += 1
            fn_name = fn.__name__
            try:
                fn()
                total_passed += 1
                print(f"   [PASS] {fn_name}")
            except Exception as e:
                failures.append((mod_name, fn_name, str(e), traceback.format_exc()))
                print(f"   [FAIL] {fn_name}: {e}")

    print("\n" + "=" * 70)
    print(f"  RESULTS: {total_passed} / {total_run} passed.")
    if failures:
        print(f"  FAILURES: {len(failures)}")
        for m, f, err, tb in failures:
            print(f"\n--- Failure in {m} -> {f} ---")
            print(err)
            print(tb)
        return False
    else:
        print("  ALL 26 TEST SUITES PASSED PERFECTLY (100% GREEN).")
        print("=" * 70)
        return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
