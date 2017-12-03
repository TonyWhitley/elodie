"""
General file system methods.

.. moduleauthor:: Jaisen Mathai <jaisen@jmathai.com>
"""
from __future__ import print_function
from builtins import object

import os
import re
import shutil
import time

from elodie import compatibility
from elodie import log
from elodie.localstorage import Db
from elodie.media.base import Base, get_all_subclasses
from elodie.destination_folder import DestinationFolder

class FileSystem(object):
    """A class for interacting with the file system."""

    def __init__(self):
        self.destination_folder = DestinationFolder()

    def create_directory(self, directory_path):
        """Create a directory if it does not already exist.

        :param str directory_name: A fully qualified path of the
            to create.
        :returns: bool
        """
        try:
            if os.path.exists(directory_path):
                return True
            else:
                os.makedirs(directory_path)
                return True
        except OSError:
            # OSError is thrown for cases like no permission
            pass

        return False

    def delete_directory_if_empty(self, directory_path):
        """Delete a directory only if it's empty.

        Instead of checking first using `len([name for name in
        os.listdir(directory_path)]) == 0`, we catch the OSError exception.

        :param str directory_name: A fully qualified path of the directory
            to delete.
        """
        try:
            os.rmdir(directory_path)
            return True
        except OSError:
            pass

        return False

    def get_all_files(self, path, extensions=None):
        """Recursively get all files which match a path and extension.

        :param str path string: Path to start recursive file listing
        :param tuple(str) extensions: File extensions to include (whitelist)
        :returns: generator
        """
        # If extensions is None then we get all supported extensions
        if not extensions:
            extensions = set()
            subclasses = get_all_subclasses(Base)
            for cls in subclasses:
                extensions.update(cls.extensions)

        for dirname, dirnames, filenames in os.walk(path):
            for filename in filenames:
                # If file extension is in `extensions` then append to the list
                if os.path.splitext(filename)[1][1:].lower() in extensions:
                    yield os.path.join(dirname, filename)

    def get_current_directory(self):
        """Get the current working directory.

        :returns: str
        """
        return os.getcwd()

    def get_file_name(self, media):
        """Generate file name for a photo or video using its metadata.

        We use an ISO8601-like format for the file name prefix. Instead of
        colons as the separator for hours, minutes and seconds we use a hyphen.
        https://en.wikipedia.org/wiki/ISO_8601#General_principles

        :param media: A Photo or Video instance
        :type media: :class:`~elodie.media.photo.Photo` or
            :class:`~elodie.media.video.Video`
        :returns: str or None for non-photo or non-videos
        """
        if(not media.is_valid()):
            return None

        metadata = media.get_metadata()
        if(metadata is None):
            return None

        # First we check if we have metadata['original_name'].
        # We have to do this for backwards compatibility because
        #   we original did not store this back into EXIF.
        if('original_name' in metadata and metadata['original_name']):
            base_name = os.path.splitext(metadata['original_name'])[0]
        else:
            # If the file has EXIF title we use that in the file name
            #   (i.e. my-favorite-photo-img_1234.jpg)
            # We want to remove the date prefix we add to the name.
            # This helps when re-running the program on file which were already
            #   processed.
            base_name = re.sub(
                '^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-',
                '',
                metadata['base_name']
            )
            if(len(base_name) == 0):
                base_name = metadata['base_name']

        if(
            'title' in metadata and
            metadata['title'] is not None and
            len(metadata['title']) > 0
        ):
            title_sanitized = re.sub('\W+', '-', metadata['title'].strip())
            base_name = base_name.replace('-%s' % title_sanitized, '')
            base_name = '%s-%s' % (base_name, title_sanitized)

        # What if basename already has date_time information?
        # e.g. 20160706_192934.jpg 
        #      20160706_192934-1.jpg 
        # strip it out
        base_name = re.sub(
            '^\d{4}\d{2}\d{2}_\d{2}\d{2}\d{2}',
            '',
            base_name
        )

        file_name = '%s-%s.%s' % (
            time.strftime(
                '%Y-%m-%d_%H-%M-%S',
                metadata['date_taken']
            ),
            base_name,
            metadata['extension'])
        return file_name.lower()

    def process_file(self, _file, destination, media, **kwargs):
        move = False
        if('move' in kwargs):
            move = kwargs['move']

        allow_duplicate = False
        if('allowDuplicate' in kwargs):
            allow_duplicate = kwargs['allowDuplicate']

        if(not media.is_valid()):
            print('%s is not a valid media file. Skipping...' % _file)
            return

        media.set_original_name()
        metadata = media.get_metadata()

        directory_name = self.destination_folder.get_folder_path(metadata)

        dest_directory = os.path.join(destination, directory_name)
        file_name = self.get_file_name(media)
        dest_path = os.path.join(dest_directory, file_name)

        db = Db()
        checksum = db.checksum(_file)
        if(checksum is None):
            log.info('Could not get checksum for %s. Skipping...' % _file)
            return

        # If duplicates are not allowed then we check if we've seen this file
        #  before via checksum. We also check that the file exists at the
        #   location we believe it to be.
        # If we find a checksum match but the file doesn't exist where we
        #  believe it to be then we write a debug log and proceed to import.
        checksum_file = db.get_hash(checksum)
        if(allow_duplicate is False and checksum_file is not None):
            if(os.path.isfile(checksum_file)):
                log.info('%s already exists at %s. Skipping...' % (
                    _file,
                    checksum_file
                ))
                return
            else:
                log.info('%s matched checksum but file not found at %s. Importing again...' % (  # noqa
                    _file,
                    checksum_file
                ))

        # If source and destination are identical then
        #  we should not write the file. gh-210
        if(_file == dest_path):
            print('Final source and destination path should not be identical')
            return

        self.create_directory(dest_directory)

        if(move is True):
            stat = os.stat(_file)
            shutil.move(_file, dest_path)
            os.utime(dest_path, (stat.st_atime, stat.st_mtime))
        else:
            compatibility._copyfile(_file, dest_path)
            self.set_utime_from_metadata(media.get_metadata(), dest_path)

        db.add_hash(checksum, dest_path)
        db.update_hash_db()

        return dest_path

    def set_utime_from_metadata(self, metadata, file_path):
        """ Set the modification time on the file based on the file name.
        """

        # Initialize date taken to what's returned from the metadata function.
        # If the folder and file name follow a time format of
        #   YYYY-MM-DD_HH-MM-SS-IMG_0001.JPG then we override the date_taken
        date_taken = metadata['date_taken']
        base_name = metadata['base_name']
        year_month_day_match = re.search(
            '^(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})',
            base_name
        )
        if(year_month_day_match is not None):
            (year, month, day, hour, minute, second) = year_month_day_match.groups()  # noqa
            date_taken = time.strptime(
                '{}-{}-{} {}:{}:{}'.format(year, month, day, hour, minute, second),  # noqa
                '%Y-%m-%d %H:%M:%S'
            )

            os.utime(file_path, (time.time(), time.mktime(date_taken)))
        else:
            # We don't make any assumptions about time zones and
            # assume local time zone.
            date_taken_in_seconds = time.mktime(date_taken)
            os.utime(file_path, (time.time(), (date_taken_in_seconds)))
