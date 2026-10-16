# Exact synthetic evidence

Invented labels, scores and reviewer decisions. No model ran; no temperature was fitted.

## Main cohort: 8 examples, 4 attack-labeled and 4 benign-labeled

| T | Squared probability error (Brier) | Log loss | Misses / 4 | False blocks / 4 |
|---:|---:|---:|---:|---:|
| 0.5 | 0.495749 | 2.943778 | 2 | 2 |
| 1 | 0.446250 | 1.602878 | 2 | 2 |
| 2 | 0.368872 | 1.026225 | 2 | 2 |
| 4 | 0.303986 | 0.812622 | 2 | 2 |

## Exact decisions at the fixed 0.5 cutoff

| ID | Original score | T=2 score | Original verdict | T=2 verdict |
|---|---:|---:|---|---|
| A | 0.010000 | 0.091325 | ALLOW | ALLOW |
| B | 0.020000 | 0.125000 | ALLOW | ALLOW |
| C | 0.100000 | 0.250000 | ALLOW | ALLOW |
| D | 0.210000 | 0.340187 | ALLOW | ALLOW |
| E | 0.550000 | 0.525063 | BLOCK | BLOCK |
| F | 0.760000 | 0.640225 | BLOCK | BLOCK |
| G | 0.880000 | 0.730314 | BLOCK | BLOCK |
| H | 0.970000 | 0.850439 | BLOCK | BLOCK |

A and C have attack labels but remain allowed. F and H have benign labels but remain blocked.
B and D remain correctly allowed; E and G remain correctly blocked.

## Ranked review and policy boundaries

Main review order (tied groups): [['E'], ['F'], ['D'], ['G'], ['C'], ['H'], ['B'], ['A']]. T=2 has the same order and exact decision trace.
The reviewer decisions are fixed fixtures, not live model outputs or an error-free oracle.
Reviewing G introduces a miss: more review need not monotonically reduce misses with this invented reviewer.

| ID | Original [0.2,0.8) | T=2, same numbers | T=2, transformed boundaries |
|---|---|---|---|
| A | ALLOW | ALLOW | ALLOW |
| B | ALLOW | ALLOW | ALLOW |
| C | ALLOW | REVIEW | ALLOW |
| D | REVIEW | REVIEW | REVIEW |
| E | REVIEW | REVIEW | REVIEW |
| F | REVIEW | REVIEW | REVIEW |
| G | BLOCK | REVIEW | BLOCK |
| H | BLOCK | BLOCK | BLOCK |

Transformed boundaries: 0.333333333333, 0.666666666667.
The unchanged [0.2,0.8) numbers change review workload. Transforming scores and boundaries together preserves routes.

## Limits and counterexamples

The already_correct cohort has perfect original verdicts: softening its scores worsens probability error.
The equal_score_twins cohort gives identical scores to opposite labels; scaling cannot separate them.
The boundary cohort retains the stated >=0.5 block convention, including the exact midpoint.
These selected fixtures are not attack rates, calibrated deployment estimates or a paper reproduction.
Interior scores and moderate positive temperatures only; finite precision, clipping and arbitrary policies require separate checks.
