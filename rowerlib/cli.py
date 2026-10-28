"""One user interface; existing scientific protocols remain the implementation."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import sys
import tempfile
from rowerlib.paths import PROJECT_ROOT, MODULES

STAGES = ('prepare','baseline','optimise','validate','gating','amplitude','phase','cycles','locking-map','robustness')
TOOLS = {
    'optimise-advanced':'optimisation', 'computing':'experiments',
    'diode':'diode_characterisation', 'disorder':'disorder',
    'switch':'run_signal_switch', 'diagnose-switch':'diagnose_switch',
    'larger-switch':'larger_switch', 'offset-search':'run_offset_search',
    'drive-sweep':'sweep_switch_drive', 'switch-cycles':'run_signal_switch',
    'switch-load':'switch_load', 'nonlinearity':'control_nonlinearity',
    'nonlinearity-report':'control_nonlinearity_plots', 'legacy-transistor':'run_transistor',
}


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path=Path(path)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    tmp.replace(path)


@contextmanager
def argv_for(name, args):
    old=sys.argv
    sys.argv=[name,*map(str,args)]
    try:yield
    finally:sys.argv=old


def call_tool(name, args):
    module=importlib.import_module('rowerlib.'+MODULES[name])
    with argv_for(name,args):return module.main()


def option(args,name):
    for i,v in enumerate(args):
        if v==name:
            if i+1>=len(args):raise ValueError(f'{name} requires a value')
            return args[i+1]
        if v.startswith(name+'='):return v.split('=',1)[1]
    return None


def relative(path, work):
    try:return str(Path(path).resolve().relative_to(work.resolve()))
    except ValueError:return str(Path(path).resolve())


def resolve_record(path,work):
    path=Path(path)
    return path if path.is_absolute() else work/path


def select_winner(work,manifest):
    record=manifest.get('stages',{}).get('optimise',{})
    if record.get('output'):
        path=resolve_record(record['output'],work)/'best.json'
        if path.is_file():return path
        raise ValueError(f'Recorded search has no best.json yet: {path}')
    choices=[p for p in (work/'search/best.json',work/'search_fast/best.json') if p.is_file()]
    if len(choices)==1:return choices[0]
    if not choices:raise ValueError('No saved winner found. Run optimise or supply --config PATH.')
    raise ValueError('Both search and search_fast have winners. Supply --config explicitly; neither is chosen silently.')


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h','--help'):
        print('Usage: python rowers.py COMMAND [options]\n\nTransistor workflow:\n  '+', '.join(STAGES)+'\n  report (saved measurements only)\n\nOther preserved tools:\n  '+', '.join(TOOLS)+'\n\nUse COMMAND --help for options. Paths are relative to your current directory.\nSee README.md for the complete workflow and migration instructions.')
        return
    command=argv.pop(0)
    if command in TOOLS:
        if command=='switch-cycles':argv=['--stage','cycles',*argv]
        return call_tool(TOOLS[command],argv)
    if command=='report':
        from rowerlib.reporting.saved import main as report_main
        return report_main(argv)
    if command not in STAGES:raise SystemExit(f'Unknown command {command!r}; use --help.')
    p=argparse.ArgumentParser(prog=f'python rowers.py {command}',add_help=False)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--objective',choices=('fast','full','legacy'),default=None)
    p.add_argument('--legacy-protocol',type=Path)
    if '-h' in argv or '--help' in argv:
        print('Unified options: --objective fast|full|legacy (optimise only; default fast)\n'
              '--legacy-protocol PATH (required for legacy optimisation)\n'
              'New experiments use experiment.json; old work folders are accepted.\n'
              'Default output: search/, validation/, locking_map/, or the stage name.\n')
        from rowerlib.experiments.transistor import main as suite
        try:suite(['--help'])
        except SystemExit as e:
            if e.code:raise
        return
    a,extra=p.parse_known_args(argv)
    if command!='optimise' and (a.objective is not None or a.legacy_protocol is not None):
        p.error('--objective and --legacy-protocol apply only to optimise')
    if a.legacy_protocol and a.objective!='legacy':p.error('--legacy-protocol requires --objective legacy')
    work=a.work.resolve();manifest_path=work/'experiment.json'
    manifest=read(manifest_path) if manifest_path.exists() else {}
    if manifest and manifest.get('schema_version')!=1:raise ValueError('Unsupported experiment.json schema version')
    if option(extra,'--stage') is not None:raise ValueError('Use the command name, not --stage, in the unified interface')
    from rowerlib.experiments.transistor import main as suite
    if command=='prepare':
        if a.objective is not None:p.error('Select the objective at optimise time')
        suite(['--stage','prepare','--work',str(work),*extra])
        manifest={'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),
            'configuration':read(work/'start.json')['configuration'],
            'source_configuration':read(work/'source.json')['configuration'],
            'device':read(work/'device.json'),'search':read(work/'search.json'),
            'fast':read(PROJECT_ROOT/'templates/computing/transistor_fast.json'),
            'preparation':read(work/'preparation.json'),'stages':{}}
        write(manifest_path,manifest)
        for name in ('start.json','source.json','device.json','search.json','preparation.json'):
            (work/name).unlink()
        print(f'Experiment settings: {manifest_path}\nEdit this file before running the baseline/search.')
        return
    if not work.is_dir():raise ValueError(f'Work directory does not exist: {work}')
    if not manifest:
        # Add navigation metadata without changing any old configuration or result.
        manifest={'schema_version':1,'imported_legacy_work':True,'stages':{}}
    if command=='optimise' and (work/'search').exists() and option(extra,'--out') is None:
        raise ValueError('search/ already exists. Use a new experiment or --out NEW_DIRECTORY; this is not a resume command.')
    objective=a.objective or 'fast'
    stage='optimise-fast' if command=='optimise' and objective=='fast' else command
    output=Path(option(extra,'--out') or work/({'optimise':'search','validate':'validation','locking-map':'locking_map'}.get(command,command))).resolve()
    if output.exists():raise ValueError(f'Output already exists: {output}. Supply a fresh --out; existing results are protected.')
    args=['--stage',stage,'--work',str(work),'--unified-layout',*extra]
    if option(extra,'--out') is None:args+=['--out',str(output)]
    if option(extra,'--exe') is None:args+=['--exe',str(PROJECT_ROOT/'src/rowers')]
    with tempfile.TemporaryDirectory(prefix='rower-settings-') as temp:
        temp=Path(temp)
        if 'configuration' in manifest:
            files={'start':{'configuration':manifest['configuration']},'device':manifest['device'],
                   'search':manifest['search'],'fast':manifest['fast']}
            for key,value in files.items():write(temp/(key+'.json'),value)
            if option(extra,'--config') is None and command in ('baseline','optimise'):args+=['--config',str(temp/'start.json')]
            if option(extra,'--protocol') is None and command in ('baseline','optimise'):args+=['--protocol',str(temp/'device.json')]
            if command=='optimise':
                if option(extra,'--search-spec') is None:args+=['--search-spec',str(temp/'search.json')]
                if objective=='fast' and option(extra,'--fast-spec') is None:args+=['--fast-spec',str(temp/'fast.json')]
        if command not in ('baseline','optimise') and option(extra,'--config') is None:
            args+=['--config',str(select_winner(work,manifest))]
        # A legacy checkpoint may have no embedded device protocol.
        if command not in ('baseline','optimise') and option(extra,'--protocol') is None and 'device' in manifest:
            rec=read(option(args,'--config'));rec=rec.get('best',rec)
            if not rec.get('protocol',{}).get('device'):args+=['--protocol',str(temp/'device.json')]
        record={'output':relative(output,work),'status':'running','started_utc':datetime.now(timezone.utc).isoformat(),
                'arguments':[command,*argv]}
        if command=='optimise':record['objective']=objective
        manifest.setdefault('stage_history',[]).append(record)
        manifest.setdefault('stages',{})[command]=record
        write(manifest_path,manifest)
        try:
            if command=='optimise' and objective=='legacy':
                if a.legacy_protocol is None:raise ValueError('--objective legacy requires --legacy-protocol PATH')
                # Preserve the historical coherence objective and generic optimiser options.
                passed=['--transistor',str(a.legacy_protocol),'--out',str(output),
                    '--config',option(args,'--config') or str(work/'start.json'),
                    '--search',option(args,'--search-spec') or str(work/'search.json'),
                    '--exe',option(args,'--exe')]
                defaults={'--iterations':'300','--runs':'3','--cores':'3','--method':'metropolis','--search-temperature':'0.05'}
                for flag,value in defaults.items():
                    if option(extra,flag) is None:passed += [flag,value]
                accepted={'--iterations','--runs','--cores','--method','--search-temperature','--proposal-seed','--seed'}
                for flag in accepted:
                    v=option(extra,flag)
                    if v is not None:
                        if flag=='--proposal-seed':passed+=['--seed',v]
                        elif flag=='--seed':passed+=['--set','seed',v]
                        else:passed += [flag,v]
                if option(extra,'--proposal-seed') is None:passed+=['--seed','42']
                if option(extra,'--seed') is None:passed+=['--set','seed','145250000']
                if '--keep' in extra:passed+=['--keep']
                # Reject unsupported options rather than silently ignoring them.
                allowed=accepted|{'--config','--search-spec','--exe','--out','--keep'}
                for token in extra:
                    if token.startswith('--') and token.split('=')[0] not in allowed:raise ValueError(f'Unsupported legacy option: {token}; use optimise-advanced for other options')
                call_tool('optimisation',passed)
            else:suite(args)
        except BaseException as e:
            record.update(status='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',error=str(e))
            write(manifest_path,manifest)
            raise
        else:
            record.update(status='complete',finished_utc=datetime.now(timezone.utc).isoformat())
            write(manifest_path,manifest)
