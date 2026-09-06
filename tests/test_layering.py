"""
T-001 acceptance criterion 2, and the ADR-0009 contract.

The domain layer is pure: it must not import infrastructure or the web layer.
This is what keeps the assessment engine unit-testable without a database and
replayable for recomputation (PR-3).

CI enforces the same rule with import-linter (T-004); this test means a local
run catches a violation before the push.
"""

import ast
import pathlib

DOMAIN = pathlib.Path(__file__).resolve().parent.parent / "vpsim" / "domain"
FORBIDDEN = ("vpsim.infra", "vpsim.api", "vpsim.app")


def _imports(path: pathlib.Path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_domain_does_not_import_infra_or_api():
    violations = []
    for py in DOMAIN.rglob("*.py"):
        for mod in _imports(py):
            if mod.startswith(FORBIDDEN):
                violations.append(f"{py.relative_to(DOMAIN.parent)} imports {mod}")
    assert not violations, "domain layer must stay pure:\n  " + "\n  ".join(violations)


def test_domain_has_no_flask_dependency():
    """A domain module that needs Flask is really a web module."""
    violations = []
    for py in DOMAIN.rglob("*.py"):
        for mod in _imports(py):
            if mod.split(".")[0] in ("flask", "groq"):
                violations.append(f"{py.relative_to(DOMAIN.parent)} imports {mod}")
    assert not violations, "domain must not depend on the framework or a provider:\n  " + "\n  ".join(violations)
