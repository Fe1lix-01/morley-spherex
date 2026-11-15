"""Tests sin dependencia externa de 00D: extraen las funciones desde el AST.

Con un entorno MORLEY completo, ejecutar `python -m unittest discover -s tests -v`.
Estas pruebas usan datos sintéticos y NO detectan movimiento real.
"""
import ast
import datetime
import math
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
MODULE = ast.parse((HERE / '00d_validate_multiepoch.py').read_text(encoding='utf-8'))
FUNCS = [node for node in MODULE.body if isinstance(node, ast.FunctionDef) and node.name in ('obs_date', 'pair_candidates')]
namespace = {'datetime': datetime.datetime, 'timezone': datetime.timezone, 'math': math}
exec(compile(ast.Module(body=FUNCS, type_ignores=[]), '<morley_00d_functions>', 'exec'), namespace)
pair_candidates = namespace['pair_candidates']


def row(obs, release, date, wave, bw=0.03585, detector='D6'):
    return {
        'obs_id': obs, 'collection': release, 'detector': detector,
        'status': 'existing_verified', 'date_obs': date,
        'wavelength_um': wave, 'bandwidth_um': bw,
        'central_good': True, 'finite_variance_fraction_7x7': 1.0,
        'access_url': 'https://irsa.ipac.caltech.edu/example.fits',
        'cutout_file': 'outputs/data/candidates_05/example.fits',
    }


class TestPairLogic(unittest.TestCase):
    def test_dr1_dr1_eligible(self):
        records = [
            row('a', 'spherex_dr1', '2026-04-20T00:00:00Z', 4.55662825),
            row('b', 'spherex_dr1', '2026-05-10T00:00:00Z', 4.55645510),
        ]
        result = pair_candidates(records, days_min=14, mismatch_max=.25)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'PRECHECK_PASS_NEEDS_CALIBRATION')
        self.assertAlmostEqual(result[0]['relative_mismatch'], 0.00483, places=4)
        self.assertFalse(result[0]['ready_for_zogy'])

    def test_all_unique_pairs(self):
        records = [
            row(str(i), 'spherex_dr1' if i < 3 else 'spherex_qr3',
                f'2026-04-{i+10:02d}T00:00:00Z', 4.5 + i * .01)
            for i in range(6)
        ]
        self.assertEqual(len(pair_candidates(records, days_min=0)), 15)

    def test_incompatible_detector_excluded(self):
        records = [
            row('a', 'spherex_dr1', '2026-04-01T00:00:00Z', 4.55),
            row('b', 'spherex_qr3', '2026-05-01T00:00:00Z', 4.55, detector='D5'),
        ]
        self.assertEqual(pair_candidates(records), [])

    def test_time_block_not_approved(self):
        records = [
            row('a', 'spherex_dr1', '2026-04-01T00:00:00Z', 4.55),
            row('b', 'spherex_dr1', '2026-04-02T00:00:00Z', 4.55),
        ]
        self.assertEqual(pair_candidates(records, days_min=14)[0]['status'], 'BLOCKED_TIME_POLICY')


if __name__ == '__main__':
    unittest.main()
