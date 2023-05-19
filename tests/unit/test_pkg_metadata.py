import semver

import rdk


def test_pkg_metadata():
    for pkg_metadata in [
        "NAME",
        "VERSION",
        "DESCRIPTION",
        "MAINTAINER",
        "MAINTAINER_EMAIL",
        "URL",
    ]:
        assert hasattr(rdk, pkg_metadata)
        assert getattr(rdk, pkg_metadata) is not None

    assert semver.VersionInfo.isvalid(getattr(rdk, "VERSION"))
