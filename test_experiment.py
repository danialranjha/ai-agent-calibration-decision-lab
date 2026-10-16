import json
import math
import unittest
from unittest.mock import patch
import experiment as e


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = e.run()

    def test_independent_odds_root(self):
        for p in [.01, .02, .1, .21, .49, .5, .51, .55, .76, .88, .97]:
            expected = math.sqrt(p) / (math.sqrt(p) + math.sqrt(1-p))
            self.assertAlmostEqual(e.rescale(p, 2), expected, places=14)

    def test_invariant_decisions_ranks_and_review(self):
        for cohort in self.result['cohorts'].values():
            raw = next(v for v in cohort if v['temperature'] == 1)
            for variant in cohort:
                for key in ['decisions_at_half', 'score_groups', 'uncertainty_groups', 'review_curve']:
                    with self.subTest(t=variant['temperature'], key=key):
                        self.assertEqual(variant[key], raw[key])

    def test_main_probability_error_changes_but_misses_do_not(self):
        raw, scaled = self.result['cohorts']['main'][1:3]
        self.assertLess(scaled['metrics']['brier'], raw['metrics']['brier'])
        self.assertLess(scaled['metrics']['log_loss'], raw['metrics']['log_loss'])
        self.assertEqual(raw['metrics']['fn'], 2)
        self.assertEqual(raw['metrics']['fp'], 2)
        self.assertEqual(scaled['metrics']['fn'], 2)
        self.assertEqual(scaled['metrics']['fp'], 2)
        self.assertEqual(raw['metrics']['attack_labels'], 4)
        self.assertEqual(raw['metrics']['benign_labels'], 4)

    def test_already_correct_counterexample(self):
        raw, scaled = self.result['cohorts']['already_correct'][1:3]
        for key in ['brier', 'log_loss']:
            self.assertGreater(scaled['metrics'][key], raw['metrics'][key])
        self.assertEqual(raw['metrics']['fn'] + raw['metrics']['fp'], 0)

    def test_equal_scores_cannot_separate_opposite_labels(self):
        for v in self.result['cohorts']['equal_score_twins']:
            self.assertEqual(v['scores']['N'], v['scores']['O'])
            self.assertEqual(v['scores']['P'], v['scores']['Q'])
            self.assertEqual(v['metrics']['fn'], 1)
            self.assertEqual(v['metrics']['fp'], 1)

    def test_boundary_convention(self):
        for v in self.result['cohorts']['boundary']:
            self.assertEqual(v['decisions_at_half'], {'R': 0, 'S': 1, 'U': 1})
            self.assertEqual(v['scores']['S'], .5)

    def test_interval_counterexample_and_remapping(self):
        for cohort in self.result['cohorts'].values():
            raw = next(v for v in cohort if v['temperature'] == 1)
            for v in cohort:
                self.assertEqual(v['remapped_interval']['routes'], raw['fixed_interval']['routes'])
        raw, scaled = self.result['cohorts']['main'][1:3]
        self.assertNotEqual(raw['fixed_interval']['routes'], scaled['fixed_interval']['routes'])
        self.assertEqual(raw['fixed_interval']['routes']['G'], 'BLOCK')
        self.assertEqual(scaled['fixed_interval']['routes']['G'], 'REVIEW')
        self.assertEqual(scaled['remapped_interval']['routes']['G'], 'BLOCK')

    def test_imperfect_reviewer_and_full_denominators(self):
        curve = self.result['cohorts']['main'][1]['review_curve']
        self.assertEqual(curve[-1]['reviewed_count'], 8)
        self.assertEqual(curve[-1]['fn'], 1)
        self.assertEqual(curve[-1]['fp'], 0)
        self.assertTrue(any(b['fn'] > a['fn'] for a,b in zip(curve, curve[1:])))
        self.assertTrue(all(v['n'] == 8 and v['attack_labels'] == 4 for v in curve))

    def test_interval_endpoints(self):
        for t in [.5, 1, 2, 4]:
            scores = {i: e.rescale(p, t) for i,p in [('lower',.2),('upper',.8)]}
            self.assertEqual(e.routes(scores, e.rescale(.2,t), e.rescale(.8,t)),
                             {'lower': 'REVIEW', 'upper': 'BLOCK'})

    def test_invalid_transform_domain(self):
        for t in [0, -1, math.inf, math.nan]:
            with self.assertRaises(ValueError): e.rescale(.2, t)
        for p in [0, 1, -1, math.nan, math.inf]:
            with self.assertRaises(ValueError): e.rescale(p, 2)

    def test_identity_and_counts(self):
        f = json.loads((e.ROOT / 'fixtures.json').read_text())
        self.assertEqual(self.result['fixture_count'], 19)
        self.assertEqual(self.result['score_records'], 76)
        for rows in f['cohorts'].values():
            for r in rows: self.assertEqual(e.rescale(r['score'], 1), r['score'])


if __name__ == '__main__':
    unittest.main()
