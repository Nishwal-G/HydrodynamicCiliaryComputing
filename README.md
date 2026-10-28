# Rowers: simulation, optimisation and analysis

This project simulates **hydrodynamically coupled, cilia-like bead oscillators**.
It lets you define their geometry and forcing, search for useful collective behaviour,
and measure how reliably the resulting device responds.

A C++ engine evolves the bead trajectories. Python prepares configurations, runs
matched experiments, performs optimisation and produces figures and numerical reports.
The main interface is **`python rowers.py COMMAND ...`**.

The project supports directional transmission (diodes), controlled oscillator junctions,
transistor-like gating, switching sequences, load tests, disorder studies and exploratory
logic/memory experiments. The supplied templates are starting configurations, not
validated computing devices.

All commands in this guide run from the **project root**: the directory containing
`rowers.py`, `src/`, `rowerlib/`, `templates/` and `requirements.txt`. Paths such as
`results/device_7_run_001` are relative to that directory unless you give an absolute path.
Replace capitalised placeholder filenames with your actual files.

## Contents

- [What a rower is](#what-a-rower-is)
- [Install and run your first example](#install-and-run-your-first-example)
- [Run the simulator directly](#run-the-simulator-directly)
- [Configurations, protocols and search settings](#configurations-protocols-and-search-settings)
- [Transistor workflow](#transistor-workflow)
- [What the transistor analysis measures](#what-the-transistor-analysis-measures)
- [Additional transistor experiments](#additional-transistor-experiments)
- [General optimisation and free parameters](#general-optimisation-and-free-parameters)
- [Diode and trajectory characterisation](#diode-and-trajectory-characterisation)
- [Input file and force-law reference](#input-file-and-force-law-reference)
- [Controlled junctions, logic and memory](#controlled-junctions-logic-and-memory)
- [Files and directory layout](#files-and-directory-layout)
- [All command families](#all-command-families)
- [Running on a blade server](#running-on-a-blade-server)
- [Runtime, seeds and reproducibility](#runtime-seeds-and-reproducibility)
- [Troubleshooting](#troubleshooting)
- [Existing projects and validation](#existing-projects-and-validation)

## What a rower is

A rower is a bead driven back and forth by an actively switched trap. When the bead
crosses one end of its stroke, the trap switches to pull it towards the other end.
This supplies energy to sustain oscillation even when thermal noise is zero.

Each bead disturbs the fluid. Other beads respond through a hydrodynamic mobility
matrix, so their phases and collective motion depend on geometry, trap parameters,
noise and external forcing. The dynamics are overdamped: mobility relates forces to
velocities, rather than integrating an inertial acceleration equation.

A useful schematic for the deterministic part is

$$
\dot{\mathbf r}_i=\sum_j\mathbf M_{ij}\mathbf F_j+\mathbf u_i.
$$

Here $\mathbf M$ is the selected hydrodynamic mobility, $\mathbf F$ includes trap and
external-drive forces, and $\mathbf u$ is the imposed flow. Thermal motion is also
supported; the wall model's noise and drift treatment is described in the force-law
reference below. This schematic is not a replacement for the implemented stochastic
integration scheme.

Three distinctions matter when interpreting results:

- **Reference geometry versus stroke direction:** bead positions and their fixed
  oscillation angles are independent settings.
- **Active oscillation versus external drive:** a bead can keep oscillating without
  an input drive. An OFF transmission state does not mean a stationary bead.
- **Coherence versus information transmission:** locking to a clock is useful evidence,
  but phase interventions test whether a changed input actually changes the output.

In the transistor experiments, the input supplies a reference signal, the control
branch changes its transmission, and designated output beads provide the readout.
Named groups label beads for forcing/measurement; they do not disconnect other
hydrodynamic interactions.

## Install and run your first example

You need Python 3.10 or newer, a C++17 compiler, `make`, `curl`, and `tar`. On a Mac,
install Xcode command-line tools if a compiler is missing. On a managed server, ask
the administrator for missing build tools rather than assuming you can install system
packages yourself.

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make -C src
python rowers.py --help
python -m unittest discover -s tests -v
```

A virtual environment keeps this project's Python packages separate from other work.
Activate it with `source .venv/bin/activate` in each new terminal session. If you
already have a working environment containing NumPy, SciPy, Matplotlib and scikit-learn,
you can keep using it instead.

`make -C src` builds the executable `src/rowers`. The Makefile downloads Eigen 3.4.0
if `src/eigen-3.4.0/` is absent. Check that `src/eigen-3.4.0/Eigen/Dense` exists if
compilation reports missing headers; an incomplete existing directory does not trigger
the download. If network access is blocked, obtain the complete Eigen directory from
your administrator.

After changing C++ source or moving to another machine, rebuild:

```bash
make -C src clean
make -C src
```

The compiler uses `-march=native`. Build separately on the Mac and each different
server rather than assuming one machine's binary is portable to another.

For a first simulation, use the supplied six-bead example:

```bash
./src/rowers -C -R templates/6beads.input
```

This produces a `6beads/` output directory in your current directory. The next
section explains its files. This is a direct simulator demonstration; it does not
perform optimisation or establish transistor behaviour. The current C++ source already
contains the earlier simulator fixes; no historical patch file needs applying.


## Run the simulator directly

```bash
./src/rowers -C -R templates/6beads.input
```

Both flag positions are required. The first selects geometry and the second
selects the hydrodynamic approximation:

| Position | Flag | Meaning |
| --- | --- | --- |
| Geometry | `-C` | Chain with reference positions along x. |
| Geometry | `-R` | Ring of reference positions. |
| Geometry | `-A` | Arbitrary reference positions supplied in the input. |
| Mobility | `-R` | Rotne–Prager finite-size correction; Python default. |
| Mobility | `-B` | Blake point-force wall model with fixed-height constraints. |
| Mobility | `-O` | Oseen point-particle approximation. |

All layouts support a fixed oscillation angle for each bead. Without an angle
line, traps still switch along global x. Reference geometry and stroke direction
are independent: a chain can lie along x while its beads oscillate at different
angles. Python now supports explicit planar coordinates (including ring layouts);
see [Computing experiments](#controlled-junctions-logic-and-memory). Legacy CLI geometry flags remain available.
Oseen is a far-field approximation and can become unsuitable at close separation.
Do not infer a guarantee of positive-definite mobility for every configuration
from the presence of the `-R` option; overlapping/coincident beads and numerical
factorisation require particular care in this implementation.

The command writes a `6beads/` directory under the current working directory:

| Output | Contents |
| --- | --- |
| `*.dat` | Frame index, physical time, then laboratory x/y bead coordinates. |
| `*.hydro` | Mobility name, wall height and imposed shear; confirms simulator settings. |
| `*.axes` | One row per bead: angle in degrees, reference x, reference y. Used for local-axis analysis. |
| `*.trap` | Trap-centre records in the simulator's own output format. |
| `*.forces` | Frame, physical time and force components after the timestamp fix. |

The analyser reads `.dat` trajectories. Do not assume that `.trap` uses the
same columns. Direct runs can overwrite existing files with the same names;
Python-managed experiments use fresh work directories.

**Keep each `.axes` file beside its same-stem `.dat` file when moving results.**
The analyser automatically loads the angles. A missing `.axes` file is treated
as an old horizontal trajectory; removing it from an angled run would therefore
produce incorrect phase and frequency measurements.

To run the supplied angled example:

```bash
./src/rowers -C -R templates/6beads_angles.input
```

The first line remains the original numerical configuration. Optional later
labelled lines specify angles, per-bead trap parameters and wall settings; see the input-file reference below. Blank
lines and `#` comments are accepted after the numerical first line. Use one
configuration per file. Multiple files can be processed sequentially:

```bash
./src/rowers -C -R run1.input run2.input run3.input
```

## Configurations, protocols and search settings

Before running an experiment, distinguish four kinds of information:

| Item | What it controls | Where it lives |
| --- | --- | --- |
| Physical configuration | Beads, geometry, traps, mobility, noise and drives | A template or a saved `best.json`; `configuration` in a new experiment manifest |
| Experiment protocol | Cases, control levels, timing, observation windows and criteria | `device` in the transistor manifest; separate protocol JSON for older tools |
| Search specification | Which coordinates may change, their bounds and proposal steps | `search` in the transistor manifest; a search JSON for the generic optimiser |
| Run settings | Repeats, workers, iterations, seeds and output location | Command-line options and recorded stage metadata |

A saved `best.json` is a complete physical configuration plus optimisation metadata,
not just a list of changed coordinates. It can seed a new search or a validation run.

New transistor experiments use one authoritative `experiment.json`, written by
`prepare`. Its main fields are `configuration`, `source_configuration`, `device`,
`search`, `fast`, `preparation`, `stages` and `stage_history`. Templates supply defaults
at preparation time; editing a template later does not change a prepared experiment.

**Older computing/switch tools also use files called `experiment.json`, but with a
different schema.** Use separate work directories for different experiment families.
Do not rename an old protocol file to turn it into a new transistor manifest.

### Planar geometry and named bead groups

Computing templates are JSON objects with a `configuration` member, just like saved
best.json files. They contain all existing scalar/per-bead settings, plus:

| Field | Meaning |
| --- | --- |
| reference_x, reference_y | Two length-N arrays of planar trap reference coordinates. Both empty means the old chain layout. |
| groups | A dictionary mapping names to nonempty lists of unique zero-based bead indices. |
| direct_traps | true gives H_i=1 in the trap potential. false preserves the legacy spacing/index multiplier. |
| drives | null preserves the legacy F0/T_signal force; [] explicitly disables external drives; a list defines independent drives. |
| seed | -1 selects random seeds; integer 0..4294967295 seeds initial state and thermal noise. |

Groups are labels for drives and analysis. They do not introduce connections or
remove interactions: the engine evaluates the hydrodynamic coupling between all
beads. A ring is simply explicit coordinates plus a cyclically ordered group.
Arbitrary layout coordinates override the first-line chain reference geometry.
The retained `distances` array is a legacy input container for explicit layouts;
it does not control their actual positions. Search reference_x/y instead.

Keep one bead fixed and usually fix a second coordinate when searching geometry
to avoid spending effort on translations/rotations of the same arrangement.
All reference pair separations are checked against the existing minimum gap and
bead diameter. Blake also requires at least four radii; instantaneous Blake
separations remain checked by the engine. Reference checks do not prevent later
close encounters or replace timestep/physical-validity studies.

Use direct_traps=true for the circuit templates. Each bead then has
U_i = kx_i |d_parallel|^alpha_i + ky_i |d_transverse|^beta_i.
The familiar kx is the potential coefficient: at alpha=2 the harmonic spring
constant is 2*kx under this convention. Changing bead indices cannot change H_i
in direct mode. Legacy lambda/base_distance trap multipliers remain available
with direct_traps=false; their searches are rejected in direct mode because
these multipliers then have no effect.

### Independent timed drives

Each drive has these fields (JSON needs no comments):

```json
{
  "targets": "input",
  "amplitude": 2.5,
  "period": 0.184715,
  "phase": 0.0,
  "start": 1.0,
  "stop": 12.0,
  "waveform": "square"
}
```

`targets` is a group name or a list such as [0,2]. Amplitude is the force on EACH
target, not a total divided among targets. Several drives on a bead add. Forces
act along that bead's local stroke axis, then rotate into laboratory coordinates
before the mobility calculation. They are external forces, not background flow.

phase is in radians. For start <= t < stop, the waveforms are:

- square: amplitude * sign(cos(2*pi*t/period + phase)), with zero mapped to -1.
- sine: amplitude * sin(2*pi*t/period + phase).
- constant: amplitude (period and phase do not affect the force).

Outside this interval the contribution is zero. The clock uses ABSOLUTE time,
not time since start. To start a sine at phase zero at start, set
phase=-2*pi*start/period. Negative constant forcing can be represented by a
reversed stroke direction; amplitudes are nonnegative. Missing phase/start/stop/
waveform default to 0/0/total_time/square when loading configuration JSON.

An explicit list replaces the legacy drive; it never adds to it. F0/T_signal are
then ignored by the engine and rejected as search coordinates. An empty list
means unforced, even if F0 is nonzero. Legacy mode retains the exact t>5 square
wave behaviour. To make a phase jump, use consecutive, non-overlapping drives
with different phases. To provide a pulse, give a finite start/stop interval.

## Transistor workflow

Replace `PATH_TO_EXISTING_BEST.json` with a saved configuration or best.json. No
optimised geometry is bundled with the source distribution.
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


If you do not have an existing seven-bead configuration, construct a starting layout
from the supplied junction first (this preparation does not run a search):

```bash
python rowers.py larger-switch --stage prepare \
  --work results/seven_bead_starts \
  --config templates/computing/junction.json --beads 7

python rowers.py prepare \
  --work results/device_7_from_template \
  --config results/seven_bead_starts/start_1.json
```

Use `results/device_7_from_template` instead of `results/device_7_run_001` in the
following commands for that route. These are two alternative starting routes, not
steps to run twice. Template-based starts are not previously optimised geometries.

### 2. Baseline

```bash
python rowers.py baseline --work results/device_7_run_001 --runs 3 --cores 3
```

The baseline measures your starting geometry before changing it. It provides the
comparison against which you judge any later optimisation improvement.

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

## What the transistor analysis measures

Read the numerical records alongside the plots. Values are measured over finite
observation windows and depend on explicit operational criteria.

### Coherence and gating contrast

The output's coherence relative to the input clock is

$$R_j=\left|\left\langle e^{i(\phi_j-\theta_{\rm in})}\right\rangle\right|.$$

$R\simeq1$ means a consistent relative phase; it does not require zero phase lag.
A small value means that the relative phase varies within the observation window.
Compare input-plus-control cases with input-only and control-only cases.

A reported endpoint gating contrast is

$$C_{\rm gate}=\frac{R_{\rm ON}-R_{\rm OFF}}{R_{\rm ON}+R_{\rm OFF}}.$$

Inspect the underlying values as well as this ratio: two very small coherences can
have a large normalised contrast. The fast search rewards the absolute difference,
not this ratio.

### Locking, reliability and frequency mismatch

With the default device criteria, a valid output is locked when all three hold:

$$R\geq0.95,\qquad |\Delta\omega/\omega_{\rm in}|\leq0.01,\qquad N_{\rm slips}=0.$$

Frequency mismatch is estimated from the fitted slope of unwrapped relative phase.
The defaults are experimental definitions, not universal constants. A large mean
coherence does not guarantee every repeat passes these criteria.

The reports include locked/valid and locked/all-repeat fractions, invalid counts and
Wilson 95% intervals. Mean curves use standard errors across repeats. Time samples
and correlated sliding windows are not independent repeats.

### Phase transmission and dynamic switching

The phase intervention changes the input drive by $\delta=\pm\pi/4$ while keeping
the control phase fixed. Faithful transmission gives a paired output change near
$\delta$ with high coherent following quality. The quality $Q$ combines coherence
with agreement of the complex response; it is not a success probability.
See [the scientific reference](docs/scientific_reference.md) for its exact formula.

Repeated ON/OFF cycles test reversibility in one continuous trajectory. Switching
times include the effects of the trailing measurement window and sustained-detection
rule. Inspect censored, invalid and already-target cases rather than treating every
missing delay as zero.

### Fourier displacement response

The input-frequency component of output displacement is

$$A_j=\frac{2}{T}\left|\int_{t_1}^{t_2}q_j(t)e^{-i\theta_{\rm in}(t)}\,dt\right|.$$

Here $q_j$ is displacement along the bead's local stroke direction. The estimator
uses an integer-period observation interval. An increase in $A$ can reflect more
coherent input-frequency motion without an equivalent increase in total stroke.
The plotted $\Delta R/\Delta F_c$ and $\Delta A/\Delta F_c$ are finite-difference
sensitivities; neither establishes power amplification.

### The fast search objective

With default weights, Metropolis maximises

$$J=\frac1{n_{\rm repeats}}\sum_r\left\{
\min_j[D_j+N_j-2U_j-2L_j-M_j]-2I\right\}_r.$$

| Term | Meaning |
| --- | --- |
| $D$ | $R(1)-R(0)$: high versus zero-control difference |
| $N$ | Excess rise within the chosen central control interval |
| $U$ | High-control output locking loss |
| $L$ | Maximum output coherence with input absent at the two control endpoints |
| $M$ | Sum of downward steps along the control-response curve |
| $I$ | Worst input locking loss across the driven cases |

The fractions are $f=F_c/F_{\rm high}=[0,0.35,0.5,0.65,1]$, with

$$N=\frac{R(0.65)-R(0.35)-0.30[R(1)-R(0)]}{0.70}.$$

A linear curve gives $N=0$. The default ideal score is 2; higher is better, and a
negative score means the weighted penalties exceed the rewards. There is no score
threshold that proves transistor behaviour. Inspect both outputs and validate on
fresh repeats. The minimum across outputs prevents one good output hiding another.

The fast score uses seven trajectories per repeat. It deliberately leaves causal
phase interventions, dynamic cycles and disorder out of each candidate evaluation.
Those remain in validation/additional experiments. The full and historical scores
are retained, but their numerical values are not directly comparable to $J$.


## Additional transistor experiments

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

## General optimisation and free parameters

```bash
python rowers.py optimise-advanced --method metropolis --config templates/6beads.input --search search.json --set total_time 100 --iterations 50 --runs 3 --cores 3 --out results/metro
python rowers.py optimise-advanced --method bayesian --config templates/6beads.input --search search.json --set total_time 100 --initial 12 --iterations 50 --runs 3 --cores 3 --out results/bayes
```

The example search includes inner reference positions, period, force and global
alpha. Bounds are starting choices, not a scientifically validated parameter
range. Remove the `alpha` entry to keep the template's exponent fixed. Commands
are examples, not requests to perform a long search automatically.

For this default directional objective, each evaluated candidate costs `3 * runs` simulations: forward forcing, backward
forcing, and an unforced control per repeat. Repeats run concurrently; candidate
configurations are evaluated sequentially. `--cores` controls concurrent repeats.
`--initial` counts the specified initial point plus random initial points.
Invalid Metropolis proposals are rejected before simulation.

### Select free and fixed parameters

`search.json` is the sole selection of free variables:

```json
{
  "positions": {"step": 0.5},
  "T_signal": {"bounds": [0.01, 2.0], "step": 0.02},
  "F0": {"bounds": [0.5, 10.0], "step": 0.2},
  "alpha": {"bounds": [0.5, 2.0], "step": 0.05}
}
```

Parameters omitted here stay fixed. Initial values come from the input unless
an entry supplies `initial`. For example, add:

```json
"temperature": {"bounds": [0, 100], "initial": 70, "step": 5}
```

Global `kx`, `ky`, and `default_lambda` intentionally set all corresponding
per-bead values. To vary beads independently, use `kx_per_bead`, `ky_per_bead`,
or `lambdas` instead. Do not select a global value and its per-bead array together.
Scalar bounds/steps broadcast across an array; separate bounds can be given as
`[[lower_0, lower_1, ...], [upper_0, upper_1, ...]]`. The array length is determined
by the number of beads. Positions have N-2 entries; endpoints remain fixed.

### Independent bead parameters and indexed searches

Six beads have six distinct longitudinal coefficients in `kx_per_bead`. Searching
that array makes six independent variables. Searching global `kx` instead uses
one common coefficient for all beads. The same convention applies to alpha,
beta, ky, amplitude, epsilon and their per-bead arrays (lambda uses `lambdas`).

```json
{
  "kx_per_bead": {"bounds": [8, 14], "step": 0.2},
  "alpha_per_bead[0]": {"bounds": [0.5, 1.0], "step": 0.02},
  "wall_height": {"bounds": [5, 10], "step": 0.2}
}
```

This example has eight variables: six independent kx values, bead 0's alpha,
and height. `wall_height` requires Blake mode. To vary only two stiffnesses,
select `kx_per_bead[0]` and `kx_per_bead[1]` instead of the whole array. Quote
bracketed names in shell commands. Global/array/index overlaps are rejected.
`bead_radius` is now searchable, but remains one common radius, not N radii.

`docs/original_search_help.txt` is a reference, not a runnable search specification.
Use `search_wall.json`
for the example above. Omit variables to fix them; setting `step` to zero does
not fix a variable for Bayesian optimisation. Angles, radius, wall height and
trap parameters are retained in best.json and all matched experiments.

### Search or fix the oscillation angles

Add this entry to a search JSON object to vary all N angles independently:

```json
"angles_deg": {"bounds": [-90, 90], "step": 5}
```

Angles, bounds and steps are in **degrees**. To create an angle-only search file, save the following as `search_angles.json`
in the project root (this example file is not pre-created):

```json
{
  "angles_deg": {"bounds": [-90, 90], "step": 5}
}
```

Other physical parameters then stay fixed:

```bash
python rowers.py optimise-advanced --method metropolis --config templates/6beads_angles.input --search search_angles.json --set total_time 50 --iterations 5 --runs 1 --cores 1 --out results/angles_metro
python rowers.py optimise-advanced --method bayesian --config templates/6beads_angles.input --search search_angles.json --set total_time 50 --initial 12 --iterations 5 --runs 1 --cores 1 --out results/angles_bayes
```

Both methods use the existing bounded parameter machinery. There is no circular
wrapping of proposals or periodic GP kernel. `step` sets the Metropolis proposal
scale, not a discretisation of allowed angles. Choose bounds and initial angles
consistently. Arrays of per-bead bounds/steps are supported as above.

To hold a pattern fixed, leave `angles_deg` out of the search and set it in the
input, or pass `--set angles_deg '[0, 15, 30, 45, 60, 75]'` for six beads. The
angles stay fixed in time within each simulation. They are saved in complete
configurations and `best.json`; older configurations without them default to zero.

### Fixed input overrides

Use `--set NAME JSON_VALUE` for fixed overrides, for example:

```bash
python rowers.py optimise-advanced --search search.json --set temperature 0 --set total_time 100 --out results/zero_temperature
```

For an array, quote the JSON value: `--set distances '[6, 7, 8, 9, 10]'`.
This is also how to choose a different total chain length. All gaps must satisfy
the constraints. Updating a free parameter with `--set` sets its baseline/initial
value, not a constraint keeping it fixed.

`rowerlib/simulation.py` contains `SCALARS`, the positional input mapping, and `SEARCHABLE`,
the supported continuous coordinates. Adding a currently supported parameter to
`search.json` updates both optimisers and their plots automatically. Adding a
new physical parameter requires a real C++ input mapping and validation; adding
an arbitrary catalogue name cannot change the simulator. Numerical settings,
bead count and unused C++ fields are not free optimisation variables.

### What the search maximises

With none of `--experiment`, `--transistor`, `--device` or `--fast-device` supplied,
the generic optimiser maximises the original directional signal-based objective:

`mean_over_repeats(R_last_forward - R_first_backward)`.

R is the magnitude of the time-averaged signal-relative phase phasor. Frequency
mismatch, winding/slip candidates and controls are saved but do not secretly alter
this score. A high score is evidence of directional phase consistency over the
observation window, not proof of causal information transfer.

The signal is the simulator's square wave starting after t=5. It acts along the
driven bead's local positive oscillation axis, with the same longitudinal
amplitude in forward and backward experiments. Default analysis
starts at t=7. At least two signal periods of common endpoint phase coverage are
required; substantially longer measurements are appropriate for scientific
claims. The recording interval is refined for short signal periods. Integration
still uses the input dt; output refinement does not establish timestep convergence.

Metropolis accepts improvements and accepts worse scores with probability
`exp((new_score-current_score)/search_temperature)`. This temperature is separate
from physical temperature. Bayesian optimisation uses a Matern Gaussian process
with learned white noise and UCB (default) or expected improvement; it searches
50,000 random valid candidates by default. SEM is recorded but is not supplied
as a separate heteroscedastic GP noise model.

### Outputs and reproducibility

- `best.json`: complete physical configuration of the best measured candidate.
- `history.json`: search settings, named coordinates, protocol and search history.
- `objective_evaluations.jsonl`: one record per actual evaluation, including all
  repeats, controls, endpoint diagnostics and SEM.
- `progress.png`, `parameters.png`: score and coordinate histories.
- `gp_slice.png`: Bayesian surrogate mean/uncertainty at the best remaining
  coordinates. This is a model prediction, not a measured phase diagram.

Successful raw simulations are deleted unless `--keep` is supplied. Failed
simulations retain inputs and logs. In the default directional objective, an unavailable endpoint measurement stops
optimisation with a diagnostic; it is never converted to a zero score. In a
parameter diagram it is recorded as a missing measurement so other points can
continue. The best candidate is not automatically revalidated on fresh repeats.

`--seed` seeds Python proposals. Use `--set seed 12345` to seed the C++
simulator too: replicate i uses seed 12345+i, shared across its matched cases.
The default simulator seed=-1 preserves legacy random runs. See [seeds and reproducibility](#runtime-seeds-and-reproducibility)
for how to validate on a fresh ensemble.

Bayesian warm start accepts a compatible `objective_evaluations.jsonl`:

```bash
python rowers.py optimise-advanced --method bayesian --search search.json --set total_time 100 --warm-start results/metro/objective_evaluations.jsonl --out results/warm_bayes
```

Protocol hashes, fixed inputs and bounds must match. This intentionally rejects
old histories and histories from edited code; never mix incompatible objectives.
Warm start adds observations, it does not resume a Metropolis chain. New initial
points are still evaluated. Warm observations remain in their original audit;
`history.json` records the warm-start source path.

## Diode and trajectory characterisation

### Mechanism: every bead, three directions/controls

```bash
python rowers.py diode mechanism --config results/metro/best.json --runs 5 --time 100 --out results/mechanism
```

`relative_phase.png` shows the first repeat's unwrapped phase relative to the
signal for every bead, forwards/backwards/control. `mechanism.png` shows mean
per-bead R, relative frequency mismatch and winding-candidate rate. All repeat
measurements and their actual time intervals are in `mechanism.json` and the
audit. Missing interior measurements are gaps; they are not zeros. Keep raw
trajectories with `--keep` if you want to inspect other repeats.

### Unforced frequency spectra

```bash
python rowers.py diode frequency --config results/metro/best.json --time 100 --runs 5 --frequency-min 0.1 --frequency-max 20 --out results/frequency
```

Outputs include per-bead Welch spectra, dominant frequencies, the peak of the
mean spectrum and ensemble uncertainty. These are frequencies of the unforced
**coupled chain**, not necessarily isolated-oscillator natural frequencies.
For angled runs, spectra use each bead's longitudinal coordinate rather than
laboratory x, so a vertical stroke is still measured correctly.

### Two-dimensional phase diagrams

```bash
python rowers.py diode diagram --config results/metro/best.json --x alpha 0.5 2 --y T_signal 0.1 0.5 --points 15 --runs 3 --time 100 --out results/alpha_period
```

A 15x15 grid with three repeats costs 2,025 simulations. Start with a small grid.
Outputs are saved after every point. `diagram.json` contains complete point
configurations and raw diagnostics, allowing reclassification without rerunning.
`diagram.png` contains score, forward/backward R, locking regime and control
locking fractions. Blank cells indicate invalid or unavailable measurements.

A repeat is classified as locked when R >= `--r-min` (default 0.9), absolute
relative frequency mismatch <= `--mismatch-max` (default 0.01), and winding
candidate rate <= `--slip-rate-max` (default 0). A direction is labelled locked
when at least `--lock-fraction` of repeats pass (default 1). These are explicit
finite-window choices, not universal physical thresholds. Controls are shown
separately rather than being assumed to establish causality automatically.

Scalar inputs can be diagram axes. A per-bead axis uses e.g. `kx_per_bead[2]`
or `angles_deg[2]`. Quote bracketed names in shell commands:

```bash
python rowers.py diode diagram --config templates/6beads_angles.input --x 'angles_deg[0]' -90 90 --points 11 --runs 3 --time 100 --out results/angle_sweep
```
Geometry axes are:

- `asymmetry`: interpolate gaps from equal spacing (0) to the supplied geometry
  (1), at fixed length. Does not remove non-geometrical trap asymmetry.
- `d_avg`: scale all supplied gaps to a new mean spacing.
- `d_grad`: construct linear gaps at the current mean spacing.
- `g_factor`: construct geometrically varying gaps at the current mean spacing.

Mean spacing is applied before the second geometry control. Conflicting axes
are rejected. Invalid gaps are never clipped, because clipping would change the
claimed geometry. The legacy implementation did clip them; this is an explicit
correctness change.

### One-dimensional and legacy sweeps

Omit `--y` to get a line sweep. For an unforced gradient sweep:

```bash
python rowers.py diode diagram --config templates/6beads.input --metric frequency --x d_grad -0.5 0.5 --points 11 --time 100 --out results/frequency_gradient
```

Use `--metric legacy` to retain the previous sweep's real-sum endpoint coherence
and distance-reversal protocol. It reverses **distances only**, not the full
per-bead physical configuration. It is distinct from swapping the driven endpoint
and is labelled accordingly. All values and repeats are stored in JSON.

### Existing trajectory plots

```bash
python rowers.py diode trajectory path/to/run.dat --signal-period 0.184715 --analysis-start 7 --outdir results/trajectory
```

This preserves the previous six plots: trajectories, coherence, crossings,
bead-to-bead phase differences, signal-relative phase and signal-locking summary,
plus the JSON summary. Omit signal arguments for a purely trajectory/coherence
analysis. `trajectory --help` lists the retained options.

For compatibility, trajectory mode retains its previous reference-level choice
(settled mean when signal analysis is enabled), whereas the original optimisation
and matched-experiment evaluator use full-record mean crossing levels. Thus
standalone trajectory measurements need not exactly equal evaluator measurements.
The evaluator's audit is authoritative for its score. Use `--reference-x` (also
accepted as `--reference-longitudinal`) to choose explicit levels in trajectory
mode. For angled runs these are local longitudinal coordinates, not laboratory
x. The summary retains the legacy `crossing_level_x` key and adds
`crossing_coordinate: "longitudinal"`. Cached phases assume an analyser's
trajectory and hysteresis settings are not modified after construction.

For each bead, analysis projects the laboratory position onto its local axes:
`u_i = x_i*cos(theta_i) + y_i*sin(theta_i)` and
`v_i = -x_i*sin(theta_i) + y_i*cos(theta_i)`. Crossings, phase, coherence,
locking and spectra use `u_i`. Subtracting its mean is equivalent to subtracting
the mean of the longitudinal displacement relative to the fixed reference.
Trajectory-mode motion plots are labelled as longitudinal displacements.

For custom Python scripts, `BeadDataAnalyzer.positions` still contains laboratory
x/y. Pass `reader.analysis_positions` to `MultiBeadCoherenceAnalyzer` for local
longitudinal/transverse analysis. At zero angles, these arrays are identical.

### Controlled stiffness disorder

The existing disorder workflow also works with angled configurations:

```bash
python rowers.py disorder --config results/metro/best.json --strengths 0 0.05 0.1 0.2 --samples 20 --runs 3 --cores 3 --total-time 100 --output results/stiffness_disorder
```

This perturbs longitudinal stiffness as `kx_i = kx_i0*(1 + w*u_i)`, with a
quenched random pattern `u_i` drawn uniformly from [-1,1]. Here `u_i` denotes
the disorder draw, not the trajectory coordinate defined above. The same pattern
is reused across disorder strengths. `w` is the maximum fractional perturbation,
not its standard deviation or a fraction of beads selected for perturbation.
`--samples` counts patterns and `--runs` counts simulation repeats per pattern.
Angles and the other baseline parameters stay fixed unless an available override
is explicitly supplied. This tests stiffness disorder, not angular disorder.
Use `--dry-run` to save the design without running simulations, and `--keep` to
retain trajectories. Outputs include `disorder_response.png` and
`disorder_locking.png`.

## Input file and force-law reference

The first line is a space-separated numerical record. Fields below are numbered
from **1**; Python indices in `rowerlib/simulation.py` start at **0**. The first 22 fields
are scalars, followed by geometry and per-bead blocks. Do not insert text labels
or inline comments into the numerical line.

The templates use the following configurations:

| Template | Beads | Reference gaps | Total reference length |
| --- | --- | --- | --- |
| `6beads.input` | 6 | 6.046, 7.068, 7.961, 9.037, 9.929 µm | 40.041 µm |
| `8beads.input` | 8 | Seven gaps of 7.5 µm | 52.5 µm |
| `6beads_angles.input` | 6 | Same gaps as `6beads.input`; angles 0°, 15°, 30°, 45°, 60°, 75°. | 40.041 µm |

The table below lists the six-bead template's scalar values. Quantities must use
the simulator's consistent length, time, force and thermal-energy conventions;
do not mix SI viscosity with micrometre-based numerical inputs without conversion.

| Field | Python name | Value | Meaning |
| --- | --- | --- | --- |
| 1 | `num_beads` | 6 | Number of beads; choose a corresponding template. |
| 2 | `amplitude` | 3 | Excursion parameter A; switching thresholds are at ±A/2 along the local axis relative to each reference position. |
| 3 | `base_distance` | 6 | Reference spacing used in ring geometry and chain trap-strength scaling. |
| 4 | `bead_radius` | 1.5 | Bead radius entering mobility. |
| 5 | `dt` | 0.00005 | Integration timestep. |
| 6 | `total_time` | 30 | Simulation duration. |
| 7 | `viscosity` | 0.006 | Fluid viscosity in the model's unit convention. |
| 8 | `alpha` | 0.5 | Exponent of the longitudinal **potential**; the force magnitude scales as displacement to the power alpha−1. |
| 9 | `kx` | 10 | Default longitudinal potential coefficient, not a universal spring constant for all alpha. |
| 10 | `beta` | 1.5 | Exponent of the transverse potential. |
| 11 | `ky` | 10 | Default transverse potential coefficient. |
| 12 | `temperature` | 70 | Physical/effective temperature entering thermal displacement. Zero disables stepwise thermal noise. |
| 13 | `sampling_feedback` | 50 | Integration steps between trap-switching checks. |
| 14 | `sampling_write` | 200 | Integration steps between output records. |
| 15 | `epsilon` | 0.3 | Places active trap centres epsilon beyond the switching thresholds. |
| 16 | `velox` | 0 | Uniform background flow velocity in x. |
| 17 | `ks` | 0 | Parsed legacy field; unused by the supplied force implementation. |
| 18 | `fl0` | 0.25 | Parsed legacy field; unused by the supplied force implementation. |
| 19 | `veloy` | 0 | Uniform background flow velocity in y. |
| 20 | `F0` | 2.5 | External square-wave force amplitude along the driven bead’s local axis. |
| 21 | `T_signal` | 0.184715 | External driving period. |
| 22 | `default_lambda` | 0.06 | Fallback parameter for the per-bead trap-strength profile. |

After these scalar fields, **chain inputs** contain:

| Block | Number of values | Meaning |
| --- | --- | --- |
| `distances` | N−1 | Gaps between neighbouring reference positions. |
| `lambdas` | N | Per-bead trap-profile parameters. |
| `kx_per_bead` | N, optional | Per-bead longitudinal coefficients. |
| `ky_per_bead` | N, optional | Per-bead transverse coefficients. |
| Signal list | 1 + count, optional | Number of driven beads followed by their zero-based indices. |

The supplied templates include distances and lambdas but omit the stiffness and
signal blocks. The defaults are global kx/ky and signal bead 0. To specify signal
beads, include both full stiffness blocks first. The Python input writer always
emits the complete blocks to avoid ambiguity, then writes the labelled angle
line separately. Do not append angles to the positional first-line blocks.

### Labelled per-bead and wall extensions

The first-line scalars remain defaults. Missing arrays are filled from their
corresponding scalar; supplied arrays override them. The labelled arrays are
`alpha_per_bead`, `beta_per_bead`, `amplitude_per_bead`, `epsilon_per_bead`.
The existing `kx_per_bead`, `ky_per_bead` and `lambdas` can also be specified as
labelled lines, overriding their legacy positional blocks. Each needs N values.
A fixed global override broadcasts first, then explicit per-bead overrides win.

```text
mobility blake
wall_height 6
shear_x 0
shear_y 0
alpha_per_bead 0.5 0.55 0.6 0.65 0.7 0.75
beta_per_bead 2 2 2 2 2 2
kx_per_bead 10 10.2 10.4 10.6 10.8 11
ky_per_bead 10 10 10 10 10 10
amplitude_per_bead 3 3 3 3 3 3
epsilon_per_bead 0.3 0.3 0.3 0.3 0.3 0.3
```

These lines follow the numeric first line. `mobility` accepts `oseen`,
`rotne_prager`, `blake`; an explicit input line takes precedence over the CLI
mobility flag. Without it, direct C++ uses its flag and Python defaults to
Rotne–Prager. Unknown/duplicate labels, non-finite values, wrong array lengths
and nonpositive trap parameters are rejected. The Python writer resolves all
arrays and writes complete settings. Old complete JSON configurations are
filled with supported defaults when loaded.

### Optional angle line

After the numerical line, add exactly one finite angle per bead:

```text
# Angles in degrees, anticlockwise from laboratory +x.
angles_deg 0 15 30 45 60 75
```

Omitting this line gives zero angles. A repeated angle line, unknown label,
wrong number of values or non-finite values is rejected. The C++ engine converts
degrees to radians internally. The example input is included; create an angle-search JSON as shown above.

For example, this complete six-bead input has increasing longitudinal coefficients, uniform
transverse coefficients, and external forcing at beads 0 and 5:

```text
6 3 6.0 1.5 0.00005 100 0.006 0.5 10 1.5 10 70 50 200 0.3 0.0 0 0.25 0.0 2.5 0.18 0.06 6.0 7.1 8.0 9.0 9.9 0.06 0.06 0.06 0.06 0.06 0.06 8 9 10 11 12 13 10 10 10 10 10 10 2 0 5
```

The matched signal experiments intentionally override the signal list: first
bead for forward, last bead for backward, and zero force for control. They keep
the geometry, angles and per-bead coefficients in place. They do **not** reverse those
arrays. Legacy sweep mode instead reverses distances only, retaining the older
protocol.

For arbitrary geometry, the C++ parser expects coordinate pairs rather than the
chain-distance block; this table and the Python input reader are for chains.

### Trap force and active oscillation

For angle theta_i, define the local unit vectors
`e_i = (cos(theta_i), sin(theta_i))` and
`n_i = (-sin(theta_i), cos(theta_i))`. Let `R_i` be the fixed reference position,
`q_i = (r_i-R_i) dot e_i` the longitudinal displacement and
`p_i = (r_i-R_i) dot n_i` the transverse displacement.

The active trap centre is `R_i + s_i*(A_i/2 + epsilon_i)*e_i`, where `s_i` is +1 or
−1. Here `s_i` labels the trap side, not the external signal. With
`delta_parallel = q_i - s_i*(A_i/2 + epsilon_i)`, the longitudinal force is
`−kx_i * H_i * alpha_i * delta_parallel * abs(delta_parallel)^(alpha_i−2)`, plus
the selected external drive on driven beads. The transverse force is
`−ky_i * H_i * beta_i * p_i * abs(p_i)^(beta_i−2)`. The code retains its existing
near-zero displacement guards. Thus alpha=2 gives a harmonic longitudinal
potential; kx is a potential coefficient and the force includes the factor alpha.

The laboratory force is `F_parallel*e_i + F_perp*n_i`. Traps switch to the
negative side when `q_i > A_i/2` and to the positive side when `q_i < -A_i/2`, at the
existing feedback-check intervals. Initial random offsets are rotated onto the
same local axis. Transverse confinement remains finite: a bead is not rigidly
constrained to a line.

The full mobility tensor, correlated thermal noise and background flow remain
in laboratory coordinates. The existing tensor handles the rotated forces;
no new mobility approximation is needed. `velox` and `veloy` retain their global
x/y meanings in unbounded modes. Setting all angles to zero and retaining
global trap defaults recovers the horizontal trap model. Blake instead uses
the shear settings described below.

With `direct_traps=false`, H_i depends on local reference spacing and lambda_i.
With `direct_traps=true`, H_i=1. Lambda changes
trap strength, rather than directly multiplying the hydrodynamic tensor. Moving
trap centres between opposite sides sustains oscillation even at zero thermal
temperature. Random initial positions and initial trap sides remain at zero
temperature.

In legacy `drives=null` mode, the external signal is `F0 * sign(cos(2*pi*time/T_signal))` after time 5. Its phase
clock is not reset when forcing begins. The code uses a definite branch at cosine
zero, so this expression is shorthand for its implemented square wave.

### Blake wall model and a heterogeneous example

The wall is the stationary plane z=0. Bead centres remain at common height h,
with motion and stroke angles in the parallel xy-plane. This release does not
simulate strokes towards/away from the wall, per-bead heights or per-bead radii.

```bash
./src/rowers -C -B templates/6beads_wall_heterogeneous.input
python rowers.py optimise-advanced --method metropolis --config templates/6beads_wall_heterogeneous.input --search search_wall.json --set total_time 50 --iterations 5 --runs 1 --cores 1 --out results/wall_pilot
python rowers.py diode mechanism --config results/wall_pilot/best.json --time 100 --runs 3 --cores 3 --keep --out results/wall_mechanism
```

The heterogeneous template uses six beads, radius 1, five gaps of 12 (total length 60),
height 6, individual exponents/stiffnesses and temperature 0 for a fast pilot.
Use `--method bayesian` with the same search to use Bayesian optimisation.
Global signal amplitude/period and the directional objective are unchanged.

The pair kernel is the point-force Blake image system, including its Stokeslet,
source-doublet and Stokes-doublet contributions. Self mobilities use the
parallel/normal series in Bruot & Cicuta (2016), Section 3.1.3, Eq. (4); pair
terms follow Eqs. (5)-(6). The finite-radius pair correction in Eq. (7) is NOT
included. This is not RPY-Blake, lubrication theory or a contact model.
Reference: https://doi.org/10.1146/annurev-conmatphys-031115-011451

We assemble the 3N mobility, then eliminate normal constraint forces with
`M_eff = M_pp - M_pz * inverse(M_zz) * M_zp`. This enforces fixed height, rather
than simply dropping the normal velocities. Both the normal block and effective
mobility must be positive definite; failures raise errors, never artificial
matrix jitter. Height must be at least 3 radii and instantaneous pair distance
at least 4 radii. These operational guards do not prove asymptotic accuracy;
use larger separations and compare approximations for scientific conclusions.

The h->infinity limit is Oseen with Stokes self drag, NOT finite-size RPY.
At finite temperature, noise covariance is `2*kBT*M_eff*dt`, and the Itô drift
`kBT*div(M_eff)*dt` is included via centred finite differences in planar
coordinates, with derivative step `1e-5*bead_radius`. This requires 4N extra
wall-mobility evaluations per integration step and is substantially slower.
The legacy unbounded integration is retained; this is not a new general audit
of its planar Brownian approximation. Initial conditions remain random at T=0 unless a simulator seed is supplied.

Uniform `velox`/`veloy` are rejected in Blake mode. Instead specify `shear_x`
and/or `shear_y` (inverse time), giving imposed flow
`u(z)=z*(shear_x,shear_y,0)`. At height h all beads sample the same imposed
velocity, while the flow vanishes at the wall. This is the imposed-flow
approximation used by the model, not a full sphere stresslet/rotation model.
The external square-wave signal remains a force along each driven bead's local
axis and is distinct from imposed flow. Shear fields are rejected outside Blake.

In legacy `direct_traps=false` mode, coefficients include the existing H_i multiplier: for
alpha_i=2 the longitudinal spring constant is `2*H_i*kx_i`. Zero lambdas remove
the index-dependent profile but not the spacing factor. Changing exponents does
not renormalise forces or coefficient units.

The implementation uses `3*r/(32*a)` for the RPY overlap unit-dyad coefficient,
records forces at their output time and checks Cholesky failures. It does not add
steric repulsion. Direct C++ failures return nonzero status.

## Controlled junctions, logic and memory

```bash
# Four matched cases: neither drive, input only, control only, both.
python rowers.py computing --config templates/computing/junction.json --experiment templates/computing/control.json --runs 3 --cores 3 --keep --out results/control

# Control-strength response curve. Quotes protect brackets in shell arguments.
python rowers.py computing --config templates/computing/junction.json --experiment templates/computing/control.json --sweep 'drives[1].amplitude' --values '[0,1,2.5,4]' --runs 3 --cores 3 --out results/control_sweep

# The same Metropolis/Bayesian code, using the selected experiment's score.
python rowers.py optimise-advanced --config templates/computing/junction.json --experiment templates/computing/control.json --search templates/computing/search.json --method metropolis --iterations 10 --runs 3 --cores 3 --out results/control_search

python rowers.py optimise-advanced --config templates/computing/junction.json --experiment templates/computing/and.json --search templates/computing/search.json --method bayesian --initial 4 --iterations 5 --candidates 1000 --runs 3 --cores 3 --out results/logic_search

# Characterise a saved candidate through precisely the same experiment protocol.
python rowers.py computing --config results/control_search/best.json --experiment templates/computing/control.json --runs 5 --cores 3 --keep --out results/control_validation

# Timed control: compare before, during and after the control pulse.
python rowers.py computing --config templates/computing/control_pulse.json --experiment templates/computing/control_sequence.json --runs 3 --cores 3 --keep --out results/sequence

# Ring: compare early/late readout after two temporary writing drives.
python rowers.py computing --config templates/computing/ring.json --experiment templates/computing/memory.json --runs 3 --cores 3 --keep --out results/memory
```

Examples use deterministic dynamics (temperature=0), a fixed simulator seed and
Rotne-Prager mobility for fast pilot runs. Set mobility to `blake` and a valid
wall_height to study the wall. Thermal Blake retains its expensive divergence
calculation. To validate on fresh initial states, change the configuration seed
(or use --set seed NEW_INTEGER in optimisation). Reusing a seed reuses the same
initial-condition ensemble. Increasing --runs alone retains the earlier seeds
and appends new ones; it is not wholly fresh validation.

### Computing protocol JSON

Experiment files describe a set of matched simulations. They are separate from
physical configuration and search bounds. The common fields are:

- kind: control, logic or memory.
- output: a group name or list. Report the arithmetic mean of per-output-bead R.
- reference: a group/list; its FIRST bead is the phase reference. Output cannot
  contain this bead, because self-comparison would give R=1 trivially.
- period: a positive diagnostic timescale; windows must span at least twice it.
- cases: list of uniquely named cases. Each has a scoring `window: [start,stop]`.
- cases may have scales: one nonnegative amplitude multiplier per drive.
- cases may have overrides: `drives` or indexed drive fields only. They cannot
  silently change the trap physics or geometry between truth-table cases.
- optional case windows: additional [start,stop] intervals from the SAME run,
  for sequence/retention diagnostics; these do not alter the score.
- threshold: optional logic readout threshold (default 0.8).
- ring: required for memory; names/lists the beads in cyclic neighbour order.

The computing protocols use upward crossings of each bead's fixed trap reference,
projected along its stroke direction. The existing diode metric keeps its old
full-record mean-crossing convention. Phase is interpolated between confirmed
crossings with no extrapolation. R_out,in is the modulus of the time-weighted
mean of exp(i*(phi_out-phi_in)) over the requested window. Trapezoidal weights
sum to one. Pair results also include mean phase, frequency mismatch in cycles
per unit time, and confirmed slip count using the existing hysteresis detector.
Every sample in a scoring window must have defined pair phase; otherwise the
candidate fails with its input/logs retained. Low R is not used as a substitute
for an unavailable measurement. Check window length against the actual oscillator
frequencies, not only the diagnostic period.

Signal metrics additionally compare output to the FIRST drive's absolute clock,
including its configured phase. In no-drive/control-off cases this is a
hypothetical reference clock; it does not mean that an external force is active.
Constant first drives have no signal-clock metric. The score uses bead-to-bead R.

These are offline diagnostics: crossing interpolation uses a later crossing.
The window comparisons do not give a causal, high-resolution switching latency.
A high R can coexist with a nonzero lag; it does not distinguish phase-coded
bits 0 and pi. The initial logic protocol instead thresholds phase consistency.


## Files and directory layout

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

## All command families

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

## Running on a blade server

The server is a separate computer. SSH opens a terminal on it; copying files is a
separate step. You need your lab account, access to its network/VPN and the assigned
storage directory. Change a temporary password after login and never put passwords
in source files or run scripts.

Copy this source folder and the small configuration/checkpoint files needed for your
task into your assigned directory under `/data`. Build and install there using the
same instructions above. A Mac executable will not run on Linux. Rebuild on each
machine because the Makefile enables native CPU instructions.

If your lab uses a scheduler, submit work through it. If direct jobs are permitted,
`tmux` can keep a run alive when your SSH connection closes:

```bash
# On the server, after entering the project directory:
tmux new -s rowers
source .venv/bin/activate
python -u rowers.py optimise --work results/device_7_run_001 \
  --objective fast --iterations 300 --runs 5 --cores 3 \
  > search_console.log 2>&1
```

This assumes you already prepared that work directory. Detach with **Ctrl+B, then D**.
Reconnect later with `tmux attach -t rowers`. From another terminal, inspect progress
with `tail -n 30 search_console.log`. If the project source is elsewhere, use an
absolute `--work /data/YOUR_ASSIGNED_DIRECTORY/device_7_run_001` path.

Use the worker count agreed with your lab. Visible CPU count is not an allocation.
More workers help only while there are independent repeats to run; each candidate
in this search is evaluated before proposing the next one.

## Runtime, seeds and reproducibility

For the default fast Metropolis objective, an upper bound on simulation count is

$$N_{\rm sim}=7\,n_{\rm runs}(n_{\rm iterations}+1).$$

The extra candidate is the initial geometry. Invalid proposals skip evaluation.
For 300 iterations and five repeats the bound is 10,535 simulations. If the printed
candidate evaluation takes 50.6 seconds, 301 similarly expensive evaluations would
take about 4.23 hours. That timing already includes configured repeats and concurrency;
do not multiply it by the number of repeats again. Different geometry, timestep,
noise, hardware or wall mobility can change timing substantially. Validation is extra.

| Option | Meaning |
| --- | --- |
| `--iterations` | Number of search proposals after the initial candidate in Metropolis |
| `--runs` | Independent simulation repeats per candidate or validation batch |
| `--cores` | Maximum concurrent repeat workers, not parallel Metropolis chains |
| `--proposal-seed` | Proposal RNG seed in the unified transistor interface |
| `--seed` | Simulator repeat seed in the unified transistor interface |
| `--search-temperature` | Metropolis acceptance scale, distinct from physical temperature |
| `--dt-divisors 1 2` | Validation at the saved timestep and half that timestep |
| `--points` | Dense validation/sweep grid request; required protocol points are retained |
| `--keep` | Retain successful raw trajectories instead of cleaning them up |

**The advanced optimiser uses different seed syntax:** `--seed` controls its proposal
RNG, and `--set seed INTEGER` controls simulator randomness. Unified transistor stages
use distinct default training and validation seed ranges. Checkpoint-based overlap
checks are retained. Increasing repeat count with the same starting seed reuses the
old seeds and appends new ones; it is not a completely fresh ensemble.

Save the physical configuration, protocol, search bounds, code/executable version and
seeds with results. The code records hashes and per-repeat measurements. Strict Bayesian
warm-start checks can reject older logs after source relocation even when the scoring
formula is unchanged. Starting a new run from an old `best.json` remains supported.
There is no exact Metropolis resume command.

Study timestep, observation-time and repeat-count convergence. Changing exponents does
not normalise force scales or coefficient units. In legacy trap mode, moving references
also changes the trap-strength multiplier; in direct-trap mode it does not. Fixed stroke
angles do not introduce rotational dynamics. A high optimisation score, steep coherence
curve or large dimensional susceptibility alone does not establish power gain, reliable
logic or the ability to drive another device.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `python: command not found` or missing NumPy/SciPy | Activate the intended environment; use `python3` to create it and install requirements there. |
| `Eigen/Dense` missing | Verify the complete `src/eigen-3.4.0/` directory; first-build download needs network access. |
| `Missing src/rowers` or `Build src/rowers first` | Run `make -C src` on this machine, or supply the correct `--exe` path. |
| `FileExistsError` / output already exists | Use a fresh `--out` or new experiment directory. Do not delete completed data merely to rerun a command. |
| Both `search` and `search_fast` contain winners | Pass `--config PATH_TO_CHOSEN_BEST.json`; the unified interface refuses to guess. |
| Old computing `experiment.json` rejected | It is a protocol, not the new manifest schema. Keep computing and transistor work directories separate. |
| Seed-overlap error | Choose held-out validation simulator seeds or keep the normal validation defaults. |
| Unexpected phase/frequency results from moved raw files | Keep matching `.axes` and `.dat` files together; inspect timestamps and observation-window coverage. |
| Few valid repeats or missing measurements | Inspect saved diagnostics, phase coverage and failed-run logs before interpreting means. Missing data are not successful OFF states. |
| Reports cannot find measurements | Supply a directory containing suite `results.json` and `protocol.json`; PNGs or `best.json` alone are insufficient. |
| Plot changes seem to require rerunning physics | Use `report` for suite measurements, `nonlinearity-report` for its historical format, or `diode trajectory` for retained raw trajectories. |

## Existing projects and validation

To replace code in an existing checkout, follow [MIGRATION.md](docs/MIGRATION.md).
It preserves `results/` and Git history. Existing completed simulations do not need
repeating merely because files were reorganised. The source distribution includes
no optimised user geometry or large result folder.

For an already completed fast-search validation:

```bash
python rowers.py report \
  --source results/transistor_device_7/validate_fast \
  --out results/transistor_device_7/reports_clean
```

Use your actual folder names and a fresh report destination. `validate_fast` is an
old output-folder name, not a reduced validation algorithm.

Scientific details are in [scientific_reference.md](docs/scientific_reference.md).
[VALIDATION.md](docs/VALIDATION.md) records the refactor's test scope and its skipped
physical simulator test. Tests using synthetic signals verify analysis and routing,
not hydrodynamic performance. Run the tests after building on your own machine.

[The original computing guide](docs/original_COMPUTING.md) retains deeper historical
protocol documentation. Its old `analysis/` commands still have forwarding wrappers;
use this README for the current interface. See [module_mapping.json](docs/module_mapping.json)
for old-to-new implementation locations. This package does not assign a new licence
to the existing source; preserve its ownership and attributions.

