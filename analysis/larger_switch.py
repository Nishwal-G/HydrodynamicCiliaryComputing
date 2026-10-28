"""Compatibility entry point. Prefer python rowers.py --help."""
from pathlib import Path
import importlib
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_impl = importlib.import_module('rowerlib.experiments.larger_switch')
if __name__ == '__main__':
    if hasattr(_impl, 'main'):
        _impl.main()
else:
    sys.modules[__name__] = _impl
