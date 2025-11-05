"""Module entrypoint for `python -m app.worker`."""

from . import main


def run() -> None:
    """Invoke the worker CLI."""

    main()


if __name__ == "__main__":
    run()
