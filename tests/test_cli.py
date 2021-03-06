import pytest
from click.testing import CliRunner

CLI_OUTPUT_NO_SUBCOMMAND = [
    "Options:",
    "--db <Photos database path>  Specify Photos database path. Path to Photos",
    "library/database can be specified using either",
    "--db or directly as PHOTOS_LIBRARY positional",
    "argument.",
    "--json                       Print output in JSON format.",
    "-v, --version                Show the version and exit.",
    "-h, --help                   Show this message and exit.",
    "Commands:",
    "  albums    Print out albums found in the Photos library.",
    "  dump      Print list of all photos & associated info from the Photos",
    "  export    Export photos from the Photos database.",
    "  help      Print help; for help on commands: help <command>.",
    "  info      Print out descriptive info of the Photos library database.",
    "  keywords  Print out keywords found in the Photos library.",
    "  list      Print list of Photos libraries found on the system.",
    "  persons   Print out persons (faces) found in the Photos library.",
    "  query     Query the Photos database using 1 or more search options; if",
]

CLI_OUTPUT_QUERY_UUID = '[{"uuid": "D79B8D77-BFFC-460B-9312-034F2877D35B", "filename": "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg", "original_filename": "Pumkins2.jpg", "date": "2018-09-28T16:07:07-04:00", "description": "Girl holding pumpkin", "title": "I found one!", "keywords": ["Kids"], "albums": ["Pumpkin Farm", "Test Album"], "persons": ["Katie"], "path": "/tests/Test-10.15.1.photoslibrary/originals/D/D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg", "ismissing": false, "hasadjustments": false, "external_edit": false, "favorite": false, "hidden": false, "latitude": null, "longitude": null, "path_edited": null, "shared": false, "isphoto": true, "ismovie": false, "uti": "public.jpeg", "burst": false, "live_photo": false, "path_live_photo": null, "iscloudasset": false, "incloud": null}]'

CLI_EXPORT_FILENAMES = [
    "Pumkins1.jpg",
    "Pumkins2.jpg",
    "Pumpkins3.jpg",
    "St James Park.jpg",
    "St James Park_edited.jpg",
    "Tulips.jpg",
    "wedding.jpg",
    "wedding_edited.jpg",
]

CLI_EXPORT_UUID = "D79B8D77-BFFC-460B-9312-034F2877D35B"

CLI_EXPORT_SIDECAR_FILENAMES = ["Pumkins2.jpg", "Pumpkins2.json", "Pumpkins2.xmp"]


def test_osxphotos():
    import osxphotos
    from osxphotos.__main__ import cli

    runner = CliRunner()
    result = runner.invoke(cli, [])
    output = result.output
    assert result.exit_code == 0
    for line in CLI_OUTPUT_NO_SUBCOMMAND:
        assert line in output


def test_query_uuid():
    import json
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            "./tests/Test-10.15.1.photoslibrary",
            "--uuid",
            "D79B8D77-BFFC-460B-9312-034F2877D35B",
        ],
    )
    assert result.exit_code == 0

    json_expected = json.loads(CLI_OUTPUT_QUERY_UUID)[0]
    json_got = json.loads(result.output)[0]

    assert list(json_expected.keys()).sort() == list(json_got.keys()).sort()

    # check values expected vs got
    # path needs special handling as path is set to full path which will differ system to system
    for key_ in json_expected:
        assert key_ in json_got
        if key_ != "path":
            assert json_expected[key_] == json_got[key_]
        else:
            assert json_expected[key_] in json_got[key_]


def test_export():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, "tests/Test-10.15.1.photoslibrary"),
                ".",
                "--original-name",
                "--export-edited",
                "-V",
            ],
        )
        files = glob.glob("*.jpg")
        assert files.sort() == CLI_EXPORT_FILENAMES.sort()


def test_query_date():
    import json
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            "./tests/Test-10.15.1.photoslibrary",
            "--from-date=2018-09-28",
            "--to-date=2018-09-28T23:00:00",
        ],
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert len(json_got) == 4


def test_export_sidecar():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, "tests/Test-10.15.1.photoslibrary"),
                ".",
                "--original-name",
                "-V",
                "--sidecar json",
                "--sidecar xmp",
                f"--uuid {CLI_EXPORT_UUID}",
            ],
        )
        files = glob.glob("*")
        assert files.sort() == CLI_EXPORT_SIDECAR_FILENAMES.sort()
