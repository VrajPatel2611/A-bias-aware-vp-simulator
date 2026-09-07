"""
T-004 criterion 2 · the build fails below 94%.

`validate_detectors.py` used to print its result and always exit 0, so wiring
it into CI would have run it and cheerfully passed at any accuracy. These tests
prove the gate exists, that it is set to the published figure, and that it
actually fails — a gate never observed failing is not known to work.

These run the full validation in a subprocess. They are NOT marked `slow` —
CI's test job runs `-m "not slow"`, and a gate whose own tests are excluded from
CI is not a gate.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "validate_detectors.py"


def _run(cwd=REPO):
    """
    Run validation in `cwd`, importing the copy of vpsim that lives there.

    PYTHONPATH matters: vpsim is installed editable, pointing at the real
    repository, so without it a subprocess in a copied tree would import the
    real detectors and the degraded copy would appear to pass.
    """
    import os

    env = dict(os.environ, PYTHONPATH=str(cwd))
    return subprocess.run(
        [sys.executable, str(cwd / "validate_detectors.py")],
        cwd=cwd, capture_output=True, text=True, timeout=180, env=env,
    )


def test_the_threshold_is_the_published_figure():
    """
    94% is what the paper reports. If this constant and the paper disagree, one
    of them is wrong — and it is not the paper's job to follow the code.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("validate_detectors", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.MINIMUM_ACCURACY == 0.94


def test_passes_on_the_current_detectors():
    r = _run()
    assert r.returncode == 0, f"validation failed unexpectedly:\n{r.stdout}\n{r.stderr}"
    assert "PASS" in r.stdout


def test_fails_when_a_detector_is_degraded(tmp_path):
    """
    The test that matters. A copy of the repository with anchoring rule A1
    broken must exit non-zero — otherwise CI would merge a change that
    invalidates the published claim.
    """
    import shutil

    work = tmp_path / "repo"
    shutil.copytree(
        REPO, work,
        ignore=shutil.ignore_patterns("venv", ".git", "__pycache__", "*.pyc",
                                      ".pytest_cache", ".mypy_cache", "report",
                                      "docs", "sessions", "*.egg-info"),
    )

    bias = work / "vpsim" / "domain" / "assessment" / "bias.py"
    source = bias.read_text()
    assert "if concentration > 0.60:" in source, "rule A1 has moved — update this test"
    bias.write_text(source.replace("if concentration > 0.60:",
                                   "if concentration > 0.99:"))

    r = _run(cwd=work)
    assert r.returncode != 0, (
        "a degraded detector did NOT fail the build — the research claim is "
        f"unprotected:\n{r.stdout}"
    )
    assert "FAIL" in r.stderr
    assert "below the required 94%" in r.stderr


def test_the_failure_message_says_not_to_lower_the_threshold(tmp_path):
    """
    The obvious way to make a red build green is to lower the number. The
    message has to say so, because whoever hits this will be under time
    pressure and may not have read TEST_STRATEGY.
    """
    import shutil

    work = tmp_path / "repo"
    shutil.copytree(
        REPO, work,
        ignore=shutil.ignore_patterns("venv", ".git", "__pycache__", "*.pyc",
                                      ".pytest_cache", ".mypy_cache", "report",
                                      "docs", "sessions", "*.egg-info"),
    )
    bias = work / "vpsim" / "domain" / "assessment" / "bias.py"
    bias.write_text(bias.read_text().replace("if concentration > 0.60:",
                                             "if concentration > 0.99:"))

    stderr = _run(cwd=work).stderr
    assert "Do not" in stderr and "lower the threshold" in stderr
