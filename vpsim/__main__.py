"""Development entry point: `python -m vpsim`."""

from vpsim.app import create_app
from vpsim.config import settings


def main() -> None:
    app = create_app()

    # Printed here because T-007 silences the werkzeug logger to stop it
    # duplicating our JSON request logs — and werkzeug emits its "Running on
    # http://..." banner through that same logger at INFO. Without this the
    # server starts correctly but never tells you where it is.
    url = f"http://127.0.0.1:{settings.PORT}"
    print(f" * VPSim running on {url}", flush=True)
    print(" * Press CTRL+C to quit", flush=True)

    app.run(debug=settings.DEBUG, port=settings.PORT)


if __name__ == "__main__":
    main()
