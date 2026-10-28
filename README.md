# Ciliary Computing 

Run the project through **`python rowers.py`**. The C++ physics, existing objectives,
measurement definitions and experiment protocols are preserved. Python implementations
now live in `rowerlib/`; `analysis/` contains small compatibility entry points only.

**Existing results are not included or deleted. No optimisation or validation needs
repeating merely because the code has been reorganised.** Read
[Migration](docs/MIGRATION.md) before replacing an existing checkout.

## Install on Mac or Linux

From this project directory, use Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make -C src
python -m unittest discover -s tests -v
python rowers.py --help
```

The build requires a C++17 compiler, `make`, `curl` and `tar`; it downloads Eigen
3.4.0 on the first build. If the server cannot download Eigen, ask the lab administrator
to supply it at `src/eigen-3.4.0/`. Do not copy your Mac executable to Linux.
The existing Makefile uses `-march=native`: rebuild on a different machine rather
than assuming a binary is portable between blade1 and blade2.

Use the lab's scheduler if required. If direct jobs are allowed and `tmux` is installed:

```bash
tmux new -s rowers
source .venv/bin/activate
# Run the commands below in this session.
```

Detach with Ctrl+B then D; reconnect with `tmux attach -t rowers`.
Use the core allocation agreed with your lab, not every core visible on the server.
The examples use three workers. Store large results under your assigned `/data`
directory. Absolute `--work` paths are supported. Do not put passwords in scripts.

## New transistor experiment

Replace `PATH_TO_EXISTING_BEST.json` with a saved configuration or best.json. The
uploaded code did not include your results, so no optimised geometry is bundled.
All commands below run from the project root.

### 1. Prepare

```bash
python rowers.py prepare \
  --work results/device_7_run_001 \
  --config PATH_TO_EXISTING_BEST.json
```

Preparation writes one authoritative `experiment.json` containing the starting
configuration, search bounds, device protocol, fast objective settings, preparation
provenance and stage history. Review it before running. Templates are defaults, not
live controls for an already prepared experiment. Changing its settings later does
not retroactively change saved runs; use a new experiment when changing the design.

### 2. Baseline

```bash
python rowers.py baseline --work results/device_7_run_001 --runs 3 --cores 3
```

### 3. Optimise

```bash
python rowers.py optimise --work results/device_7_run_001 \
  --objective fast --iterations 300 --runs 5 --cores 3 \
  --search-temperature 0.05 --proposal-seed 42
```

`fast` is the default and retains the seven-simulation-per-repeat objective.
`--objective full` uses the existing comprehensive objective, including configured
phase, cycles and disorder terms. `--method bayesian` retains Bayesian optimisation;
Metropolis remains the default. Advanced Bayesian acquisition options remain available
through `optimise-advanced` (see below).

`--objective legacy --legacy-protocol FILE` selects the historical coherence objective
using its original protocol schema. Do not pass a device protocol as that legacy file.
The legacy path accepts common search options; use `optimise-advanced` for other options.

The winner is saved to `search/best.json` regardless of objective. Each checkpoint
records the objective. A new search requires a fresh output directory; **resume is not
implemented**. Starting with `--config OLD_SEARCH/best.json` starts a new search from
that configuration; it does not restore the old chain or RNG state.

### 4. Full validation

```bash
python rowers.py validate --work results/device_7_run_001 \
  --runs 50 --cores 3 --points 21 --dt-divisors 1 2
```

The recorded search winner is selected automatically. Validation always performs
transfer, phase intervention and repeated control cycles, plus the dense transfer
sweep. `dt1` uses the saved timestep; `dt2` halves it while retaining physical
sampling intervals. Validation can take much longer than the fast search.

Use `--runs 5 --out results/device_7_run_001/validation_pilot` for a small pilot before
a full run. Each output directory must be new. Training and validation seed overlap
is checked using checkpoint metadata. The usual validation seeds are held out from
training. An interrupted search's saved best can be validated, but is not a completed
search; `experiment.json` records interrupted/failed status when caught by the process.
Abrupt termination can leave the status at `running`; inspect the checkpoint/log.

### 5. Reports, without new simulations

```bash
python rowers.py report --work results/device_7_run_001
```

This creates `reports/` from the available `results.json`, `protocol.json`, map,
robustness and optional trace files. It creates transfer, phase and cycle reports,
baseline/timestep comparison curves and a CSV of measured transfer statistics.
No executable is required. It includes available partial batches; inspect sample
counts and `sources.json`. Comparisons are descriptive: confirm matching protocols,
windows and geometry before interpreting differences. Fast and full objective scores
are different quantities and are not combined.

To regenerate after more simulations finish, use a fresh output:

```bash
python rowers.py report --work results/device_7_run_001 \
  --out results/device_7_run_001/reports_complete
```

Saved-data reporting supports both the new and previous transistor-suite layout.
Historical coherence/nonlinearity formats retain their original reporting tools
below. Reports cannot reconstruct new trajectory-derived metrics if raw data were
not retained. Original per-stage reports are also still produced during simulation.

## Additional experiments

```bash
python rowers.py phase --work results/device_7_run_001 --runs 20 --cores 3
python rowers.py cycles --work results/device_7_run_001 --runs 20 --cores 3
python rowers.py gating --work results/device_7_run_001 --points 21 --runs 20 --cores 3
python rowers.py amplitude --work results/device_7_run_001 --points 21 --runs 20 --cores 3
python rowers.py locking-map --work results/device_7_run_001 --runs 20 --cores 3 --dt-divisors 2
python rowers.py robustness --work results/device_7_run_001 --runs 50 --cores 3 --dt-divisors 2
```

Gating and amplitude use the same underlying transfer measurements. Running both is
usually unnecessary: the gating/full validation reports already include amplitude.
The separate commands remain for compatibility. Full validation already includes
phase and cycles; separate commands are useful for targeted repeats or protocols.
Noise/disorder robustness currently tests endpoint gating, not the complete phase
and cycles suite under every perturbation. A locking map varies the input frequency
while keeping the control frequency fixed.

`--keep` retains bulky raw trajectories. `--config FILE` explicitly selects a geometry;
`--protocol FILE` explicitly overrides the device protocol. Both are recorded in the
stage's saved scientific metadata. Numerical settings and defaults are unchanged.

## Directory layout

```text
rowers.py                 main interface
README.md                 this guide
requirements.txt
src/                      unchanged C++ simulator and Makefile
rowerlib/
  cli.py                  command routing, experiment settings and stage history
  paths.py                module locations and source fingerprint resolution
  simulation.py           shared simulator/configuration handling
  optimisation.py         Metropolis/Bayesian search
  measurements/           trajectory, signal and transistor measurements
  experiments/            transistor suite and all earlier experiment families
  objectives/             fast, full-device and historical transistor objectives
  reporting/              figures, saved-data reporting and legacy diagnostics
analysis/                 forwarding scripts; no duplicated scientific implementation
templates/                original example locations retained for compatibility
tests/                    original tests plus unified-pipeline integration checks
docs/                     migration, scientific reference, original documentation
results/device_7_run_001/
  experiment.json
  baseline/
  search/
  validation/dt1/full/
  validation/dt1/dense/
  validation/dt2/full/
  validation/dt2/dense/
  locking_map/
  robustness/
  reports/
```

A small number of helpers remain separate to preserve tested boundaries. The
reference/template paths and legacy entry scripts are intentionally retained so old
commands continue to work. `analysis/` is not a second copy of the implementation.
See `docs/module_mapping.json` for every old-to-new module mapping.

## Earlier capabilities

Each command forwards all following options to the preserved original parser.
Run it with `--help` to see the full options:

| Command after `python rowers.py` | Preserved capability |
| --- | --- |
| `optimise-advanced` | Generic optimiser, all old objective/method/acquisition options |
| `computing` | Computing experiments, original protocols and objectives |
| `diode` | Diode characterisation |
| `disorder` | Original disorder experiments |
| `switch` | Confirm/search/validate/sequence/cycles switch pipeline |
| `diagnose-switch` | Switch diagnostics |
| `larger-switch` | Seven/eight-bead geometry preparation, search, validation |
| `offset-search` | Geometry offset search |
| `drive-sweep` | Drive sweep |
| `switch-cycles` | Original switch pipeline's cycles stage |
| `switch-load` | Output-load experiments |
| `nonlinearity` | Original control-nonlinearity experiments |
| `nonlinearity-report` | Original saved-data plots/sigmoid diagnostics |
| `legacy-transistor` | Earlier transistor preparation/analysis/sigmoid diagnostics |

For example, `python rowers.py switch --stage validate ...` retains the old switch
parser. The original `python analysis/NAME.py ...` commands and imports also work.
Old scripts retain their old default folder names; use the unified interface for
new naming and automatic winner selection. Do not mix the two interfaces on a new
manifest-only experiment; use old scripts on old work folders, or pass their required
configuration files explicitly.

## Validation of this refactor

See [validation record](docs/VALIDATION.md) for the checks run on this release.
Source relocation does not constitute new physical validation of a device.
