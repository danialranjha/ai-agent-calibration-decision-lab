# AI-agent detector confidence and decision audit

Rescaling a detector's confidence can improve a probability-error metric while leaving its actual decisions unchanged. This repository demonstrates that narrow mathematical distinction with **invented scores, labels and reviewer decisions**. No model, detector, reviewer API, malicious prompt, real user data or network request runs.

The eight-example main fixture has four attack labels and four benign labels. With temperature T=2, average squared probability error falls from **0.446250 to 0.368872**, and log loss falls from **1.602878 to 1.026225**. At the unchanged 0.5 blocking cutoff, both versions still miss **2 of 4** attack-labeled examples and falsely block **2 of 4** benign-labeled examples. These are fixture counts, not measured attack rates.

## Hypothesis and motivation

For interior probabilities and a positive scalar temperature, `q = sigmoid(logit(p) / T)` preserves the score order, which side of 0.5 a score lies on, and mathematical distance-from-0.5 ordering. Therefore fixed-0.5 decisions and uncertainty-ranked review can stay identical despite different probability-error metrics. This says nothing about the quality of a fitted calibrator on unseen data.

Motivation: [From Detection to Decision, arXiv 2610.20907v1](https://arxiv.org/html/2610.20907v1), especially §§3.2–3.3 and 4.2–4.3, distinguishes probability calibration, decisions and reviewer behavior. Its large-cohort escalation result belongs to that specific study, not to this experiment. We do not reproduce its predictions or percentages.

The source's [released review implementation](https://github.com/lanqianlong/calibrated-decision-models/blob/4c30771c7d8c07890884d596512251a7cf03157e/src/security_deferral.py) orders by `abs(p - 0.5)`, replaces selected decisions with fixed reviewer decisions, and has a separate interval-policy path. [Provenance](artifacts/source.json) records the verified blob. This repository independently implements a smaller mathematical audit. No upstream code or prediction corpus is copied.

## Threat model and containment

An AI-agent system might rely on an injection detector to route untrusted content. Here its confident mistakes are explicitly assumed by assigning labels to numeric fixtures; no attacker access, successful injection or text classification is demonstrated. The labels, transform, evaluator and policy implementation remain trusted. A downstream reviewer is also an invented decision array, including an error, not an oracle or a real model.

The only sink is a local JSON record of ALLOW, BLOCK and REVIEW decisions. There are no messages, credentials, endpoints, package installations, external actions or real protected resources. All writes are the three reproducible files under `artifacts/`.

## Setup and exact commands

Python 3.9 or later, standard library only. From this directory:

```sh
python3 experiment.py
python3 -m unittest -v test_experiment
python3 check.py
```

The first command regenerates `artifacts/run.json` and `artifacts/evidence.md`. The final command runs the focused tests and two deliberate fault variants, then regenerates `artifacts/checks.json`. A successful exit requires the original tests to pass and both faults to trigger assertion failures without errors. No model download or API key is needed.

## Technical walkthrough

### What changes, and what stays fixed

- **Original scores:** T=1 leaves every invented score unchanged, then the program applies the stated decision policy.
- **Rescaled scores:** T=2 moves each score toward 0.5 before applying the same decision policy; labels and reviewer decisions stay fixed.

T=0.5 sharpens confidence and T=4 softens further as additional controls. These temperatures were fixed before the run, not selected by optimizing fixture labels. Calling this a rescaling experiment is deliberate: no calibration parameters were trained and no held-out calibration quality was established.

| Main fixture, 8 examples | Original T=1 | Rescaled T=2 |
|---|---:|---:|
| Average squared probability error (Brier) | 0.446250 | 0.368872 |
| Average log loss | 1.602878 | 1.026225 |
| Attack-labeled examples allowed | 2 / 4 | 2 / 4 |
| Benign-labeled examples blocked | 2 / 4 | 2 / 4 |
| Example A score | 0.010000 | 0.091325 |
| Example A decision | ALLOW | ALLOW |

Example A is assigned the attack label. Its score rises, which reduces its probability error, but remains below the blocking cutoff. A and C are still the missed IDs. F and H are still the falsely blocked IDs. The other four retain their correct decisions.

The [exact table](artifacts/evidence.md) and [machine-readable record](artifacts/run.json) expose every value and decision rather than just aggregate metrics. Across four cohorts there are **19 selected examples × 4 temperatures = 76 score records**; this is not 76 independent observations of attack behavior.

### Why the invariant holds

The logit and sigmoid functions are increasing, and division by a positive T preserves order. Logit(0.5)=0, so the 0.5 crossing stays fixed. The transform is symmetric around 0.5, so the order of distances from that midpoint is preserved mathematically too. No new textual feature or label information is introduced.

The fixture implementation groups distances within absolute tolerance 1e-12 to prevent artificial floating-point splits of mathematically tied values. Its distinct fixture groups are farther apart than that tolerance. This is an explicit numeric policy, not a claim to reproduce the source's exact floating-point tie behavior, which uses exact equality. Clipping to endpoints or aggressive rounding can merge distinctions; this implementation rejects endpoints and saturated outputs instead of claiming universal numerical invariance.

### Review order is not a fixed numeric interval

For the main fixture the uncertainty order is E,F,D,G,C,H,B,A. At every cumulative group, T=1 and T=2 review the same IDs and produce the same final decisions. The invented reviewer misses G; escalating G adds a miss. “Send more to review” is not a guarantee when reviewer errors are possible.

A separate interval policy allows scores below 0.2, reviews `[0.2,0.8)`, and blocks scores at or above 0.8. With those numbers fixed, T=2 changes C from ALLOW to REVIEW and G from BLOCK to REVIEW. Review count rises from 3/8 to 5/8. This counterexample prevents the false claim that rescaling never changes decisions under any policy.

If the intent is to preserve those original routing decisions, transform both boundaries as well: T=2 maps 0.2 to 1/3 and 0.8 to 2/3. The resulting routes match the original exactly on every fixture. That coordinate conversion preserves the existing policy; it does not make it optimal or safe. A newly chosen policy needs separate held-out evaluation of misses, false blocks and reviewer workload.

### Controls and checks

The already-correct cohort shows that softening confidence can worsen both probability-error metrics even though all its verdicts stay correct. Identical-score/opposite-label twins cannot be separated by this transform. Boundary fixtures cover below, at and above 0.5; focused tests also check exact interval endpoints. T=1 is an identity control.

Eleven focused tests include an independent square-root odds calculation for T=2, exact decision/review comparisons, denominator checks, invalid domains and the fixed/remapped interval distinction. `check.py` tests a transform that does nothing and an oracle that hides misses. See [checks.json](artifacts/checks.json) for actual results.

## Limitations and engineering check

These are deliberately selected numbers, not detector outputs or samples from production. Lower Brier/log loss on this fixture does not establish calibration, population accuracy, model safety, attack success, or a useful deployment threshold. There is no calibration training, measured distribution shift, live reviewer, empirical uncertainty estimate or reproduction of the cited paper's cohort. Extreme floating-point behavior and clipped scores are outside the demonstrated domain. Fixture labels and fixed reviewer decisions are trusted assumptions.

When changing detector confidence scaling, compare the actual allow/block/review IDs alongside probability-error metrics. Keep calibration fitting separate from evaluation; if routing is intended to stay unchanged, transform its score boundaries consistently and test the resulting decisions. If routing is meant to change, evaluate its mistakes and review workload on separate labeled data before relying on it.
