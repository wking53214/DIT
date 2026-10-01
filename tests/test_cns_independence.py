"""DIT is independent of CNS, and these tests hold whether or not CNS is
installed. Each one runs in a fresh interpreter in which ``cns`` is blocked
outright (``sys.modules['cns'] = None`` makes any import of it fail), so the
result does not depend on what the test environment happens to contain.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

SRC = str(Path(__file__).resolve().parents[1] / "src")

BLOCK = "import sys; sys.modules['cns'] = None; sys.modules['cns.gate'] = None\n"


def _run(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", BLOCK + textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": SRC, "PATH": ""},
        timeout=60,
    )


def test_dit_and_its_connector_import_with_cns_blocked():
    done = _run("import dit, dit.cns_connector; print('ok')")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "ok"


def test_dit_still_judges_text_with_cns_blocked():
    done = _run(
        """
        from dit import evaluate
        assert evaluate("Throughput may have improved.").passed is False
        assert evaluate("Queue depth fell 22% because the batch window widened.").passed
        print('ok')
        """
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "ok"


def test_connector_says_what_is_missing_when_cns_is_blocked():
    done = _run(
        """
        from dit.cns_connector import CnsNotInstalled, cns_available, evaluate_to_cns
        assert cns_available() is False
        try:
            evaluate_to_cns("x")
        except CnsNotInstalled as exc:
            assert "pip install 'dit[cns]'" in str(exc)
            assert isinstance(exc, ImportError)
            print('ok')
        """
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "ok"


def test_constructing_a_cns_gate_fails_at_construction_not_first_use():
    done = _run(
        """
        from dit import HedgingGate, default_rules
        from dit.cns_connector import CnsGate, CnsNotInstalled
        try:
            CnsGate(HedgingGate(default_rules()))
        except CnsNotInstalled:
            print('ok')
        """
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "ok"


def test_the_package_declares_no_runtime_dependency():
    import tomllib

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())
    assert data["project"]["dependencies"] == []
    assert "cns" in data["project"]["optional-dependencies"]
