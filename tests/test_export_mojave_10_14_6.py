import pytest

from osxphotos._constants import _UNKNOWN_PERSON

# TODO: put some of this code into a pre-function


PHOTOS_DB = "./tests/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-10.14.6.photoslibrary"

KEYWORDS = [
    "Kids",
    "wedding",
    "flowers",
    "England",
    "London",
    "London 2018",
    "St. James's Park",
    "UK",
    "United Kingdom",
]
PERSONS = ["Katie", "Suzy", "Maria"]
ALBUMS = ["Pumpkin Farm", "Test Album", "Test Album (1)"]
KEYWORDS_DICT = {
    "Kids": 4,
    "wedding": 2,
    "flowers": 1,
    "England": 1,
    "London": 1,
    "London 2018": 1,
    "St. James's Park": 1,
    "UK": 1,
    "United Kingdom": 1,
}
PERSONS_DICT = {"Katie": 3, "Suzy": 2, "Maria": 1}
ALBUM_DICT = {"Pumpkin Farm": 3, "Test Album": 1, "Test Album (1)": 1}

UUID_DICT = {
    "missing": "od0fmC7NQx+ayVr+%i06XA",
    "has_adjustments": "6bxcNnzRQKGnK4uPrCJ9UQ",
    "no_adjustments": "15uNd7%8RguTEgNPKHfTWw",
    "export": "15uNd7%8RguTEgNPKHfTWw",
    "location": "3Jn73XpSQQCluzRBMWRsMA",
    "xmp": "8SOE9s0XQVGsuq4ONohTng",
}


def test_export_1():
    # test basic export
    # get an unedited image and export it using default filename
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest)

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)

    # remove the temporary file
    os.remove(got_dest)


def test_export_2():
    # test export with user provided filename
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename)

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)

    # remove the temporary file
    os.remove(got_dest)


def test_export_3():
    # test file already exists and test increment=True (default)
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    filename2 = pathlib.Path(filename)
    filename2 = f"{filename2.stem} (1){filename2.suffix}"
    expected_dest = os.path.join(dest, filename)
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest = photos[0].export(dest)
    got_dest_2 = photos[0].export(dest)

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)

    # remove the temporary file
    os.remove(got_dest)
    os.remove(got_dest_2)


def test_export_4():
    # test user supplied file already exists and test increment=True (default)
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    filename2 = f"osxphotos-export-2-test-{timestamp} (1).jpg"
    expected_dest = os.path.join(dest, filename)
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest = photos[0].export(dest, filename)
    got_dest_2 = photos[0].export(dest, filename)

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)

    # remove the temporary file
    os.remove(got_dest)
    os.remove(got_dest_2)


def test_export_5():
    # test file already exists and test increment=True (default)
    # and overwrite = True
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)
    got_dest_2 = photos[0].export(dest, overwrite=True)

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)

    # remove the temporary file
    os.remove(got_dest)


def test_export_6():
    # test user supplied file already exists and test increment=True (default)
    # and overwrite = True
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename)
    got_dest_2 = photos[0].export(dest, filename, overwrite=True)

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)

    # remove the temporary file
    os.remove(got_dest)


def test_export_7():
    # test file already exists and test increment=False (not default), overwrite=False (default)
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)
    with pytest.raises(Exception) as e:
        # try to export again with increment = False
        assert photos[0].export(dest, increment=False)
    assert e.type == type(FileExistsError())

    # remove the temporary file
    os.remove(got_dest)


def test_export_8():
    # try to export missing file
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["missing"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest)
    assert e.type == type(FileNotFoundError())


def test_export_9():
    # try to export edited file that's not edited
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, edited=True)
    assert e.type == type(FileNotFoundError())


def test_export_10():
    # try to export edited file that's not edited and name provided
    # should raise exception
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, filename, edited=True)
    assert e.type == type(FileNotFoundError())


def test_export_11():
    # export edited file with name provided
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename, edited=True)
    assert got_dest == expected_dest

    # remove the temporary file
    os.remove(got_dest)


def test_export_12():
    # export edited file with default name
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    edited_name = pathlib.Path(photos[0].path_edited).name
    edited_suffix = pathlib.Path(edited_name).suffix
    filename = pathlib.Path(photos[0].filename).stem + "_edited" + edited_suffix
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, edited=True)
    assert got_dest == expected_dest

    # remove the temporary file
    os.remove(got_dest)


def test_export_13():
    # export to invalid destination
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()

    # create a folder that doesn't exist
    i = 0
    while os.path.isdir(dest):
        dest = os.path.join(dest, str(i))
        i += 1

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest)
    assert e.type == type(FileNotFoundError())


def test_exiftool_json_sidecar():
    import osxphotos
    import json

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["location"]])

    json_expected = json.loads(
        """
    [{"FileName": "St James Park.jpg", 
    "Title": "St. James\'s Park", 
    "TagsList": ["London 2018", "St. James\'s Park", "England", "United Kingdom", "UK", "London"], 
    "Keywords": ["London 2018", "St. James\'s Park", "England", "United Kingdom", "UK", "London"], 
    "Subject": ["London 2018", "St. James\'s Park", "England", "United Kingdom", "UK", "London"], 
    "GPSLatitude": "51 deg 30\' 12.86\\" N", 
    "GPSLongitude": "0 deg 7\' 54.50\\" W", 
    "GPSPosition": "51 deg 30\' 12.86\\" N, 0 deg 7\' 54.50\\" W", 
    "GPSLatitudeRef": "North", "GPSLongitudeRef": "West", 
    "DateTimeOriginal": "2018:10:13 09:18:12", 
    "OffsetTimeOriginal": "-04:00",
    "ModifyDate": "2019:12:01 11:43:45"}]
    """
    )

    json_got = photos[0]._exiftool_json_sidecar()
    json_got = json.loads(json_got)

    # some gymnastics to account for different sort order in different pythons
    for item in zip(sorted(json_got[0].items()), sorted(json_expected[0].items())):
        if type(item[0][1]) in (list, tuple):
            assert sorted(item[0][1]) == sorted(item[1][1])
        else:
            assert item[0][1] == item[1][1]


def test_xmp_sidecar():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["xmp"]])

    xmp_expected = """<!-- Created with osxphotos https://github.com/RhetTbull/osxphotos -->
        <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">
        <!-- mirrors Photos 5 "Export IPTC as XMP" option -->
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about="" 
            xmlns:dc="http://purl.org/dc/elements/1.1/" 
            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
        <dc:description>Girls with pumpkins</dc:description>
        <dc:title>Can we carry this?</dc:title>
        <!-- keywords and persons listed in <dc:subject> as Photos does -->
        <dc:subject>
            <rdf:Seq>
                <rdf:li>Kids</rdf:li>
                <rdf:li>Suzy</rdf:li>
                <rdf:li>Katie</rdf:li>
            </rdf:Seq>
        </dc:subject>
        <photoshop:DateCreated>2018-09-28T15:35:49.063000-04:00</photoshop:DateCreated>
        </rdf:Description>
        <rdf:Description rdf:about='' 
            xmlns:Iptc4xmpExt='http://iptc.org/std/Iptc4xmpExt/2008-02-29/'>
        <Iptc4xmpExt:PersonInImage>
            <rdf:Bag>
                    <rdf:li>Suzy</rdf:li>
                    <rdf:li>Katie</rdf:li>
            </rdf:Bag>
        </Iptc4xmpExt:PersonInImage>
        </rdf:Description>
        <rdf:Description rdf:about='' 
            xmlns:digiKam='http://www.digikam.org/ns/1.0/'>
        <digiKam:TagsList>
            <rdf:Seq>
                <rdf:li>Kids</rdf:li>
            </rdf:Seq>
        </digiKam:TagsList>
        </rdf:Description>
        <rdf:Description rdf:about='' 
            xmlns:xmp='http://ns.adobe.com/xap/1.0/'>
        <xmp:CreateDate>2018-09-28T15:35:49</xmp:CreateDate>
        <xmp:ModifyDate>2018-09-28T15:35:49</xmp:ModifyDate>
        </rdf:Description>
        </rdf:RDF>
         </x:xmpmeta>"""

    xmp_expected_lines = [line.strip() for line in xmp_expected.split("\n")]

    xmp_got = photos[0]._xmp_sidecar()
    xmp_got_lines = [line.strip() for line in xmp_got.split("\n")]

    for line_expected, line_got in zip(xmp_expected_lines, xmp_got_lines):
        assert line_expected == line_got

