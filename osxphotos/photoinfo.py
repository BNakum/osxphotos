"""
PhotoInfo class
Represents a single photo in the Photos library and provides access to the photo's attributes
PhotosDB.photos() returns a list of PhotoInfo objects
"""

import glob
import json
import logging
import os.path
import pathlib
import re
import subprocess
import sys
from datetime import timedelta, timezone
from pprint import pformat

import yaml
from mako.template import Template

from ._constants import (
    _MOVIE_TYPE,
    _PHOTO_TYPE,
    _PHOTOS_5_SHARED_PHOTO_PATH,
    _PHOTOS_5_VERSION,
    _TEMPLATE_DIR,
    _XMP_TEMPLATE_NAME,
)
from .utils import (
    _copy_file,
    _export_photo_uuid_applescript,
    _get_resource_loc,
    dd_to_dms_str,
)


class PhotoInfo:
    """
    Info about a specific photo, contains all the details about the photo
    including keywords, persons, albums, uuid, path, etc.
    """

    def __init__(self, db=None, uuid=None, info=None):
        self._uuid = uuid
        self._info = info
        self._db = db

    @property
    def filename(self):
        """ filename of the picture """
        return self._info["filename"]

    @property
    def original_filename(self):
        """ original filename of the picture 
            Photos 5 mangles filenames upon import """
        return self._info["originalFilename"]

    @property
    def date(self):
        """ image creation date as timezone aware datetime object """
        imagedate = self._info["imageDate"]
        seconds = self._info["imageTimeZoneOffsetSeconds"] or 0
        delta = timedelta(seconds=seconds)
        tz = timezone(delta)
        imagedate_utc = imagedate.astimezone(tz=tz)
        return imagedate_utc

    @property
    def date_modified(self):
        """ image modification date as timezone aware datetime object
            or None if no modification date set """
        imagedate = self._info["lastmodifieddate"]
        if imagedate:
            seconds = self._info["imageTimeZoneOffsetSeconds"] or 0
            delta = timedelta(seconds=seconds)
            tz = timezone(delta)
            imagedate_utc = imagedate.astimezone(tz=tz)
            return imagedate_utc
        else:
            return None

    @property
    def tzoffset(self):
        """ timezone offset from UTC in seconds """
        return self._info["imageTimeZoneOffsetSeconds"]

    @property
    def path(self):
        """ absolute path on disk of the original picture """

        photopath = None
        if self._info["isMissing"] == 1:
            return photopath  # path would be meaningless until downloaded

        if self._db._db_version < _PHOTOS_5_VERSION:
            vol = self._info["volume"]
            if vol is not None:
                photopath = os.path.join("/Volumes", vol, self._info["imagePath"])
            else:
                photopath = os.path.join(
                    self._db._masters_path, self._info["imagePath"]
                )
            return photopath
            # TODO: Is there a way to use applescript or PhotoKit to force the download in this

        if self._info["shared"]:
            # shared photo
            photopath = os.path.join(
                self._db._library_path,
                _PHOTOS_5_SHARED_PHOTO_PATH,
                self._info["directory"],
                self._info["filename"],
            )
            return photopath

        # if self._info["masterFingerprint"]:
        # if masterFingerprint is not null, path appears to be valid
        if self._info["directory"].startswith("/"):
            photopath = os.path.join(self._info["directory"], self._info["filename"])
        else:
            photopath = os.path.join(
                self._db._masters_path, self._info["directory"], self._info["filename"]
            )
        return photopath

        # if all else fails, photopath = None
        # photopath = None
        # logging.debug(
        #     f"WARNING: photopath None, masterFingerprint null, not shared {pformat(self._info)}"
        # )
        # return photopath

    @property
    def path_edited(self):
        """ absolute path on disk of the edited picture """
        """ None if photo has not been edited """

        # TODO: break this code into a _path_edited_4 and _path_edited_5
        # version to simplify the big if/then; same for path_live_photo

        photopath = None

        if self._db._db_version < _PHOTOS_5_VERSION:
            if self._info["hasAdjustments"]:
                edit_id = self._info["edit_resource_id"]
                if edit_id is not None:
                    library = self._db._library_path
                    folder_id, file_id = _get_resource_loc(edit_id)
                    # todo: is this always true or do we need to search file file_id under folder_id
                    # figure out what kind it is and build filename
                    filename = None
                    if self._info["type"] == _PHOTO_TYPE:
                        # it's a photo
                        filename = f"fullsizeoutput_{file_id}.jpeg"
                    elif self._info["type"] == _MOVIE_TYPE:
                        # it's a movie
                        filename = f"fullsizeoutput_{file_id}.mov"
                    else:
                        # don't know what it is!
                        logging.debug(f"WARNING: unknown type {self._info['type']}")
                        return None

                    # photopath appears to usually be in "00" subfolder but
                    # could be elsewhere--I haven't figured out this logic yet
                    # first see if it's in 00
                    photopath = os.path.join(
                        library,
                        "resources",
                        "media",
                        "version",
                        folder_id,
                        "00",
                        filename,
                    )

                    if not os.path.isfile(photopath):
                        rootdir = os.path.join(
                            library, "resources", "media", "version", folder_id
                        )

                        for dirname, _, filelist in os.walk(rootdir):
                            if filename in filelist:
                                photopath = os.path.join(dirname, filename)
                                break

                    # check again to see if we found a valid file
                    if not os.path.isfile(photopath):
                        logging.debug(
                            f"MISSING PATH: edited file for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                        )
                        photopath = None
                else:
                    logging.debug(
                        f"{self.uuid} hasAdjustments but edit_resource_id is None"
                    )
                    photopath = None
            else:
                photopath = None

            # if self._info["isMissing"] == 1:
            #     photopath = None  # path would be meaningless until downloaded
        else:
            # in Photos 5.0 / Catalina / MacOS 10.15:
            # edited photos appear to always be converted to .jpeg and stored in
            # library_name/resources/renders/X/UUID_1_201_a.jpeg
            # where X = first letter of UUID
            # and UUID = UUID of image
            # this seems to be true even for photos not copied to Photos library and
            # where original format was not jpg/jpeg
            # if more than one edit, previous edit is stored as UUID_p.jpeg

            if self._info["hasAdjustments"]:
                library = self._db._library_path
                directory = self._uuid[0]  # first char of uuid
                filename = None
                if self._info["type"] == _PHOTO_TYPE:
                    # it's a photo
                    filename = f"{self._uuid}_1_201_a.jpeg"
                elif self._info["type"] == _MOVIE_TYPE:
                    # it's a movie
                    filename = f"{self._uuid}_2_0_a.mov"
                else:
                    # don't know what it is!
                    logging.debug(f"WARNING: unknown type {self._info['type']}")
                    return None

                photopath = os.path.join(
                    library, "resources", "renders", directory, filename
                )

                if not os.path.isfile(photopath):
                    logging.debug(
                        f"edited file for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                    )
                    photopath = None
            else:
                photopath = None

            # TODO: might be possible for original/master to be missing but edit to still be there
            # if self._info["isMissing"] == 1:
            #     photopath = None  # path would be meaningless until downloaded

            logging.debug(photopath)

        return photopath

    @property
    def description(self):
        """ long / extended description of picture """
        return self._info["extendedDescription"]

    @property
    def persons(self):
        """ list of persons in picture """
        return self._info["persons"]

    @property
    def albums(self):
        """ list of albums picture is contained in """
        albums = []
        for album in self._info["albums"]:
            albums.append(self._db._dbalbum_details[album]["title"])
        return albums

    @property
    def keywords(self):
        """ list of keywords for picture """
        return self._info["keywords"]

    @property
    def title(self):
        """ name / title of picture """
        return self._info["name"]

    @property
    def uuid(self):
        """ UUID of picture """
        return self._uuid

    @property
    def ismissing(self):
        """ returns true if photo is missing from disk (which means it's not been downloaded from iCloud) 
        NOTE:   the photos.db database uses an asynchrounous write-ahead log so changes in Photos
                do not immediately get written to disk. In particular, I've noticed that downloading 
                an image from the cloud does not force the database to be updated until something else
                e.g. an edit, keyword, etc. occurs forcing a database synch
                The exact process / timing is a mystery to be but be aware that if some photos were recently
                downloaded from cloud to local storate their status in the database might still show
                isMissing = 1
        """
        return True if self._info["isMissing"] == 1 else False

    @property
    def hasadjustments(self):
        """ True if picture has adjustments / edits """
        return True if self._info["hasAdjustments"] == 1 else False

    @property
    def external_edit(self):
        """ Returns True if picture was edited outside of Photos using external editor """
        return (
            True
            if self._info["adjustmentFormatID"] == "com.apple.Photos.externalEdit"
            else False
        )

    @property
    def favorite(self):
        """ True if picture is marked as favorite """
        return True if self._info["favorite"] == 1 else False

    @property
    def hidden(self):
        """ True if picture is hidden """
        return True if self._info["hidden"] == 1 else False

    @property
    def location(self):
        """ returns (latitude, longitude) as float in degrees or None """
        return (self._latitude, self._longitude)

    @property
    def shared(self):
        """ returns True if photos is in a shared iCloud album otherwise false
            Only valid on Photos 5; returns None on older versions """
        if self._db._db_version >= _PHOTOS_5_VERSION:
            return self._info["shared"]
        else:
            return None

    @property
    def uti(self):
        """ Returns Uniform Type Identifier (UTI) for the image
            for example: public.jpeg or com.apple.quicktime-movie
        """
        return self._info["UTI"]

    @property
    def ismovie(self):
        """ Returns True if file is a movie, otherwise False
        """
        return True if self._info["type"] == _MOVIE_TYPE else False

    @property
    def isphoto(self):
        """ Returns True if file is an image, otherwise False
        """
        return True if self._info["type"] == _PHOTO_TYPE else False

    @property
    def incloud(self):
        """ Returns True if photo is cloud asset and is synched to cloud
                    False if photo is cloud asset and not yet synched to cloud
                    None if photo is not cloud asset
        """
        return self._info["incloud"]

    @property
    def iscloudasset(self):
        """ Returns True if photo is a cloud asset (in an iCloud library),
            otherwise False 
        """
        if self._db._db_version < _PHOTOS_5_VERSION:
            return (
                True
                if self._info["cloudLibraryState"] is not None
                and self._info["cloudLibraryState"] != 0
                else False
            )
        else:
            return True if self._info["cloudAssetGUID"] is not None else False

    @property
    def burst(self):
        """ Returns True if photo is part of a Burst photo set, otherwise False """
        return self._info["burst"]

    @property
    def burst_photos(self):
        """ If photo is a burst photo, returns list of PhotoInfo objects 
            that are part of the same burst photo set; otherwise returns empty list.
            self is not included in the returned list """
        if self._info["burst"]:
            burst_uuid = self._info["burstUUID"]
            burst_photos = [
                PhotoInfo(db=self._db, uuid=u, info=self._db._dbphotos[u])
                for u in self._db._dbphotos_burst[burst_uuid]
                if u != self._uuid
            ]
            return burst_photos
        else:
            return []

    @property
    def live_photo(self):
        """ Returns True if photo is a live photo, otherwise False """
        return self._info["live_photo"]

    @property
    def path_live_photo(self):
        """ Returns path to the associated video file for a live photo
            If photo is not a live photo, returns None
            If photo is missing, returns None """

        photopath = None
        if self._db._db_version < _PHOTOS_5_VERSION:
            if self.live_photo and not self.ismissing:
                live_model_id = self._info["live_model_id"]
                if live_model_id == None:
                    logging.debug(f"missing live_model_id: {self._uuid}")
                    photopath = None
                else:
                    folder_id, file_id = _get_resource_loc(live_model_id)
                    library_path = self._db.library_path
                    photopath = os.path.join(
                        library_path,
                        "resources",
                        "media",
                        "master",
                        folder_id,
                        "00",
                        f"jpegvideocomplement_{file_id}.mov",
                    )
                    if not os.path.isfile(photopath):
                        # In testing, I've seen occasional missing movie for live photo
                        # These appear to be valid -- e.g. live component hasn't been downloaded from iCloud
                        # photos 4 has "isOnDisk" column we could check
                        # or could do the actual check with "isfile"
                        # TODO: should this be a warning or debug?
                        logging.debug(
                            f"MISSING PATH: live photo path for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                        )
                        photopath = None
            else:
                photopath = None
        else:
            # Photos 5
            if self.live_photo and not self.ismissing:
                filename = pathlib.Path(self.path)
                photopath = filename.parent.joinpath(f"{filename.stem}_3.mov")
                photopath = str(photopath)
                if not os.path.isfile(photopath):
                    # In testing, I've seen occasional missing movie for live photo
                    # these appear to be valid -- e.g. video component not yet downloaded from iCloud
                    # TODO: should this be a warning or debug?
                    logging.debug(
                        f"MISSING PATH: live photo path for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                    )
                    photopath = None
            else:
                photopath = None

        return photopath

    def export(
        self,
        dest,
        *filename,
        edited=False,
        overwrite=False,
        increment=True,
        sidecar_json=False,
        sidecar_xmp=False,
        use_photos_export=False,
        timeout=120,
    ):
        """ export photo 
            dest: must be valid destination path (or exception raised) 
            filename: (optional): name of picture; if not provided, will use current filename 
            edited: (boolean, default=False); if True will export the edited version of the photo 
                    (or raise exception if no edited version) 
            overwrite: (boolean, default=False); if True will overwrite files if they alreay exist 
            increment: (boolean, default=True); if True, will increment file name until a non-existant name is found 
                       if overwrite=False and increment=False, export will fail if destination file already exists 
            sidecar_json: (boolean, default = False); if True will also write a json sidecar with IPTC data in format readable by exiftool
                      sidecar filename will be dest/filename.json 
            sidecar_xmp: (boolean, default = False); if True will also write a XMP sidecar with IPTC data 
                      sidecar filename will be dest/filename.xmp 
            use_photos_export: (boolean, default=False); if True will attempt to export photo via applescript interaction with Photos
            timeout: (int, default=120) timeout in seconds used with use_photos_export
            returns the full path to the exported file """

        # TODO: add this docs:
        #  ( for jpeg in *.jpeg; do exiftool -v -json=$jpeg.json $jpeg; done )

        # check arguments and get destination path and filename (if provided)
        if filename and len(filename) > 2:
            raise TypeError(
                "Too many positional arguments.  Should be at most two: destination, filename."
            )
        else:
            # verify destination is a valid path
            if dest is None:
                raise ValueError("Destination must not be None")
            elif not os.path.isdir(dest):
                raise FileNotFoundError("Invalid path passed to export")

            if filename and len(filename) == 1:
                # second arg is filename of picture
                filename = filename[0]
            else:
                # no filename provided so use the default
                # if edited file requested, use filename but add _edited
                # need to use file extension from edited file as Photos saves a jpeg once edited
                if edited:
                    # verify we have a valid path_edited and use that to get filename
                    if not self.path_edited:
                        raise FileNotFoundError(
                            "edited=True but path_edited is none; hasadjustments: "
                            f" {self.hasadjustments}"
                        )
                    edited_name = pathlib.Path(self.path_edited).name
                    edited_suffix = pathlib.Path(edited_name).suffix
                    filename = (
                        pathlib.Path(self.filename).stem + "_edited" + edited_suffix
                    )
                else:
                    filename = self.filename

        # check destination path
        dest = pathlib.Path(dest)
        filename = pathlib.Path(filename)
        dest = dest / filename

        # check to see if file exists and if so, add (1), (2), etc until we find one that works
        # Photos checks the stem and adds (1), (2), etc which avoids collision with sidecars
        # e.g. exporting sidecar for file1.png and file1.jpeg
        # if file1.png exists and exporting file1.jpeg,
        # dest will be file1 (1).jpeg even though file1.jpeg doesn't exist to prevent sidecar collision
        if increment and not overwrite:
            count = 1
            glob_str = str(dest.parent / f"{dest.stem}*")
            dest_files = glob.glob(glob_str)
            dest_files = [pathlib.Path(f).stem for f in dest_files]
            dest_new = dest.stem
            while dest_new in dest_files:
                dest_new = f"{dest.stem} ({count})"
                count += 1
            dest = dest.parent / f"{dest_new}{dest.suffix}"

        # if overwrite==False and #increment==False, export should fail if file exists
        if dest.exists() and not overwrite and not increment:
            raise FileExistsError(
                f"destination exists ({dest}); overwrite={overwrite}, increment={increment}"
            )

        if not use_photos_export:
            # find the source file on disk and export
            # get path to source file and verify it's not None and is valid file
            # TODO: how to handle ismissing or not hasadjustments and edited=True cases?
            if edited:
                if not self.hasadjustments:
                    logging.warning(
                        "Attempting to export edited photo but hasadjustments=False"
                    )

                if self.path_edited is not None:
                    src = self.path_edited
                else:
                    raise FileNotFoundError(
                        f"edited=True but path_edited is none; hasadjustments: {self.hasadjustments}"
                    )
            else:
                if self.ismissing:
                    logging.warning(
                        f"Attempting to export photo with ismissing=True: path = {self.path}"
                    )

                if self.path is None:
                    logging.warning(
                        f"Attempting to export photo but path is None: ismissing = {self.ismissing}"
                    )
                    raise FileNotFoundError("Cannot export photo if path is None")
                else:
                    src = self.path

            if not os.path.isfile(src):
                raise FileNotFoundError(f"{src} does not appear to exist")

            logging.debug(
                f"exporting {src} to {dest}, overwrite={overwrite}, increment={increment}, dest exists: {dest.exists()}"
            )

            # copy the file, _copy_file uses ditto to preserve Mac extended attributes
            _copy_file(src, dest)
        else:
            # use_photo_export
            exported = None
            if edited:
                # exported edited version and not original
                exported = _export_photo_uuid_applescript(
                    self.uuid, dest, original=False, edited=True, timeout=timeout
                )
            else:
                # export original version and not edited
                exported = _export_photo_uuid_applescript(
                    self.uuid, dest, original=True, edited=False, timeout=timeout
                )

            if exported is None:
                logging.warning(f"Error exporting photo {self.uuid} to {dest}")

        if sidecar_json:
            logging.debug("writing exiftool_json_sidecar")
            sidecar_filename = dest.parent / pathlib.Path(f"{dest.stem}.json")
            sidecar_str = self._exiftool_json_sidecar()
            try:
                self._write_sidecar(sidecar_filename, sidecar_str)
            except Exception as e:
                logging.warning(f"Error writing json sidecar to {sidecar_filename}")
                raise e

        if sidecar_xmp:
            logging.debug("writing xmp_sidecar")
            sidecar_filename = dest.parent / pathlib.Path(f"{dest.stem}.xmp")
            sidecar_str = self._xmp_sidecar()
            try:
                self._write_sidecar(sidecar_filename, sidecar_str)
            except Exception as e:
                logging.warning(f"Error writing xmp sidecar to {sidecar_filename}")
                raise e

        return str(dest)

    def _exiftool_json_sidecar(self):
        """ return json string of EXIF details in exiftool sidecar format
            Does not include all the EXIF fields as those are likely already in the image
            Exports the following:
                FileName
                ImageDescription
                Description
                Title
                TagsList
                Keywords
                Subject
                PersonInImage
                GPSLatitude, GPSLongitude
                GPSPosition
                GPSLatitudeRef, GPSLongitudeRef
                DateTimeOriginal
                OffsetTimeOriginal
                ModifyDate """

        exif = {}
        exif["_CreatedBy"] = "osxphotos, https://github.com/RhetTbull/osxphotos"
        exif["FileName"] = self.filename

        if self.description:
            exif["ImageDescription"] = self.description
            exif["Description"] = self.description

        if self.title:
            exif["Title"] = self.title

        if self.keywords:
            exif["TagsList"] = exif["Keywords"] = list(self.keywords)
            # Photos puts both keywords and persons in Subject when using "Export IPTC as XMP"
            exif["Subject"] = list(self.keywords)

        if self.persons:
            exif["PersonInImage"] = self.persons
            # Photos puts both keywords and persons in Subject when using "Export IPTC as XMP"
            if "Subject" in exif:
                exif["Subject"].extend(self.persons)
            else:
                exif["Subject"] = self.persons

        # if self.favorite():
        #     exif["Rating"] = 5

        (lat, lon) = self.location
        if lat is not None and lon is not None:
            lat_str, lon_str = dd_to_dms_str(lat, lon)
            exif["GPSLatitude"] = lat_str
            exif["GPSLongitude"] = lon_str
            exif["GPSPosition"] = f"{lat_str}, {lon_str}"
            lat_ref = "North" if lat >= 0 else "South"
            lon_ref = "East" if lon >= 0 else "West"
            exif["GPSLatitudeRef"] = lat_ref
            exif["GPSLongitudeRef"] = lon_ref

        # process date/time and timezone offset
        date = self.date
        # exiftool expects format to "2015:01:18 12:00:00"
        datetimeoriginal = date.strftime("%Y:%m:%d %H:%M:%S")
        offsettime = date.strftime("%z")
        # find timezone offset in format "-04:00"
        offset = re.findall(r"([+-]?)([\d]{2})([\d]{2})", offsettime)
        offset = offset[0]  # findall returns list of tuples
        offsettime = f"{offset[0]}{offset[1]}:{offset[2]}"
        exif["DateTimeOriginal"] = datetimeoriginal
        exif["OffsetTimeOriginal"] = offsettime

        if self.date_modified is not None:
            exif["ModifyDate"] = self.date_modified.strftime("%Y:%m:%d %H:%M:%S")

        json_str = json.dumps([exif])
        return json_str

    def _xmp_sidecar(self):
        """ returns string for XMP sidecar """
        # TODO: add additional fields to XMP file?
        
        xmp_template = Template(
            filename=os.path.join(_TEMPLATE_DIR, _XMP_TEMPLATE_NAME)
        )
        xmp_str = xmp_template.render(photo=self)
        # remove extra lines that mako inserts from template
        xmp_str = "\n".join([line for line in xmp_str.split("\n") if line.strip() != ""])
        return xmp_str

    def _write_sidecar(self, filename, sidecar_str):
        """ write sidecar_str to filename
            used for exporting sidecar info """
        if not filename and not sidecar_str:
            raise (
                ValueError(
                    f"filename {filename} and sidecar_str {sidecar_str} must not be None"
                )
            )

        # TODO: catch exception?
        f = open(filename, "w")
        f.write(sidecar_str)
        f.close()

    @property
    def _longitude(self):
        """ Returns longitude, in degrees """
        return self._info["longitude"]

    @property
    def _latitude(self):
        """ Returns latitude, in degrees """
        return self._info["latitude"]

    def __repr__(self):
        return f"osxphotos.{self.__class__.__name__}(db={self._db}, uuid='{self._uuid}', info={self._info})"

    def __str__(self):
        """ string representation of PhotoInfo object """

        date_iso = self.date.isoformat()
        date_modified_iso = (
            self.date_modified.isoformat() if self.date_modified else None
        )

        info = {
            "uuid": self.uuid,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "date": date_iso,
            "description": self.description,
            "title": self.title,
            "keywords": self.keywords,
            "albums": self.albums,
            "persons": self.persons,
            "path": self.path,
            "ismissing": self.ismissing,
            "hasadjustments": self.hasadjustments,
            "external_edit": self.external_edit,
            "favorite": self.favorite,
            "hidden": self.hidden,
            "latitude": self._latitude,
            "longitude": self._longitude,
            "path_edited": self.path_edited,
            "shared": self.shared,
            "isphoto": self.isphoto,
            "ismovie": self.ismovie,
            "uti": self.uti,
            "burst": self.burst,
            "live_photo": self.live_photo,
            "path_live_photo": self.path_live_photo,
            "iscloudasset": self.iscloudasset,
            "incloud": self.incloud,
            "date_modified": date_modified_iso,
        }
        return yaml.dump(info, sort_keys=False)

    def json(self):
        """ return JSON representation """

        date_modified_iso = (
            self.date_modified.isoformat() if self.date_modified else None
        )

        pic = {
            "uuid": self.uuid,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "date": self.date.isoformat(),
            "description": self.description,
            "title": self.title,
            "keywords": self.keywords,
            "albums": self.albums,
            "persons": self.persons,
            "path": self.path,
            "ismissing": self.ismissing,
            "hasadjustments": self.hasadjustments,
            "external_edit": self.external_edit,
            "favorite": self.favorite,
            "hidden": self.hidden,
            "latitude": self._latitude,
            "longitude": self._longitude,
            "path_edited": self.path_edited,
            "shared": self.shared,
            "isphoto": self.isphoto,
            "ismovie": self.ismovie,
            "uti": self.uti,
            "burst": self.burst,
            "live_photo": self.live_photo,
            "path_live_photo": self.path_live_photo,
            "iscloudasset": self.iscloudasset,
            "incloud": self.incloud,
            "date_modified": date_modified_iso,
        }
        return json.dumps(pic)

    # compare two PhotoInfo objects for equality
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__

        return False

    def __ne__(self, other):
        return not self.__eq__(other)
