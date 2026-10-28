"""Stable project paths and scientific implementation fingerprints."""
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULES = {'simulation': 'simulation', 'bead_analysis': 'measurements.bead_analysis', 'signal_switch': 'measurements.signal_switch', 'transistor_measurements': 'measurements.transistor', 'optimisation': 'optimisation', 'experiments': 'experiments.computing', 'diagnose_switch': 'experiments.diagnose_switch', 'disorder': 'experiments.disorder', 'diode_characterisation': 'experiments.diode', 'larger_switch': 'experiments.larger_switch', 'run_offset_search': 'experiments.offset_search', 'run_signal_switch': 'experiments.signal_switch', 'sweep_switch_drive': 'experiments.drive_sweep', 'switch_cycles': 'experiments.switch_cycles', 'switch_load': 'experiments.switch_load', 'control_nonlinearity': 'experiments.control_nonlinearity', 'control_nonlinearity_plots': 'reporting.control_nonlinearity', 'run_transistor': 'experiments.legacy_transistor', 'run_transistor_suite': 'experiments.transistor', 'transistor': 'objectives.legacy', 'transistor_device': 'objectives.device', 'transistor_fast': 'objectives.fast', 'transistor_reports': 'reporting.transistor'}
def code_path(name):
    stem = Path(name).stem
    return PROJECT_ROOT / 'rowerlib' / (MODULES[stem].replace('.', '/') + '.py')
