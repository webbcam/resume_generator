def pytest_addoption(parser):
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Rewrite tests/golden HTML snapshots",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "chrome: requires Google Chrome / Chromium")
