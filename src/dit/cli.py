"""``python -m dit`` -- run the historical test vectors against the tower.

Vector 01 is the drift-recovery case the GSA v13.0 engine could not clear:
its generator emits non-compliant text until the instructional delta lands.
Vector 02 is the immediate-compliance path. Both are run against the
remediated tower with a ledger attached, so the output also demonstrates
hash-chain sealing and verification.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .config import FAST, HISTORICAL, TowerConfig
from .ledger import HashChainLedger
from .results import Status
from .tower import DeterministicIntegrityTower


async def drifting_generator(prompt: str) -> str:
    """Non-compliant until the tower's delta names the failures."""
    if "INSTRUCTIONAL_DELTA" in prompt:
        return "Queue depth fell 22% because the batch window was widened."
    return "I think we can optimize the pipeline to look much better."


async def compliant_generator(prompt: str) -> str:
    return (
        "System performance remains steady because local token consumption "
        "decreased by 22%."
    )


def _report(label: str, result) -> None:
    print(f"\n{label}")
    print(f"  status   : {result.status.value}")
    print(f"  parity   : {result.parity}")
    print(f"  attempts : {result.attempts}")
    print(f"  latency  : {result.latency_ms} ms")
    if result.payload is not None:
        print(f"  payload  : {result.payload}")
        print(f"  checksum : {result.checksum[:32]}...")
    for reason in result.failures:
        print(f"  failure  : {reason}")


async def _run(config: TowerConfig, as_json: bool) -> int:
    ledger = HashChainLedger()
    print("--- DETERMINISTIC INTEGRITY TOWER ---")

    drift = DeterministicIntegrityTower(
        drifting_generator, config=config, ledger=ledger
    )
    result_01 = await drift.run(
        "Process standard network infrastructure analysis matrix."
    )

    fast = DeterministicIntegrityTower(
        compliant_generator, config=config, ledger=ledger
    )
    result_02 = await fast.run("Generate a compliant status report metrics profile.")

    if as_json:
        print(
            json.dumps(
                {
                    "vector_01": result_01.as_dict(),
                    "vector_02": result_02.as_dict(),
                    "ledger_intact": ledger.verify(),
                    "ledger_head": ledger.head,
                },
                indent=2,
            )
        )
    else:
        _report("Test Vector 01 (Linguistic Drift Recovery):", result_01)
        _report("Test Vector 02 (Immediate Compliant Track):", result_02)
        print(f"\nLedger records : {len(ledger)}")
        print(f"Chain intact   : {ledger.verify()}")
        print(f"Chain head     : {ledger.head}")

    failed = [r for r in (result_01, result_02) if r.status is not Status.PASS]
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dit", description=__doc__)
    parser.add_argument(
        "--fast",
        action="store_true",
        help="disable kinetic pacing (the FAST profile)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)
    config = FAST if args.fast else HISTORICAL
    return asyncio.run(_run(config, args.json))


if __name__ == "__main__":
    sys.exit(main())
