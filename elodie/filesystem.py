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

        # Instantiate a plugins object
        self.plugins = Plugins()

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

    def get_all_files(self, path, extensions=None, exclude_regex_list=set()):
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

        # Create a list of compiled regular expressions to match against the file path
        compiled_regex_list = [re.compile(regex) for regex in exclude_regex_list]
        for dirname, dirnames, filenames in os.walk(path):
            for filename in filenames:
                # If file extension is in `extensions` 
                # And if file path is not in exclude regexes
                # Then append to the list
                filename_path = os.path.join(dirname, filename)
                if (
                        os.path.splitext(filename)[1][1:].lower() in extensions and
                        not self.should_exclude(filename_path, compiled_regex_list, False)
                    ):
                    yield filename_path

    def get_current_directory(self):
        """Get the current working directory.

        :returns: str
        """
        return os.getcwd()

    def get_file_name(self, metadata):
        """Generate file name for a photo or video using its metadata.

        Originally we hardcoded the file name to include an ISO date format.
        We use an ISO8601-like format for the file name prefix. Instead of
        colons as the separator for hours, minutes and seconds we use a hyphen.
        https://en.wikipedia.org/wiki/ISO_8601#General_principles

        PR #225 made the file name customizable and fixed issues #107 #110 #111.
        https://github.com/jmathai/elodie/pull/225

        :param media: A Photo or Video instance
        :type media: :class:`~elodie.media.photo.Photo` or
            :class:`~elodie.media.video.Video`
        :returns: str or None for non-photo or non-videos
        """
        if(metadata is None):
            return None

        # Get the name template and definition.
        # Name template is in the form %date-%original_name-%title.%extension
        # Definition is in the form
        #  [
        #    [('date', '%Y-%m-%d_%H-%M-%S')],
        #    [('original_name', '')], [('title', '')], // contains a fallback
        #    [('extension', '')]
        #  ]
        name_template, definition = self.get_file_name_definition()

        name = name_template
        for parts in definition:
            this_value = None
            for this_part in parts:
                part, mask = this_part
                if part in ('date', 'day', 'month', 'year'):
                    this_value = time.strftime(mask, metadata['date_taken'])
                    break
                elif part in ('location', 'city', 'state', 'country'):
                    place_name = geolocation.place_name(
                        metadata['latitude'],
                        metadata['longitude']
                    )

                    location_parts = re.findall('(%[^%]+)', mask)
                    this_value = self.parse_mask_for_location(
                        mask,
                        location_parts,
                        place_name,
                    )
                    break
                elif part in ('album', 'extension', 'title'):
                    if metadata[part]:
                        this_value = re.sub(self.whitespace_regex, '-', metadata[part].strip())
                        break
                elif part in ('original_name'):
                    # First we check if we have metadata['original_name'].
                    # We have to do this for backwards compatibility because
                    #   we original did not store this back into EXIF.
                    if metadata[part]:
                        this_value = os.path.splitext(metadata['original_name'])[0]
                    else:
                        # We didn't always store original_name so this is 
                        #  for backwards compatibility.
                        # We want to remove the hardcoded date prefix we used 
                        #  to add to the name.
                        # This helps when re-running the program on file 
                        #  which were already processed.
                        this_value = re.sub(
                            '^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-',
                            '',
                            metadata['base_name']
                        )
                        if(len(this_value) == 0):
                            this_value = metadata['base_name']

                    # Lastly we want to sanitize the name
                    this_value = re.sub(self.whitespace_regex, '-', this_value.strip())
                elif part.startswith('"') and part.endswith('"'):
                    this_value = part[1:-1]
                    break

            # Here we replace the placeholder with it's corresponding value.
            # Check if this_value was not set so that the placeholder
            #  can be removed completely.
            # For example, %title- will be replaced with ''
            # Else replace the placeholder (i.e. %title) with the value.
            if this_value is None:
                name = re.sub(
                    #'[^a-z_]+%{}'.format(part),
                    '[^a-zA-Z0-9_]+%{}'.format(part),
                    '',
                    name,
                )
            else:
                name = re.sub(
                    '%{}'.format(part),
                    this_value,
                    name,
                )

        config = load_config()

        if('File' in config and 'capitalization' in config['File'] and config['File']['capitalization'] == 'upper'):
            return name.upper()
        else:
            return name.lower()

    def get_file_name_definition(self):
        """Returns a list of folder definitions.

        Each element in the list represents a folder.
        Fallback folders are supported and are nested lists.
        Return values take the following form.
        [
            ('date', '%Y-%m-%d'),
            [
                ('location', '%city'),
                ('album', ''),
                ('"Unknown Location", '')
            ]
        ]

        :returns: list
        """
        # If we've done this already then return it immediately without
        # incurring any extra work
        if self.cached_file_name_definition is not None:
            return self.cached_file_name_definition

        config = load_config()

        # If File is in the config we assume name and its
        #  corresponding values are also present
        config_file = self.default_file_name_definition
        if('File' in config):
            config_file = config['File']

        # Find all subpatterns of name that map to the components of the file's
        #  name.
        #  I.e. %date-%original_name-%title.%extension => ['date', 'original_name', 'title', 'extension'] #noqa
        path_parts = re.findall(
                         '(\%[a-z_]+)',
                         config_file['name']
                     )

        if not path_parts or len(path_parts) == 0:
            return (config_file['name'], self.default_file_name_definition)

        self.cached_file_name_definition = []
        for part in path_parts:
            if part in config_file:
                part = part[1:]
                self.cached_file_name_definition.append(
                    [(part, config_file[part])]
                )
            else:
                this_part = []
                for p in part.split('|'):
                    p = p[1:]
                    this_part.append(
                        (p, config_file[p] if p in config_file else '')
                    )
                self.cached_file_name_definition.append(this_part)

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
            log.info('Could not get checksum for %s.' % _file)
            return None

        # If duplicates are not allowed then we check if we've seen this file
        #  before via checksum. We also check that the file exists at the
        #   location we believe it to be.
        # If we find a checksum match but the file doesn't exist where we
        #  believe it to be then we write a debug log and proceed to import.
        checksum_file = db.get_hash(checksum)
        if(allow_duplicate is False and checksum_file is not None):
            if(os.path.isfile(checksum_file)):
                log.info('%s already at %s.' % (
                    _file,
                    checksum_file
                ))
                return None
            else:
                log.info('%s matched checksum but file not found at %s.' % (  # noqa
                    _file,
                    checksum_file
                ))
        return checksum

    def process_file(self, _file, destination, media, **kwargs):
        move = False
        if('move' in kwargs):
            move = kwargs['move']

        allow_duplicate = False
        if('allowDuplicate' in kwargs):
            allow_duplicate = kwargs['allowDuplicate']

        stat_info_original = os.stat(_file)
        metadata = media.get_metadata()

        if(not media.is_valid()):
            print('%s is not a valid media file. Skipping...' % _file)
            return

        checksum = self.process_checksum(_file, allow_duplicate)
        if(checksum is None):
            log.info('Original checksum returned None for %s. Skipping...' %
                     _file)
            return

        # Run `before()` for every loaded plugin and if any of them raise an exception
        #  then we skip importing the file and log a message.
        plugins_run_before_status = self.plugins.run_all_before(_file, destination)
        if(plugins_run_before_status == False):
            log.warn('At least one plugin pre-run failed for %s' % _file)
            return

        directory_name = self.get_folder_path(metadata)
        dest_directory = os.path.join(destination, directory_name)
        file_name = self.get_file_name(metadata)
        dest_path = os.path.join(dest_directory, file_name)        

        media.set_original_name()

        # If source and destination are identical then
        #  we should not write the file. gh-210
        if(_file == dest_path):
            print('Final source and destination path should not be identical')
            return

        self.create_directory(dest_directory)

        # exiftool renames the original file by appending '_original' to the
        # file name. A new file is written with new tags with the initial file
        # name. See exiftool man page for more details.
        exif_original_file = _file + '_original'

        # Check if the source file was processed by exiftool and an _original
        # file was created.
        exif_original_file_exists = False
        if(os.path.exists(exif_original_file)):
            exif_original_file_exists = True

        if(move is True):
            stat = os.stat(_file)
            # Move the processed file into the destination directory
            shutil.move(_file, dest_path)

            if(exif_original_file_exists is True):
                # We can remove it as we don't need the initial file.
                os.remove(exif_original_file)
            os.utime(dest_path, (stat.st_atime, stat.st_mtime))
        else:
            compatibility._copyfile(_file, dest_path)
            self.set_utime_from_metadata(media.get_metadata(), dest_path)

        db = Db()
        db.add_hash(checksum, dest_path)
        db.update_hash_db()

        # Run `after()` for every loaded plugin and if any of them raise an exception
        #  then we skip importing the file and log a message.
        plugins_run_after_status = self.plugins.run_all_after(_file, destination, dest_path, metadata)
        if(plugins_run_after_status == False):
            log.warn('At least one plugin pre-run failed for %s' % _file)
            return


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

    def should_exclude(self, path, regex_list=set(), needs_compiled=False):
        if(len(regex_list) == 0):
            return False

        if(needs_compiled):
            compiled_list = []
            for regex in regex_list:
                compiled_list.append(re.compile(regex))
            regex_list = compiled_list

        return any(regex.search(path) for regex in regex_list)
