"""Measure entire encounter cycles from execution traces, including recovery and travel."""
from collections import defaultdict


def cycles(events):
    """Fight onset to next fight onset. Keep the final incomplete cycle as censored.

    Named operations can overlap; component seconds are reported separately and never
    added to elapsed seconds. Death time is already in elapsed time, without a penalty.
    """
    starts, opened, components = [], {}, defaultdict(float)
    result = []
    last = None
    for event in events:
        at, op, phase = event.get('t'), event.get('operation'), event.get('phase')
        if not isinstance(at, (int, float)):
            continue
        if last is not None and at < last:
            raise ValueError('trace timestamps run backwards')
        last = at
        if op == 'fight' and phase == 'begin':
            if starts:
                result.append({**starts[-1], 'seconds': at - starts[-1]['at'],
                               'components': dict(components), 'censored': False})
            starts.append({'at':at, 'deaths':0, 'killed':False})
            components.clear()
            opened.clear()
        if not starts:
            continue
        if phase == 'begin':
            opened[op] = at
        elif phase == 'end':
            if op in opened:
                components[op] += at - opened.pop(op)
            if op == 'fight':
                starts[-1]['deaths'] += int(event.get('code') == 'died')
                starts[-1]['killed'] |= event.get('code') == 'killed'
    if starts:
        result.append({**starts[-1], 'seconds': max(0, last - starts[-1]['at']),
                       'components': dict(components), 'censored': True})
    return result
