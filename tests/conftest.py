"""Shared fixtures.

The suite is stdlib plus pytest: no pytest-asyncio, no event-loop plugin.
Coroutines are driven through :func:`run`, which is explicit about the fact
that each test owns its own loop.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

import pytest

from dit import FAST, RuleSet, StasisSigner, TowerConfig, default_rules


def run(coro: Awaitable[Any]) -> Any:
    """Drive one coroutine to completion on a fresh event loop."""
    return asyncio.run(coro)


def scripted(*responses: str) -> Callable[[str], Awaitable[str]]:
    """A generator that returns each response in turn, repeating the last.

    Records every prompt it was called with on ``.prompts``, so a test can
    assert what the tower actually asked for on retry.
    """

    async def generator(prompt: str) -> str:
        generator.prompts.append(prompt)
        index = min(len(generator.prompts) - 1, len(responses) - 1)
        return responses[index]

    generator.prompts = []  # type: ignore[attr-defined]
    return generator


def constant(response: str) -> Callable[[str], Awaitable[str]]:
    return scripted(response)


@pytest.fixture
def rules() -> RuleSet:
    return default_rules()


@pytest.fixture
def fast_config() -> TowerConfig:
    return FAST


@pytest.fixture
def signer() -> StasisSigner:
    return StasisSigner.generate()


#: A payload that clears every retryable gate: no pronouns, no hedging,
#: and both a causal connective and a measured quantity.
COMPLIANT = "Queue depth fell 22% because the batch window was widened."
