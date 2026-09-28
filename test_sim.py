"""Quick test of fleet_sim."""
import sys
sys.path.insert(0, '.')
from src.fleet_sim import load_config, FleetSimulation

cfg = load_config('config/fleet_config.yaml')
sim = FleetSimulation(cfg, 'Dongri_Buzurg', mine_tpd=877)

print(f"Fleet: {sim.num_ore_dumpers} ore + {sim.num_waste_dumpers} waste = {sim.num_dumpers} dumpers")
print(f"Shovels: {sim.num_shovels}")
print(f"Ore cycle: {sim.ore_cycle_min:.1f} min, TPH: {sim.ore_tph:.1f}")
print(f"Waste cycle: {sim.waste_cycle_min:.1f} min, TPH: {sim.waste_tph:.1f}")
print(f"Shift: {sim.shift_hours} hours = {sim.shift_hours * 60} min")
print()

# Run single shift
r = sim.simulate_shift(strategy='or_tools', seed=42)
print(f"Ore tonnes/shift: {r['ore_tonnes']:.0f}")
print(f"Waste tonnes/shift: {r['waste_tonnes']:.0f}")
print(f"Total trips: {r['total_trips']}")
print(f"Avg queue time: {r['avg_queue_time']:.1f} min")
print(f"Avg utilisation: {r['avg_utilisation']:.1f}%")
print(f"Shovel utilisation: {r['shovel_utilisation']}")
print()

if not r['dumper_logs'].empty:
    print("Dumper logs:")
    print(r['dumper_logs'].to_string(index=False))
else:
    print("WARNING: No dumper logs generated!")
