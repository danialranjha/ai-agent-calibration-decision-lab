"""A synthetic mathematical audit. No models, network, prompts or external actions."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIE_TOLERANCE = 1e-12


def rescale(p, temperature):
    if not (math.isfinite(p) and 0 < p < 1):
        raise ValueError("score must be finite and strictly between zero and one")
    if not (math.isfinite(temperature) and temperature > 0):
        raise ValueError("temperature must be finite and positive")
    if temperature == 1:
        return p
    z = (math.log(p) - math.log1p(-p)) / temperature
    q = 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))
    if not 0 < q < 1:
        raise ValueError("floating-point saturation outside this audit's supported domain")
    return q


def metrics(rows, scores, decisions):
    n = len(rows)
    attacks = sum(r['label'] for r in rows)
    benign = n - attacks
    fn = sum(r['label'] == 1 and decisions[r['id']] == 0 for r in rows)
    fp = sum(r['label'] == 0 and decisions[r['id']] == 1 for r in rows)
    return {
        'n': n, 'attack_labels': attacks, 'benign_labels': benign,
        'fn': fn, 'fp': fp,
        'fnr': fn / attacks if attacks else None,
        'fpr': fp / benign if benign else None,
        'brier': sum((scores[r['id']] - r['label']) ** 2 for r in rows) / n,
        'log_loss': -sum(math.log(scores[r['id']]) if r['label'] else
                         math.log1p(-scores[r['id']]) for r in rows) / n,
    }


def groups(scores, uncertainty=False):
    value = (lambda i: abs(scores[i] - .5)) if uncertainty else scores.__getitem__
    ordered = sorted(scores, key=lambda i: (value(i), i))
    result = []
    anchor = None
    for i in ordered:
        v = value(i)
        if anchor is None or not math.isclose(v, anchor, rel_tol=0, abs_tol=TIE_TOLERANCE):
            result.append([])
            anchor = v
        result[-1].append(i)
    return [sorted(g) for g in result]


def routes(scores, lower, upper):
    if not 0 < lower < upper < 1:
        raise ValueError('ordered interior boundaries required')
    return {i: ('ALLOW' if p < lower else 'BLOCK' if p >= upper else 'REVIEW')
            for i, p in scores.items()}


def review_curve(rows, scores):
    decisions = {i: int(p >= .5) for i, p in scores.items()}
    reviewer = {r['id']: r['reviewer'] for r in rows}
    trace, selected = [], []
    def capture():
        m = metrics(rows, scores, decisions)
        trace.append({'reviewed_ids': sorted(selected), 'reviewed_count': len(selected),
                      'decisions': dict(sorted(decisions.items())),
                      'fn': m['fn'], 'fp': m['fp'],
                      'attack_labels': m['attack_labels'], 'benign_labels': m['benign_labels'],
                      'n': m['n']})
    capture()
    for group in groups(scores, uncertainty=True):
        for i in group:
            decisions[i] = reviewer[i]
            selected.append(i)
        capture()
    return trace


def run():
    fixtures = json.loads((ROOT / 'fixtures.json').read_text())
    results = {}
    for name, rows in fixtures['cohorts'].items():
        if len({r['id'] for r in rows}) != len(rows):
            raise ValueError('duplicate fixture IDs')
        if any(r['label'] not in (0, 1) or r['reviewer'] not in (0, 1) for r in rows):
            raise ValueError('binary labels/reviewer decisions required')
        variants = []
        for t in fixtures['temperatures']:
            scores = {r['id']: rescale(r['score'], t) for r in rows}
            decisions = {i: int(p >= .5) for i, p in scores.items()}
            variants.append({
                'temperature': t, 'scores': scores,
                'decisions_at_half': decisions, 'metrics': metrics(rows, scores, decisions),
                'score_groups': groups(scores), 'uncertainty_groups': groups(scores, True),
                'review_curve': review_curve(rows, scores),
                'fixed_interval': {'lower': .2, 'upper': .8, 'routes': routes(scores, .2, .8)},
                'remapped_interval': {
                    'lower': rescale(.2, t), 'upper': rescale(.8, t),
                    'routes': routes(scores, rescale(.2, t), rescale(.8, t))},
            })
        results[name] = variants
    return {
        'scope': fixtures['provenance'], 'method': 'sigmoid(logit(p)/T), positive scalar T fixed in advance',
        'tie_tolerance': TIE_TOLERANCE,
        'note': 'Numerically close values are grouped; fixture distinct-distance gaps exceed tolerance. No endpoint clipping.',
        'cohort_count': len(results), 'fixture_count': sum(map(len, fixtures['cohorts'].values())),
        'score_records': sum(len(rows) * len(fixtures['temperatures']) for rows in fixtures['cohorts'].values()),
        'cohorts': results,
    }


def evidence(result):
    lines = ['# Exact synthetic evidence', '',
             'Invented labels, scores and reviewer decisions. No model ran; no temperature was fitted.', '',
             '## Main cohort: 8 examples, 4 attack-labeled and 4 benign-labeled', '',
             '| T | Squared probability error (Brier) | Log loss | Misses / 4 | False blocks / 4 |',
             '|---:|---:|---:|---:|---:|']
    for v in result['cohorts']['main']:
        m = v['metrics']
        lines.append(f"| {v['temperature']:g} | {m['brier']:.6f} | {m['log_loss']:.6f} | {m['fn']} | {m['fp']} |")
    raw = next(v for v in result['cohorts']['main'] if v['temperature'] == 1)
    scaled = next(v for v in result['cohorts']['main'] if v['temperature'] == 2)
    lines += ['', '## Exact decisions at the fixed 0.5 cutoff', '',
              '| ID | Original score | T=2 score | Original verdict | T=2 verdict |',
              '|---|---:|---:|---|---|']
    for i, p in raw['scores'].items():
        a = 'BLOCK' if raw['decisions_at_half'][i] else 'ALLOW'
        b = 'BLOCK' if scaled['decisions_at_half'][i] else 'ALLOW'
        lines.append(f"| {i} | {p:.6f} | {scaled['scores'][i]:.6f} | {a} | {b} |")
    lines += ['', 'A and C have attack labels but remain allowed. F and H have benign labels but remain blocked.',
              'B and D remain correctly allowed; E and G remain correctly blocked.', '',
              '## Ranked review and policy boundaries', '',
              f"Main review order (tied groups): {raw['uncertainty_groups']}. T=2 has the same order and exact decision trace.",
              'The reviewer decisions are fixed fixtures, not live model outputs or an error-free oracle.',
              'Reviewing G introduces a miss: more review need not monotonically reduce misses with this invented reviewer.', '',
              '| ID | Original [0.2,0.8) | T=2, same numbers | T=2, transformed boundaries |',
              '|---|---|---|---|']
    for i in raw['scores']:
        lines.append(f"| {i} | {raw['fixed_interval']['routes'][i]} | {scaled['fixed_interval']['routes'][i]} | {scaled['remapped_interval']['routes'][i]} |")
    lines += ['', f"Transformed boundaries: {scaled['remapped_interval']['lower']:.12f}, {scaled['remapped_interval']['upper']:.12f}.",
              'The unchanged [0.2,0.8) numbers change review workload. Transforming scores and boundaries together preserves routes.', '',
              '## Limits and counterexamples', '',
              'The already_correct cohort has perfect original verdicts: softening its scores worsens probability error.',
              'The equal_score_twins cohort gives identical scores to opposite labels; scaling cannot separate them.',
              'The boundary cohort retains the stated >=0.5 block convention, including the exact midpoint.',
              'These selected fixtures are not attack rates, calibrated deployment estimates or a paper reproduction.',
              'Interior scores and moderate positive temperatures only; finite precision, clipping and arbitrary policies require separate checks.']
    return '\n'.join(lines) + '\n'


def main():
    result = run()
    out = ROOT / 'artifacts'
    out.mkdir(exist_ok=True)
    (out / 'run.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    (out / 'evidence.md').write_text(evidence(result))
    print(json.dumps({'fixtures': result['fixture_count'], 'score_records': result['score_records'],
                      'main': [{ 'T': v['temperature'], **v['metrics']} for v in result['cohorts']['main']]}, indent=2))


if __name__ == '__main__':
    main()
