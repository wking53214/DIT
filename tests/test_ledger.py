import pytest

from dit import GENESIS, HashChainLedger, LedgerTampered, canonical_json


def test_first_record_anchors_to_genesis():
    ledger = HashChainLedger()
    ledger.append({"cycle": "one"})
    assert ledger.entries()[0]["prev_hash"] == GENESIS


def test_head_advances_with_each_record():
    ledger = HashChainLedger()
    first = ledger.append({"cycle": "one"})
    second = ledger.append({"cycle": "two"})
    assert ledger.head == second != first
    assert ledger.entries()[1]["prev_hash"] == first


def test_empty_chain_verifies():
    assert HashChainLedger().verify()
    assert HashChainLedger().head == GENESIS


def test_chain_verifies_when_intact():
    ledger = HashChainLedger()
    for index in range(10):
        ledger.append({"cycle": index})
    assert ledger.verify()


def test_edited_content_is_detected():
    """The recovered verify() compared only the stored hash fields, so a
    record's body could be edited in place without detection. Digests are
    recomputed from the body here."""
    ledger = HashChainLedger()
    ledger.append({"cycle": "original"})
    ledger._log[0]["cycle"] = "forged"
    assert not ledger.verify()


def test_broken_link_is_detected():
    ledger = HashChainLedger()
    ledger.append({"cycle": "one"})
    ledger.append({"cycle": "two"})
    ledger._log[1]["prev_hash"] = "0" * 64
    assert not ledger.verify()


def test_require_intact_raises_on_tamper():
    ledger = HashChainLedger()
    ledger.append({"cycle": "one"})
    ledger._log[0]["cycle"] = "forged"
    with pytest.raises(LedgerTampered):
        ledger.require_intact()


def test_entries_are_snapshots():
    ledger = HashChainLedger()
    ledger.append({"cycle": "one"})
    ledger.entries()[0]["cycle"] = "mutated"
    assert ledger.verify()


def test_reserved_fields_cannot_be_supplied():
    ledger = HashChainLedger()
    with pytest.raises(ValueError, match="ledger-owned"):
        ledger.append({"hash": "forged"})


def test_canonical_json_is_key_order_independent():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})
