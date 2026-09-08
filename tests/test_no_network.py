"""
T-002 criterion 1 · no test makes a network call.

Two guards. The autouse `_no_real_llm` fixture in conftest makes a real call
fail; these tests prove that guard is actually wired to reality rather than
patching a path that no longer exists.
"""

import pytest

import vpsim.api.routes as routes
import vpsim.infra.feedback as infra_feedback
from vpsim.infra.llm import gateway


def test_the_guard_actually_blocks_a_real_client():
    """The autouse fixture is in force, so constructing a client must fail."""
    with pytest.raises(AssertionError, match="real LLM client"):
        gateway._get_client()


def test_every_call_llm_import_site_is_patched_by_the_fake_llm_fixture(fake_llm):
    """
    `call_llm` is imported by name, so each importing module holds its own
    reference. conftest patches a hard-coded list of sites; this test fails if
    that list goes stale — a new module importing call_llm would otherwise
    silently reach the real gateway.
    """
    assert infra_feedback.call_llm is fake_llm
    assert routes.call_llm is fake_llm


def test_no_unpatched_module_imports_call_llm():
    """
    Catches the stale-list problem at its source: if a module starts importing
    call_llm and conftest is not updated, this names it.
    """
    import pathlib

    patched = {"vpsim/infra/feedback.py", "vpsim/api/routes.py"}
    root = pathlib.Path(__file__).resolve().parent.parent

    importers = {
        str(py.relative_to(root))
        for py in (root / "vpsim").rglob("*.py")
        if "import call_llm" in py.read_text(encoding="utf-8")
    }

    unpatched = sorted(importers - patched)
    assert not unpatched, (
        "These modules import call_llm but conftest's fake_llm fixture does not "
        f"patch them, so they would reach the real gateway: {unpatched}"
    )
