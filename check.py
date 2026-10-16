"""Focused checks and two intentional faults; never modifies source on disk."""
import io
import json
import unittest
from unittest.mock import patch
from pathlib import Path
import experiment
import test_experiment


def suite_result():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_experiment.AuditTests)
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    return {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
            'passed': result.wasSuccessful()}


def main():
    baseline = suite_result()
    with patch.object(experiment, 'rescale', side_effect=lambda p,t: p):
        no_scaling = suite_result()
    original = experiment.metrics
    def hide_misses(rows, scores, decisions):
        result = original(rows, scores, decisions)
        result['fn'] = 0
        result['fnr'] = 0
        return result
    with patch.object(experiment, 'metrics', side_effect=hide_misses):
        hidden_misses = suite_result()
    result = {'baseline': baseline,
              'faults': {'skip_scaling': no_scaling, 'hide_misses': hidden_misses},
              'faults_detected': all(not x['passed'] and x['failures'] > 0 and x['errors'] == 0
                                     for x in [no_scaling, hidden_misses])}
    target = Path(__file__).resolve().parent / 'artifacts' / 'checks.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2))
    if not baseline['passed'] or not result['faults_detected']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
