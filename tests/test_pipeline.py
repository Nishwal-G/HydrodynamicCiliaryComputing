"""Integration checks for unified commands using synthetic trajectories."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'analysis'))
from rowerlib.cli import main,select_winner
from rowerlib.reporting.saved import regenerate
from test_transistor_device import protocol,source,fake_simulate
from rowerlib.simulation import save_json
from rowerlib.optimisation import main as optimise_main

class PipelineTests(unittest.TestCase):
    def test_alias_is_same_module(self):
        import transistor_fast
        from rowerlib.objectives import fast
        self.assertIs(transistor_fast,fast)

    def test_ambiguous_old_winners_require_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for name in ('search','search_fast'):
                (p/name).mkdir();(p/name/'best.json').write_text('{}')
            with self.assertRaises(ValueError):select_winner(p,{})
            self.assertEqual(select_winner(p,{'stages':{'optimise':{'output':'search_fast'}}}),p/'search_fast/best.json')

    def test_full_and_legacy_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            with patch('rowerlib.experiments.transistor.main') as suite:
                main(['optimise','--work',str(work),'--objective','full','--method','bayesian'])
            args=suite.call_args.args[0]
            self.assertEqual(args[args.index('--stage')+1],'optimise')
            self.assertEqual(args[args.index('--method')+1],'bayesian')
            with patch('rowerlib.cli.call_tool') as tool:
                main(['optimise','--work',str(work),'--objective','legacy','--legacy-protocol','legacy.json'])
            name,args=tool.call_args.args
            self.assertEqual(name,'optimisation')
            self.assertEqual(args[args.index('--transistor')+1],'legacy.json')
            self.assertEqual(args[args.index('--iterations')+1],'300')
            self.assertEqual(args[args.index('--seed')+1],'42')
            self.assertIn('145250000',args)

    def test_complete_pipeline_and_report_without_simulator(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);work=p/'device';exe=p/'fake';exe.write_text('fingerprint only')
            save_json(p/'source.json',{'configuration':source().values})
            save_json(p/'protocol.json',protocol())
            main(['prepare','--work',str(work),'--config',str(p/'source.json'),'--protocol',str(p/'protocol.json')])
            manifest=json.loads((work/'experiment.json').read_text())
            self.assertEqual(manifest['device'],protocol())
            self.assertFalse((work/'device.json').exists())
            def launch(command,check):
                with patch.object(sys,'argv',command[1:]):optimise_main()
            with patch('rowerlib.objectives.fast.simulate',side_effect=fake_simulate),patch('rowerlib.experiments.transistor.subprocess.run',side_effect=launch):
                main(['optimise','--work',str(work),'--exe',str(exe),'--iterations','0','--runs','1','--cores','1'])
            moved=p/'device_relocated';work.rename(moved);work=moved
            best=json.loads((work/'search/best.json').read_text())
            self.assertEqual(best['protocol']['simulations_per_repeat'],7)
            self.assertFalse((work/'search_fast').exists())
            with patch('rowerlib.objectives.device.simulate',side_effect=fake_simulate):
                main(['validate','--work',str(work),'--exe',str(exe),'--runs','1','--cores','1','--points','3','--dt-divisors','1'])
            full=work/'validation/dt1/full'
            self.assertTrue((full/'reports/phase_response.csv').exists())
            manifest=json.loads((work/'experiment.json').read_text())
            self.assertEqual(manifest['stages']['validate']['status'],'complete')
            self.assertEqual(manifest['stages']['optimise']['objective'],'fast')
            with patch('rowerlib.objectives.device.simulate',side_effect=fake_simulate):
                main(['locking-map','--work',str(work),'--exe',str(exe),'--runs','1','--cores','1'])
                main(['robustness','--work',str(work),'--exe',str(exe),'--runs','1','--cores','1'])
            with patch('rowerlib.objectives.device.simulate',side_effect=AssertionError('Reporting must not simulate')):
                result=regenerate(work,work/'reports')
            self.assertEqual(result['batches'],10)
            self.assertEqual(result['maps'],1)
            self.assertEqual(result['robustness'],1)
            self.assertTrue((work/'reports/locking_map/dt1/locking_map_5.png').exists())
            self.assertTrue((work/'reports/output_5_comparison.png').exists())
            self.assertEqual((full/'reports/phase_response.csv').read_text(),(work/'reports/validation/dt1/full/phase_response.csv').read_text())
            with self.assertRaises(ValueError):regenerate(work,work/'reports')
            with self.assertRaises(ValueError):main(['optimise','--work',str(work)])

if __name__=='__main__':unittest.main()
