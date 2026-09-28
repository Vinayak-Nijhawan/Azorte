import os
import sys
import pytest

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.fleet_sim import FleetSimulation, load_config as load_oc_config
from src.underground_sim import UndergroundSimulation, load_config as load_ug_config

def test_opencast_ortools_vs_greedy():
    """Verify OR-Tools dispatch produces different results than Greedy dispatch."""
    cfg = load_oc_config()
    # Dongri Buzurg, 5000 TPD target
    sim = FleetSimulation(cfg, 'Dongri_Buzurg', mine_tpd=5000.0)
    
    # Run identical seeds for both
    res_greedy = sim.simulate_shift(strategy='greedy', seed=42)
    res_ortools = sim.simulate_shift(strategy='or_tools', seed=42)
    
    # Check that they differ (at least in queue time or trips)
    # They should differ because OR-Tools balances queues better
    assert res_greedy['avg_queue_time'] != res_ortools['avg_queue_time'] or res_greedy['total_trips'] != res_ortools['total_trips'], "OR-Tools result equals greedy result!"

def test_opencast_demand_limit():
    """Verify simulation respects demand limits."""
    cfg = load_oc_config()
    target_tpd = 5000.0
    sim = FleetSimulation(cfg, 'Dongri_Buzurg', mine_tpd=target_tpd)
    
    res = sim.simulate_shift(strategy='or_tools', seed=42)
    achieved_tpd = res['ore_tonnes'] * sim.shifts_per_day
    
    limit = target_tpd * 1.05
    assert achieved_tpd <= limit, f"Achieved TPD ({achieved_tpd}) exceeds target limit ({limit})"

def test_underground_demand_limit():
    """Verify underground simulation respects demand limits."""
    cfg = load_ug_config()
    target_tpd = 2000.0
    sim = UndergroundSimulation(cfg, 'Balaghat', mine_tpd=target_tpd)
    
    res = sim.simulate_shift(strategy='cp_sat', seed=42)
    achieved_tpd = res['tonnes_hoisted'] * sim.shifts_per_day
    
    limit = target_tpd * 1.05
    assert achieved_tpd <= limit, f"Achieved TPD ({achieved_tpd}) exceeds target limit ({limit})"

def test_fleet_validation_logic():
    """Test the validation function directly."""
    cfg = load_oc_config()
    sim = FleetSimulation(cfg, 'Dongri_Buzurg', mine_tpd=5000.0)
    
    # Fake result passing limits
    res_pass = {
        'ore_tonnes': 5000 / sim.shifts_per_day,
        'avg_utilisation': 80.0
    }
    checks = sim.validate(res_pass)
    assert all(c[0] == 'PASS' for c in checks)
    
    # Fake result failing limits
    res_fail = {
        'ore_tonnes': 8000 / sim.shifts_per_day,
        'avg_utilisation': 99.0
    }
    checks = sim.validate(res_fail)
    status_list = [c[0] for c in checks]
    assert 'FAIL' in status_list
    assert 'WARN' in status_list
