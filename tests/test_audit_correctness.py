"""Regressions for the 11 October audit's repeated failures and unknown observations."""
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest
from test_provisions import _state

from jev.clients.rest import Rest, Rested
from jev.coach.policy import Context, services
from jev.run.hunt import Hunt
from jev.world.vendor import Larder


def shopping_context():
    return Context(larder=lambda s: Larder(roles=("food",), near=("food",), near_price=125))


def test_no_supplier_cannot_spin_or_forget_at_a_session_boundary():
    ctx, state = shopping_context(), _state(money=1000)
    assert "service.provisions" in [p.rule for p in services(state, context=ctx)]
    ctx.supplies_out_of_reach("no_supplier")
    for _ in range(100):
        assert not services(state, context=ctx)
    next_session = shopping_context()
    next_session.restore_purse(json.loads(json.dumps(ctx.purse())))
    assert not services(state, context=next_session)
    moved = state.model_copy(update={"pos": state.pos.model_copy(update={"zone_id": 6586})})
    assert "service.provisions" in [p.rule for p in services(moved, context=next_session)]


@pytest.mark.parametrize("field,value", [("money_copper", 1500), ("food_count", 2),
                                         ("inventory_revision", 4)])
def test_changed_supply_facts_reopen_a_request(field, value):
    ctx, state = shopping_context(), _state(money=1000)
    services(state, context=ctx)
    ctx.supplies_out_of_reach("nothing_sold")
    changed = state.model_copy(update={"bags": state.bags.model_copy(update={field: value})})
    assert any(p.rule == "service.provisions" for p in services(changed, context=ctx))


def test_time_and_guide_changes_do_not_reopen_the_same_failed_purchase():
    ctx, state = shopping_context(), _state(money=1000)
    services(state, context=ctx)
    ctx.supplies_out_of_reach("no_supplier")
    assert not services(_state(money=1000, t=5000, step="another"), context=ctx)
    ctx.supplies_out_of_reach("too_far")
    assert any(p.rule == "service.provisions" for p in services(state, context=ctx))


@pytest.mark.parametrize("values", [{}, {"vitals.hp": 1.0}, {"vitals.hp": float("nan")},
                                   {"vitals.hp": True}, {"vitals.hp": 1.2}])
def test_recovery_requires_every_requested_gauge(values):
    assert Rest(object(), lambda: values).until_both(.9, .9) is Rested.BLIND


def test_incoming_combat_preempts_even_an_incomplete_or_full_recovery_read():
    assert Rest(object(), lambda: {"vitals.combat": True}).until() is Rested.INTERRUPTED
    assert Rest(object(), lambda: {"vitals.hp": 1, "vitals.dead": True}).until() is Rested.INTERRUPTED


@pytest.mark.parametrize("values", [None, {}, {"vitals.hp": float("nan")},
                                   {"char.class_id": 8, "vitals.hp": 1.0}])
def test_no_new_pull_without_readable_required_vitals(values):
    hunt = object.__new__(Hunt)
    hunt.read = lambda: values
    hunt.fight = SimpleNamespace()
    assert hunt._ready_to_pull() is False
    assert hunt._ready_to_pull({"vitals.combat": True}) is True


def test_default_timing_is_reproducible_across_python_processes():
    code = ('from jev.clients.hid import Humaniser; h=Humaniser.for_client("hive-944"); '
            'print(h.gap(), h.stagger_ms)')
    results = [subprocess.check_output([sys.executable, "-c", code], text=True,
                                     env={**os.environ, "PYTHONHASHSEED": str(seed)})
               for seed in (0, 1)]
    assert results[0] == results[1]
