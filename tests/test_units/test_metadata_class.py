"""Test the _MetaData class from the _metadata.py module"""
import logging
from copy import deepcopy

import fmu.dataio as dio
import pytest
from fmu.dataio._metadata import SCHEMA, SOURCE, VERSION, ConfigurationError, MetaData
from fmu.dataio._utils import prettyprint_dict
from fmu.dataio.datastructure.meta.meta import (
    SystemInformationOperatingSystem,
    TracklogEvent,
)

# pylint: disable=no-member

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# DOLLAR block
# --------------------------------------------------------------------------------------


def test_metadata_dollars(edataobj1):
    """Testing the dollars part which is hard set."""

    mymeta = MetaData("dummy", edataobj1)

    assert mymeta.meta_dollars["version"] == VERSION
    assert mymeta.meta_dollars["$schema"] == SCHEMA
    assert mymeta.meta_dollars["source"] == SOURCE


# --------------------------------------------------------------------------------------
# Tracklog
# --------------------------------------------------------------------------------------


def test_generate_meta_tracklog_fmu_dataio_version(edataobj1):
    mymeta = MetaData("dummy", edataobj1)
    mymeta._populate_meta_tracklog()
    tracklog = mymeta.meta_tracklog

    assert isinstance(tracklog, list)
    assert len(tracklog) == 1  # assume "created"

    parsed = TracklogEvent.model_validate(tracklog[0])
    assert parsed.event == "created"

    # datetime in tracklog shall include time zone offset
    assert parsed.datetime.tzinfo is not None

    # datetime in tracklog shall be on UTC time
    assert parsed.datetime.utcoffset().total_seconds() == 0

    assert parsed.sysinfo.fmu_dataio is not None
    assert parsed.sysinfo.fmu_dataio.version is not None


def test_generate_meta_tracklog_komodo_version(edataobj1, monkeypatch):
    fake_komodo_release = "<FAKE_KOMODO_RELEASE_VERSION>"
    monkeypatch.setenv("KOMODO_RELEASE", fake_komodo_release)

    mymeta = MetaData("dummy", edataobj1)
    mymeta._populate_meta_tracklog()
    tracklog = mymeta.meta_tracklog

    assert isinstance(tracklog, list)
    assert len(tracklog) == 1  # assume "created"

    parsed = TracklogEvent.model_validate(tracklog[0])
    assert parsed.event == "created"

    # datetime in tracklog shall include time zone offset
    assert parsed.datetime.tzinfo is not None

    # datetime in tracklog shall be on UTC time
    assert parsed.datetime.utcoffset().total_seconds() == 0

    assert parsed.sysinfo.komodo is not None
    assert parsed.sysinfo.komodo.version == fake_komodo_release


def test_generate_meta_tracklog_operating_system(edataobj1):
    mymeta = MetaData("dummy", edataobj1)
    mymeta._populate_meta_tracklog()
    tracklog = mymeta.meta_tracklog

    assert isinstance(tracklog, list)
    assert len(tracklog) == 1  # assume "created"

    parsed = TracklogEvent.model_validate(tracklog[0])
    assert isinstance(
        parsed.sysinfo.operating_system,
        SystemInformationOperatingSystem,
    )


# --------------------------------------------------------------------------------------
# DATA block (ObjectData)
# --------------------------------------------------------------------------------------


def test_populate_meta_objectdata(regsurf, edataobj2):
    mymeta = MetaData(regsurf, edataobj2)
    mymeta._populate_meta_objectdata()
    assert mymeta.objdata.name == "VOLANTIS GP. Top"


def test_populate_meta_undef_is_zero(regsurf, globalconfig2):
    eobj1 = dio.ExportData(
        config=globalconfig2,
        name="TopVolantis",
        content="depth",
        unit="m",
    )

    # assert field is present and default is False
    mymeta1 = eobj1.generate_metadata(regsurf)
    assert mymeta1["data"]["undef_is_zero"] is False

    # assert that value is reflected when passed to generate_metadata
    mymeta2 = eobj1.generate_metadata(regsurf, undef_is_zero=True)
    assert mymeta2["data"]["undef_is_zero"] is True

    # assert that value is reflected when passed to ExportData
    eobj2 = dio.ExportData(
        config=globalconfig2,
        name="TopVolantis",
        content="depth",
        unit="m",
        undef_is_zero=True,
    )
    mymeta3 = eobj2.generate_metadata(regsurf, undef_is_zero=True)
    assert mymeta3["data"]["undef_is_zero"] is True


# --------------------------------------------------------------------------------------
# MASTERDATA block
# --------------------------------------------------------------------------------------


def test_metadata_populate_masterdata_is_empty(globalconfig1):
    """Testing the masterdata part, first with no settings."""

    some = dio.ExportData(config=globalconfig1, content="depth")
    del some.config["masterdata"]  # to force missing masterdata

    mymeta = MetaData("dummy", some)

    with pytest.raises(ValueError, match="A config exists, but 'masterdata' are not"):
        mymeta._populate_meta_masterdata()


def test_metadata_populate_masterdata_is_present_ok(edataobj1, edataobj2):
    """Testing the masterdata part with OK metdata."""

    mymeta = MetaData("dummy", edataobj1)
    mymeta._populate_meta_masterdata()
    assert mymeta.meta_masterdata == edataobj1.config["masterdata"]

    mymeta = MetaData("dummy", edataobj2)
    mymeta._populate_meta_masterdata()
    assert mymeta.meta_masterdata == edataobj2.config["masterdata"]


# --------------------------------------------------------------------------------------
# ACCESS block
# --------------------------------------------------------------------------------------


def test_metadata_populate_access_miss_config_access(edataobj1):
    """Testing the access part, now with config missing access."""

    cfg1_edited = deepcopy(edataobj1)
    del cfg1_edited.config["access"]

    mymeta = MetaData("dummy", cfg1_edited)

    with pytest.raises(ConfigurationError):
        mymeta._populate_meta_access()


def test_metadata_populate_access_ok_config(edataobj2):
    """Testing the access part, now with config ok access."""

    mymeta = MetaData("dummy", edataobj2)

    mymeta._populate_meta_access()
    assert mymeta.meta_access == {
        "asset": {"name": "Drogon"},
        "ssdl": {"access_level": "internal", "rep_include": True},
        "classification": "internal",
    }


def test_metadata_populate_from_argument(globalconfig1):
    """Testing the access part, now with ok config and a change in access."""

    # test assumptions
    assert globalconfig1["access"]["ssdl"]["access_level"] == "internal"

    edata = dio.ExportData(
        config=globalconfig1,
        access_ssdl={"access_level": "restricted", "rep_include": True},
        content="depth",
    )
    mymeta = MetaData("dummy", edata)

    mymeta._populate_meta_access()
    assert mymeta.meta_access == {
        "asset": {"name": "Test"},
        "ssdl": {"access_level": "restricted", "rep_include": True},
        "classification": "restricted",  # mirroring ssdl.access_level
    }


def test_metadata_populate_partial_access_ssdl(globalconfig1):
    """Test what happens if ssdl_access argument is partial."""

    # test assumptions
    assert globalconfig1["access"]["ssdl"]["access_level"] == "internal"
    assert globalconfig1["access"]["ssdl"]["rep_include"] is False

    # rep_include only, but in config
    edata = dio.ExportData(
        config=globalconfig1, access_ssdl={"rep_include": True}, content="depth"
    )
    mymeta = MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is True
    assert mymeta.meta_access["ssdl"]["access_level"] == "internal"  # default
    assert mymeta.meta_access["classification"] == "internal"  # default

    # access_level only, but in config
    edata = dio.ExportData(
        config=globalconfig1,
        access_ssdl={"access_level": "restricted"},
        content="depth",
    )
    mymeta = MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is False  # default
    assert mymeta.meta_access["ssdl"]["access_level"] == "restricted"
    assert mymeta.meta_access["classification"] == "restricted"


def test_metadata_populate_wrong_config(globalconfig1):
    """Test error in access_ssdl in config."""

    # test assumptions
    _config = deepcopy(globalconfig1)
    _config["access"]["ssdl"]["access_level"] = "wrong"

    with pytest.warns(UserWarning):
        edata = dio.ExportData(config=_config, content="depth")

    mymeta = MetaData("dummy", edata)
    with pytest.raises(ConfigurationError, match="Illegal value for access"):
        mymeta._populate_meta_access()


def test_metadata_populate_wrong_argument(globalconfig1):
    """Test error in access_ssdl in arguments."""

    with pytest.warns(UserWarning):
        edata = dio.ExportData(
            config=globalconfig1,
            access_ssdl={"access_level": "wrong"},
            content="depth",
        )
    mymeta = MetaData("dummy", edata)
    with pytest.raises(ConfigurationError, match="Illegal value for access"):
        mymeta._populate_meta_access()


def test_metadata_access_correct_input(globalconfig1):
    """Test giving correct input."""
    # Input is "restricted" and False - correct use, shall work
    edata = dio.ExportData(
        config=globalconfig1,
        content="depth",
        access_ssdl={"access_level": "restricted", "rep_include": False},
    )
    mymeta = MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is False
    assert mymeta.meta_access["ssdl"]["access_level"] == "restricted"
    assert mymeta.meta_access["classification"] == "restricted"

    # Input is "internal" and True - correct use, shall work
    edata = dio.ExportData(
        config=globalconfig1,
        content="depth",
        access_ssdl={"access_level": "internal", "rep_include": True},
    )
    mymeta = MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is True
    assert mymeta.meta_access["ssdl"]["access_level"] == "internal"
    assert mymeta.meta_access["classification"] == "internal"


def test_metadata_access_deprecated_input(globalconfig1):
    """Test giving deprecated input."""
    # Input is "asset". Is deprecated, shall work with warning.
    # Output shall be "restricted".
    edata = dio.ExportData(
        config=globalconfig1, access_ssdl={"access_level": "asset"}, content="depth"
    )
    mymeta = MetaData("dummy", edata)
    with pytest.warns(
        UserWarning,
        match="The value 'asset' for access.ssdl.access_level is deprec",
    ):
        mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["access_level"] == "restricted"
    assert mymeta.meta_access["classification"] == "restricted"


def test_metadata_access_illegal_input(globalconfig1):
    """Test giving illegal input."""

    # Input is "secret". Not allowed, shall fail.
    with pytest.warns(UserWarning):
        edata = dio.ExportData(
            config=globalconfig1,
            access_ssdl={"access_level": "secret"},
            content="depth",
        )

    mymeta = MetaData("dummy", edata)
    with pytest.raises(ConfigurationError, match="Illegal value for access"):
        mymeta._populate_meta_access()

    # Input is "open". Not allowed, shall fail.
    with pytest.warns(UserWarning):
        edata = dio.ExportData(
            config=globalconfig1,
            access_ssdl={"access_level": "open"},
            content="depth",
        )
    mymeta = MetaData("dummy", edata)
    with pytest.raises(ConfigurationError, match="Illegal value for access"):
        mymeta._populate_meta_access()


def test_metadata_access_no_input(globalconfig1):
    """Test not giving any input arguments."""

    # No input, revert to config
    configcopy = deepcopy(globalconfig1)
    configcopy["access"]["ssdl"]["access_level"] = "restricted"
    configcopy["access"]["ssdl"]["rep_include"] = True
    edata = dio.ExportData(config=configcopy, content="depth")
    mymeta = MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is True
    assert mymeta.meta_access["ssdl"]["access_level"] == "restricted"
    assert mymeta.meta_access["classification"] == "restricted"  # mirrored

    # No input, no config, shall default to "internal" and False
    configcopy = deepcopy(globalconfig1)
    del configcopy["access"]["ssdl"]["access_level"]
    del configcopy["access"]["ssdl"]["rep_include"]
    edata = dio.ExportData(config=globalconfig1, content="depth")
    mymeta = MetaData("dummy", edata)
    mymeta._populate_meta_access()
    assert mymeta.meta_access["ssdl"]["rep_include"] is False  # default
    assert mymeta.meta_access["ssdl"]["access_level"] == "internal"  # default
    assert mymeta.meta_access["classification"] == "internal"  # mirrored


# --------------------------------------------------------------------------------------
# DISPLAY block
# --------------------------------------------------------------------------------------


def test_metadata_display_name_not_given(regsurf, edataobj2):
    """Test that display.name == data.name when not explicitly provided."""

    mymeta = MetaData(regsurf, edataobj2)
    mymeta._populate_meta_objectdata()
    mymeta._populate_meta_display()

    assert "name" in mymeta.meta_display
    assert mymeta.meta_display["name"] == mymeta.objdata.name


def test_metadata_display_name_given(regsurf, edataobj2):
    """Test that display.name is set when explicitly given."""

    mymeta = MetaData(regsurf, edataobj2)
    edataobj2.display_name = "My Display Name"
    mymeta._populate_meta_objectdata()
    mymeta._populate_meta_display()

    assert mymeta.meta_display["name"] == "My Display Name"
    assert mymeta.objdata.name == mymeta.meta_objectdata["name"] == "VOLANTIS GP. Top"


# --------------------------------------------------------------------------------------
# The GENERATE method
# --------------------------------------------------------------------------------------


def test_generate_full_metadata(regsurf, edataobj2):
    """Generating the full metadata block for a xtgeo surface."""

    mymeta = MetaData(regsurf, edataobj2)

    metadata_result = mymeta.generate_export_metadata(
        skip_null=False
    )  # want to have None

    logger.debug("\n%s", prettyprint_dict(metadata_result))

    # check some samples
    assert metadata_result["masterdata"]["smda"]["country"][0]["identifier"] == "Norway"
    assert metadata_result["access"]["ssdl"]["access_level"] == "internal"
    assert metadata_result["data"]["unit"] == "m"
