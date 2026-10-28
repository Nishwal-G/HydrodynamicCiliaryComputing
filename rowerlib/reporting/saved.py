"""Regenerate reports from saved measurements without invoking the simulator."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rowerlib.reporting.transistor import transfer_report,phase_report,cycle_report,mean_sem,trace_plots
from rowerlib.measurements.transistor import valid,locked,probability
from rowerlib.simulation import load_configuration


def read(path):return json.loads(path.read_text())


def regenerate(source,output):
    source=Path(source).resolve();output=Path(output).resolve()
    if not source.is_dir():raise ValueError(f'Input directory not found: {source}')
    if output.exists():raise ValueError(f'Report output exists: {output}; choose a fresh --out')
    batches=[p for p in sorted(source.rglob('results.json')) if (p.parent/'protocol.json').is_file()]
    maps=sorted(source.rglob('map_results.json'));robust=sorted(source.rglob('robustness_summary.json'))
    if not (batches or maps or robust):raise ValueError('No saved transistor measurements found; expected results.json and protocol.json together')
    output.mkdir(parents=True);audit=[];summary=[]
    for path in batches:
        records=read(path);protocol=read(path.parent/'protocol.json')
        if not records:continue
        rel=path.parent.relative_to(source);target=output/rel;target.mkdir(parents=True,exist_ok=True)
        keys=records[0]
        if 'transfer' in keys:transfer_report(records,protocol,target)
        if keys.get('phase') is not None:phase_report(records,protocol,target)
        if keys.get('cycles') is not None:cycle_report(records,protocol,target)
        trace_plots(path.parent,protocol,target)
        audit.append({'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'protocol_sha256':hashlib.sha256((path.parent/'protocol.json').read_bytes()).hexdigest(),
            'repeats':len(records),'report':str(rel)})
        if 'transfer' not in keys:continue
        for i,row in enumerate(keys['transfer']):
            for bead in row['driven']['outputs']:
                ms=[r['transfer'][i]['driven']['outputs'][bead] for r in records]
                m,sem,n=mean_sem([x['phase_consistency_R'] for x in ms if valid(x)])
                prob=probability([locked(x,protocol['criteria']) if valid(x) else None for x in ms])
                summary.append({'dataset':str(rel),'bead':bead,'control_amplitude':row['amplitude'],
                    'R_mean':m,'R_sem':sem,'valid_repeats':n,'total_repeats':len(ms),'locked_fraction_all':prob['fraction_all']})
    if summary:
        with (output/'transfer_comparison.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
        for bead in sorted({r['bead'] for r in summary}):
            datasets=sorted({r['dataset'] for r in summary if r['bead']==bead and not any(
                part.startswith(('frequency_','stiffness_')) for part in Path(r['dataset']).parts)})
            if not datasets:continue
            fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
            for dataset in datasets:
                rows=sorted([r for r in summary if r['bead']==bead and r['dataset']==dataset],key=lambda r:r['control_amplitude'])
                x=[r['control_amplitude'] for r in rows]
                axes[0].errorbar(x,[np.nan if r['R_mean'] is None else r['R_mean'] for r in rows],
                    yerr=[r['R_sem'] or 0 for r in rows],marker='o',label=dataset)
                axes[1].plot(x,[r['locked_fraction_all'] for r in rows],'o-',label=dataset)
            for ax,label in zip(axes,['Coherence to input clock','Locked / all repeats']):
                ax.set(xlabel='Control force amplitude',ylabel=label,ylim=(-.03,1.03));ax.grid(alpha=.2)
            axes[0].legend(fontsize=7);fig.suptitle(f'Output {bead}: saved datasets (check protocols before comparison)')
            fig.savefig(output/f'output_{bead}_comparison.png',dpi=150);plt.close(fig)
    for path in maps:
        from rowerlib.experiments.transistor import map_report
        records=read(path)
        if not records:continue
        # Choose frequency_0 explicitly; lexicographic order is unsafe with >9 cells.
        cells=sorted(path.parent.glob('frequency_0_control_*/source_configuration.json'))
        if not cells:raise ValueError(f'Missing saved map cell configurations: {path.parent}')
        base=load_configuration(cells[0]);ratio=records[0]['frequency_ratio']
        base=base.updated(**{'drives[0].period':base.values['drives'][0]['period']*ratio})
        dest=output/path.parent.relative_to(source);dest.mkdir(parents=True,exist_ok=True)
        map_report(records,base,dest)
        audit.append({'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    for path in robust:
        rows=read(path);dest=output/path.parent.relative_to(source);dest.mkdir(parents=True,exist_ok=True)
        for bead in sorted({r['bead'] for r in rows}):
            fig,ax=plt.subplots(figsize=(7,4),layout='constrained')
            for d in sorted({r['stiffness_fraction'] for r in rows}):
                selected=sorted([r for r in rows if r['bead']==bead and r['stiffness_fraction']==d],key=lambda r:r['temperature'])
                ax.plot([r['temperature'] for r in selected],[r['fraction_all'] for r in selected],'o-',label=f'Stiffness +/- {100*d:g}%')
            ax.set(xlabel='Simulator temperature',ylabel='All gating targets / all repeats',ylim=(-.03,1.03));ax.legend()
            fig.savefig(dest/f'robustness_{bead}.png',dpi=150);plt.close(fig)
        audit.append({'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (output/'sources.json').write_text(json.dumps(audit,indent=2)+'\n')
    figures=sorted(output.rglob('*.png'))
    (output/'README.md').write_text('# Saved-data reports\n\nNo simulations were run. Partial runs use the available repeats; inspect sources.json.\n\n'
        'Comparison curves retain datasets separately. Check protocols, geometries, windows and sample sizes before drawing comparisons. '
        'Full validation scores are not comparable to fast search scores.\n\n'
        +'\n'.join(f'- [{p.relative_to(output)}]({p.relative_to(output).as_posix()})' for p in figures)+'\n')
    return {'batches':len(batches),'maps':len(maps),'robustness':len(robust),'figures':len(figures),'output':str(output)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,help='Experiment directory; default source and output parent')
    p.add_argument('--source',type=Path,help='Existing results directory; old validate_fast folders are supported')
    p.add_argument('--out',type=Path,help='Fresh report directory; default WORK/reports')
    a=p.parse_args(argv)
    if a.work is None and (a.source is None or a.out is None):p.error('Supply --work or both --source and --out')
    print(json.dumps(regenerate(a.source or a.work,a.out or a.work/'reports'),indent=2))
