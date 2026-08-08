"""Phase 00: installable package + version export (ADR §7.13 / §13.4)."""


def test_import_facktry():
    import facktry  # noqa: F401

    assert True


def test_version_string():
    import facktry

    assert isinstance(facktry.__version__, str) and facktry.__version__
