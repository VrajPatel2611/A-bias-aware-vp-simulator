# VPSim container image (BUILD_PLAN T-005 · TECH_SPEC §9.1 · ADR-0008).
#
# Multi-stage: the build stage carries pip, compilers and build metadata; the
# runtime stage carries only the installed package and its dependencies.

# ── build stage ──────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# The whole package is copied before installing, so `pip install .` produces a
# COMPLETE distribution — templates and static files included via the
# package-data entry in pyproject.toml.
#
# This costs layer caching: any source change reinstalls dependencies. The
# alternative (installing dependencies from requirements.txt first, then the
# package with --no-deps) caches better but makes requirements.txt load-bearing
# for the image, and it can drift from pyproject.toml. Correctness wins; the
# image is built in CI where a warm cache matters little.
COPY pyproject.toml README.md ./
COPY nidan/ ./nidan/

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --prefix=/install ".[prod]"

# ── runtime stage ────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Never run as root. A container escape starting from uid 0 is a very different
# incident from one starting as an unprivileged user (SECURITY_SPEC §3, T6).
RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 nidan

WORKDIR /app

# Only the installed package and its dependencies cross the stage boundary.
# There is deliberately no second copy of the source at /app: two importable
# copies of `nidan` on the path shadow each other unpredictably.
COPY --from=builder /install /usr/local

USER nidan

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

# /healthz, added in T-007. Liveness only: it touches no dependency, so a
# database outage does not trigger a restart loop. Previously this probed "/",
# which rendered the entire case list every 30 seconds.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status==200 else 1)"

# 2 workers x 4 threads, per TECH_SPEC §9.1.
#
# This line was --workers 1 until T-013, and not as a performance choice:
# session state was a dict in process memory (the old infra/session_store.py,
# blocker B1), so a second worker would have served requests that could not see
# the session. The spec was explicit that "multiple workers are only safe
# because session state left process memory".
#
# It has now left. Every handler replays an append-only event log and holds
# nothing between requests (ADR-0003), so a request may be served by any worker
# — or by a process that did not exist when the consultation started.
# tests/db/test_routes.py proves both halves: a consultation survives the
# process being disposed, and two clients cannot see each other.
# NO --access-logfile. Gunicorn's access log is plain text, so it breaks the
# "JSON logs to stdout" contract (TECH_SPEC §10), duplicates the app's own
# request log, and re-adds the /healthz probe every 30s that the app-level
# filter exists to remove. The after_request handler in nidan/app.py already
# logs every request as JSON with correlation ids and a duration.
#
# --error-logfile is kept: gunicorn's own failures (worker crash, bind refused)
# happen outside Flask and would otherwise be invisible.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", \
     "--error-logfile", "-", "nidan.app:app"]
