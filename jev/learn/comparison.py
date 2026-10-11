"""Paired episode evaluation for scripts, models, planners, and human reference runs.

Pairs must share conditions and use independent assignment units. This describes measured
outcomes only: saved observations cannot reveal outcomes of actions never executed.
"""
import math
import random
import statistics


def compare(samples, *, margin=.05, seed=11, draws=4000):
    if not 0 <= margin < 1:
        raise ValueError('invalid noninferiority margin')
    units = [s['unit'] for s in samples]
    if len(set(units)) != len(units):
        raise ValueError('repeated assignment units must be aggregated before comparison')
    ratios, failures, deaths = [], [], []
    for sample in samples:
        a, b = sample['candidate'], sample['control']
        for arm in (a, b):
            if (not isinstance(arm['success'], bool)
                    or not isinstance(arm['deaths'], int) or arm['deaths'] < 0
                    or not math.isfinite(arm['seconds']) or arm['seconds'] <= 0):
                raise ValueError('episode is missing valid duration, completion or deaths')
        ratios.append(a['seconds'] / b['seconds'])
        failures.append(int(not a['success']) - int(not b['success']))
        deaths.append(a['deaths'] - b['deaths'])
    status, interval = 'inconclusive', None
    if len(samples) >= 8:
        rng = random.Random(seed)
        boot = sorted(statistics.mean(rng.choices(ratios, k=len(ratios))) for _ in range(draws))
        interval = [boot[int(draws * .05)], boot[int(draws * .95)]]
        if any(d > 0 for d in deaths) or any(f > 0 for f in failures) or interval[0] > 1 + margin:
            status = 'harmful'
        elif all(s[a]['success'] for s in samples for a in ('candidate', 'control')):
            status = 'improved' if interval[1] < 1 else 'noninferior' if interval[1] <= 1 + margin else status
    return {'status': status, 'units': len(samples), 'duration_ratio': interval,
            'margin': margin, 'seed': seed,
            'completed': bool(samples) and all(s[a]['success'] for s in samples for a in ('candidate','control')),
            'candidate_deaths': sum(s['candidate']['deaths'] for s in samples),
            'control_deaths': sum(s['control']['deaths'] for s in samples),
            'interpretation': 'matched measured episodes; no unobserved counterfactual estimate'}
