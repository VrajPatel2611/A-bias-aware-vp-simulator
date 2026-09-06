"""Development entry point: `python -m vpsim`."""

from vpsim.app import create_app
from vpsim.config import settings


def main() -> None:
    create_app().run(debug=settings.DEBUG, port=settings.PORT)


if __name__ == "__main__":
    main()
