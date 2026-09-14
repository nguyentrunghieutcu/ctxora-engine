from harness_context.interfaces.cli import app as _cli  # noqa: I001
build_parser = _cli.build_parser; _main = _cli._main
def main(argv=None):
    try:
        return _main(argv)
    except BaseException as error: return 130 if isinstance(error, KeyboardInterrupt) else 1  # noqa: BLE001
if __name__ == "__main__": raise SystemExit(main())
