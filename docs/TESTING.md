# Validation

## Automated checks

```sh
.venv/bin/python -m unittest discover -s tests -v
node tests/navigation.test.js
node tests/replay-policy.test.js
node tests/presentation.test.js
```

The latest local Python run passed 66 tests. Tests use mocked model transports and do not spend Azure credit. They cover chronology, prefix boundaries, rules across seeds, phase selection, fact validation, corrections, caching, concurrent requests and atomic budget reservation. JavaScript checks cover spoiler-free navigation, rewind, freshness, important-moment scheduling and shared broadcast payloads.

## Real-model verification

Development has used real Microsoft Foundry inference for explanations, audience and team preferences, personnel events, selected phases and recaps. These are individual samples, not an error-free benchmark.

A full-time failure was reproduced: goal scorers and a dismissed player appeared in the supplied match history but were missing from the selected event evidence used by player-name validation. Full-time context now includes goals, dismissals and the final whistle. Hosted verification of the released image passed for a goal explanation (about 4.0 seconds) and full-time explanation (about 2.6 seconds), both with source `foundry`.

Model failures still produce explicit fallbacks. Request timing varies. Tests do not prove qualitative tactical causality or that every generated sentence is correct.

## Browser review

Browser review covers replay controls, narrow-width layouts, evidence expansion, selected phases, audience preferences, record corrections and consistent broadcast output. Automated tests complement visual and interactive review.
