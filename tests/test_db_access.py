"""
T-012 acceptance criterion 1: "no query bypasses" the repository layer.

The wording is not "queries should use the repository". A convention is
something you can follow, which means it is something you can forget, and a
forgotten `WHERE user_id = ...` in a hand-rolled query is precisely the breach
the whole layer exists to prevent. So the property is checked the way
`test_layering.py` checks ADR-0009: by reading the source and failing the build.

Three claims, each of which stops being true the moment someone writes the
convenient thing:

1. Connections are created in exactly one module.
2. Nothing outside `nidan.infra.db` imports that module.
3. SQL is written in exactly one package.

A fourth guards the path where the database is not protecting us at all
(criterion 3).
"""

from __future__ import annotations

import ast
import pathlib

PKG = pathlib.Path(__file__).resolve().parent.parent / "nidan"
DB = PKG / "infra" / "db"
ENGINE = DB / "engine.py"
REPOSITORIES = DB / "repositories"

_SQL_STARTS = ("select ", "insert ", "update ", "delete ", "with ")


def _modules():
    for py in PKG.rglob("*.py"):
        yield py, ast.parse(py.read_text(encoding="utf-8"))


def _rel(py: pathlib.Path) -> str:
    return py.relative_to(PKG.parent).as_posix()


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """
    Every string that is a statement on its own -- docstrings, and the prose
    blocks these modules use to explain their SQL. Excluded from the literal
    scan, or this file's own explanations would trip it.
    """
    ids = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):      # IfExp.body is an expression
            continue
        for stmt in body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) \
                    and isinstance(stmt.value.value, str):
                ids.add(id(stmt.value))
    return ids


def _sql_literals(tree: ast.AST):
    skip = _docstring_nodes(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in skip:
            text = node.value.strip().lower()
            if text.startswith(_SQL_STARTS):
                yield node.value


def test_connections_are_created_in_one_module() -> None:
    """
    `create_engine` anywhere else is a second pool with its own credentials and
    no actor -- the exact shape of the bypass this task forbids.
    """
    offenders = []
    for py, tree in _modules():
        in_db = py.parent == DB or DB in py.parents
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            # `.connect()` is legitimate anywhere inside infra/db -- base.py
            # opens the transaction. `create_engine` is legitimate in exactly
            # one file, because a second engine is a second pool that no scope
            # controls.
            if name in ("create_engine", "create_async_engine") and py != ENGINE:
                offenders.append(f"{_rel(py)}:{node.lineno} calls {name}()")
            elif name == "connect" and not in_db:
                offenders.append(f"{_rel(py)}:{node.lineno} calls connect()")
    assert not offenders, (
        "only nidan/infra/db/engine.py may open connections:\n  "
        + "\n  ".join(offenders))


def test_nothing_outside_infra_db_imports_the_engine() -> None:
    """
    The engine is the only object from which an unscoped connection can be
    obtained. Keeping the import surface to one package is what makes
    `repo_scope` the only door rather than merely the front one.
    """
    offenders = []
    for py, tree in _modules():
        if DB in py.parents or py.parent == DB:
            continue
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            for mod in mods:
                if "infra.db.engine" in mod:
                    offenders.append(f"{_rel(py)}:{node.lineno} imports {mod}")
    assert not offenders, (
        "the engine is private to nidan/infra/db:\n  " + "\n  ".join(offenders))


def test_sql_is_written_only_in_the_repository_package() -> None:
    """
    A query outside the repositories is a query that ran outside a scope, which
    means it ran with whatever role and whatever `auth.uid()` the connection
    happened to carry.
    """
    offenders = []
    for py, tree in _modules():
        if REPOSITORIES in py.parents or py.parent == REPOSITORIES:
            continue
        for sql in _sql_literals(tree):
            offenders.append(f"{_rel(py)}: {sql.strip().splitlines()[0][:60]}...")
    assert not offenders, (
        "SQL belongs in nidan/infra/db/repositories/:\n  " + "\n  ".join(offenders))


def test_every_anonymous_query_filters_on_anonymous_id() -> None:
    """
    Criterion 3, checked mechanically.

    On this path RLS is bypassed, so `anonymous_id = :anonymous_id` is the only
    thing standing between one trial visitor and every other. A query here that
    omits it does not fail, does not warn, and returns other people's sessions.
    """
    tree = ast.parse((REPOSITORIES / "anonymous.py").read_text(encoding="utf-8"))
    unfiltered = [
        sql for sql in _sql_literals(tree) if "anonymous_id" not in sql
    ]
    assert not unfiltered, (
        "every statement in anonymous.py must filter anonymous_id:\n  "
        + "\n  ".join(s.strip()[:80] for s in unfiltered))
