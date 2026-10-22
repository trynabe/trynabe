import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec=importlib.util.spec_from_file_location('renderer', ROOT / 'scripts/render_profile_gif.py')
renderer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class TimingTests(unittest.TestCase):
    def test_loop_has_symmetric_1300ms_transitions(self):
        seq=renderer.frames_for_loop()
        peak=next(i for i,(t,_) in enumerate(seq) if t==1)
        forward=[round(t,6) for t,_ in seq[1:peak]]
        backward=[round(t,6) for t,_ in seq[peak+1:]]
        self.assertEqual(forward, list(reversed(backward)))
        self.assertEqual(sum(ms for _,ms in seq[1:peak+1]),3700)
        self.assertEqual(seq[0],(0.0,1150))
        self.assertEqual(seq[peak],(1.0,2450))
        self.assertEqual(sum(ms for _,ms in seq),6100)

    def test_unverified_input_cannot_overwrite_existing_assets(self):
        base={'username':'trynabe','generatedAt':'2026-10-20T12:00:00Z','days':[{'date':'2026-10-20','count':3}],'stats':{'total':3}}
        scratch=ROOT/'test-results'
        scratch.mkdir(exist_ok=True)
        for changes in ({},{'isDemo':True},{'isDemo':False,'username':'demo'}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory(dir=scratch) as name:
                root=Path(name)
                assert root.resolve().is_relative_to(scratch.resolve())
                (root/'contributions.json').write_text(json.dumps({**base,**changes}),encoding='utf8')
                sentinel=root/'contribution-skyline.gif'
                sentinel.write_bytes(b'previous verified asset')
                with patch.object(renderer,'ROOT',root), self.assertRaises(SystemExit):
                    renderer.render()
                self.assertEqual(sentinel.read_bytes(),b'previous verified asset')


if __name__=='__main__':
    unittest.main()
