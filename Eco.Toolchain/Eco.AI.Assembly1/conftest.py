def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: mark test as live (requires real LLM, --live flag)"
    )
    config.addinivalue_line(
        "markers", "timeout(seconds): mark test with timeout (requires pytest-timeout)"
    )


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False,
                     help="enable @pytest.mark.live tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--live"):
        skip = __import__("pytest").mark.skip(reason="needs --live")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip)
