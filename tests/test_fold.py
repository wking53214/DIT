from dit import default_rules
from dit.evaluate import run_stack
from dit.gates import GSA_V13_STACK, build_stack


def _hedging_passed(text):
    gates = build_stack(default_rules(), GSA_V13_STACK)
    return next(r for r in run_stack(text, gates) if r.gate == "hedging").passed


def test_a_plain_hedge_is_caught():
    assert not _hedging_passed("The load might increase by 40% because of retries.")


def test_a_zero_width_character_does_not_hide_a_hedge():
    assert not _hedging_passed("The load mi​ght increase by 40% because of retries.")


def test_a_lookalike_letter_does_not_hide_a_hedge():
    assert not _hedging_passed("The load mіght increase by 40% because of retries.")
