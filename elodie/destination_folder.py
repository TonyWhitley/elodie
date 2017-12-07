"""
Calculating the destination folder for a file.

.. moduleauthor:: Jaisen Mathai <jaisen@jmathai.com>
.. refactored and enhanced by Tony Whitley
"""
from __future__ import print_function
from builtins import object

import os
import re
import time

from elodie import geolocation
from elodie import log
from elodie.config import load_config
#from elodie.filesystem import FileSystem

# +++ the extended folder_path handler
from elodie.destination_path_config import Destination_path_pattern, Destination_actual_path
from elodie import constants

config_file = '%s/config.ini' % constants.application_directory
# --- the extended folder_path handler

class DestinationFolder(object):
    """A class for calculating the destination folder for a file."""

    def __init__(self):
        # The default folder path is along the lines of 2015-01-Jan/Chicago
        self.default_folder_path_definition = {
            'date': '%Y-%m-%b',
            'location': '%city',
            'full_path': '%date/%album|%location|"{}"'.format(
                            geolocation.__DEFAULT_LOCATION__
                         ),
        }
        self.cached_folder_path_definition = None
        self.default_parts = ['album', 'city', 'state', 'country']


    def _parseFallbacks(self, dict, mask):
        """ Given %a|%b|"default" and a dict which may contain a or b
            return [a, value of a], [b, value of b] or ['', "default"]
        """
        for p in mask.split('|'):
            if p[0] == '%':
               if p[1:] in dict:
                   return [p[1:], dict[p[1:]]]
            if p[0] == '"':   # "default"
                return ['', p]
        return []

    def get_folder_path_definition(self):
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
        if self.cached_folder_path_definition is not None:
            return self.cached_folder_path_definition

        config = load_config()

        # If Directory is in the config we assume full_path and its
        #  corresponding values (date, location) are also present
        config_directory = self.default_folder_path_definition
        if('Directory' in config):
            config_directory = config['Directory']

        # Find all subpatterns of full_path that map to directories.
        #  I.e. %foo/%bar => ['foo', 'bar']
        #  I.e. %foo/%bar|%example|"something" => ['foo', 'bar|example|"something"']
        path_parts = re.findall(
                         '(\%[^/]+)',
                         config_directory['full_path']
                     )

        if not path_parts or len(path_parts) == 0:
            return self.default_folder_path_definition

        self.cached_folder_path_definition = []
        for part in path_parts:
            part = part.replace('%', '')
            if part in config_directory:
                self.cached_folder_path_definition.append(
                    [(part, config_directory[part])]
                )
            elif part in self.default_parts:
                self.cached_folder_path_definition.append(
                    [(part, '')]
                )
            else:
                #""" original
                this_part = []
                for p in part.split('|'):
                    this_part.append(
                        (p, config_directory[p] if p in config_directory else '')
                    )
                """ New way breaks old tests
                this_part = self._parseFallbacks(config_directory, part)
                """

                self.cached_folder_path_definition.append(this_part)

        return self.cached_folder_path_definition

    def get_folder_path(self, metadata, path_parts=None):
        """Given a media's metadata this function returns the folder path as a string.

        :param metadata dict: Metadata dictionary.
        :optional param path_parts list of tuples: Pre-defined path definition (for unit test)
        :returns: str
        """

        # Stitch in the extended folder_path handler
        config = Destination_path_pattern()
        config_ini = os.path.join(os.getcwd(), 'elodie', 'tests', 'files', 'config_extended_1.ini')
        config.read_config_file(config_file)
        raw_full_path = config.get_raw_full_path()
        if raw_full_path != '':
            fpconfig = Destination_actual_path(raw_full_path, '') # Don't need the filepath as we'll fake the metadata
            fpconfig._set_metadata(metadata)
            full_path = fpconfig.get_full_path()
            return full_path
        # else extended folder_path handler is not specified in config.ini


        if not path_parts:
            path_parts = self.get_folder_path_definition()
        path = []
        for path_part in path_parts:
            # We support fallback values so that
            #  'album|city|"Unknown Location"
            #  %album|%city|"Unknown Location" results in
            #  My Album - when an album exists
            #  Sunnyvale - when no album exists but a city exists
            #  Unknown Location - when neither an album nor location exist
            for this_part in path_part:
                part, mask = this_part
                if part in ('date', 'day', 'month', 'year'):
                    path.append(
                        time.strftime(mask, metadata['date_taken'])
                    )
                    break
                elif part in ('location', 'hamlet', 'village', 'town', 'city', 'state', 'country'):
                    place_name = geolocation.place_name(
                        metadata['latitude'],
                        metadata['longitude']
                    )

                    # TBD _x = self._parseFallbacks(metadata, mask)
                    location_parts = re.findall('(%[^%]+)', mask)
                    parsed_folder_name = self.parse_mask_for_location(
                        mask,
                        location_parts,
                        place_name,
                    )
                    path.append(parsed_folder_name)
                    break
                elif part in ('album', 'camera_make', 'camera_model'):
                    if metadata[part]:
                        path.append(metadata[part])
                        break
                elif part.startswith('"') and part.endswith('"'):
                    path.append(part[1:-1])

        return os.path.join(*path)

    def parse_mask_for_location(self, mask, location_parts, place_name):
        """Takes a mask for a location and interpolates the actual place names.

        Given these parameters here are the outputs.

        mask=%city
        location_parts=[('%city','%city','city')]
        place_name={'city': u'Sunnyvale'}
        output=Sunnyvale

        mask=%city-%state
        location_parts=[('%city-','%city','city'), ('%state','%state','state')]
        place_name={'city': u'Sunnyvale', 'state': u'California'}
        output=Sunnyvale-California

        mask=%country
        location_parts=[('%country','%country','country')]
        place_name={'default': u'Sunnyvale', 'city': u'Sunnyvale'}
        output=Sunnyvale


        :param str mask: The location mask in the form of %city-%state, etc
        :param list location_parts: A list of tuples in the form of
            [('%city-', '%city', 'city'), ('%state', '%state', 'state')]
        :param dict place_name: A dictionary of place keywords and names like
            {'default': u'California', 'state': u'California'}
        :returns: str
        """
        found = False
        folder_name = mask
        for loc_part in location_parts:
            # We assume the search returns a tuple of length 2.
            # If not then it's a bad mask in config.ini.
            # loc_part = '%country-random'
            # component_full = '%country-random'
            # component = '%country'
            # key = 'country
            component_full, component, key = re.search(
                '((%([a-z]+))[^%]*)',
                loc_part
            ).groups()

            if(key in place_name):
                found = True
                replace_target = component
                replace_with = place_name[key]
            else:
                replace_target = component_full
                replace_with = ''

            folder_name = folder_name.replace(
                replace_target,
                replace_with,
            )

        if(not found and folder_name == ''):
            folder_name = place_name['default']

        # If there are | in the result, take the left side (first option)
        folder_name = folder_name.split('|')[0]
        # Normalise any mixed path separators
        folder_name = os.path.normpath(folder_name)

        return folder_name

