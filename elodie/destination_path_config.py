from configparser import ConfigParser, ExtendedInterpolation
import re
import time

"""
More flexible, simpler way of calculating the destination path for a file.

Design:
Folder structure BNF

<full_path> ::= "full_path=" <term>
<rule>      ::= <term-name> "=" <term>
<term>      ::= <atoms> | <conditional term>
<conditional term> ::= <atoms> <'|'> <atoms> | <conditional term> <'|'> <atoms>
<atoms>     ::= <atom> | <atoms> <atom>
<atom>      ::= <time format> | <photo data> | <text> | "%" <term-name>
<text>      ::= <'-'> | <'/'> | "%" <"text string">

<time format> ::=  <any standard Python time directive, e.g. %Y for 2017>

<photo data> ::= <photo location> | <photo camera information>

<photo location> ::= <'%country'> | <'%county'> | <'%city'> | <'%town'> | <'%village'>
<photo camera information> ::= <'%camera_make'> | <'%camera_model'> |

Values may be "UNKNOWN LOCATION" (GPS long/lat didn't give the requested
location element) or "NO GPS" (GPS information not present in the photo)
or "NO CAMERA INFO".
If those values are returned to a <conditional term> then processing skips to
the <term> after the |

"""

class Destination_path_pattern():
    """
    Get the 'full_path' definition from the [Folder] section of ~/config.ini
    """
    def __init__(self):
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        # Extended interpolation example:
        # [Folder]
        # month= %B
        # year= %Y
        # full_path= ${year}/${month}
        self.raw_full_path = None # as parsed from config file ready to
                                  # substitute <atoms>
    def read_config_file(self, config_filepath):
        """ Read the ~/config.ini file. """
        self.config.read(config_filepath)
        self._parse_raw_full_path(self.config)
    def _set_config(self, config_file_str):
        """ Used for unit tests, bypassing the actual config.ini file. """
        self.config.read_string(config_file_str)
        self._parse_raw_full_path(self.config)
    def _parse_raw_full_path(self, raw_config):
        """
        Parse raw_full_path from the [Folder] section
        BasicInterpolation does that for us
        """
        try:
            self.raw_full_path = raw_config['Folder']
        except: # No [Folder]
            self.raw_full_path = ''
            return
        try:
            self.raw_full_path = raw_config['Folder']['full_path']
        except: # No full_path = ...
            self.raw_full_path = ''
    def get_raw_full_path(self):
        """ The final result """
        return self.raw_full_path

class Destination_actual_path():
    """
    Given the 'full_path' definition from the [Folder] section of ~/config.ini
    apply it to a file
    """
    def __init__(self, raw_full_path, filepath):
        self.raw_full_path = raw_full_path
        self.filepath = filepath
        self.metadata = {}
    def get_metadata_from_file(self):
        # get the metadata for the file
        pass #tbd
    def _set_metadata(self, metadata):
        """ unit test """
        self.metadata = metadata
    def __parse_full_path(self, raw_full_path):
        """
        Substitute atoms by items from metadata.
        Then evaluate any <conditional terms> and return the first one
        that has a value (i.e. has no UNKNOWNs)
        """
        # Extract atoms
        atoms = re.findall(
            '\%([^/|-]+)',      # separators are / | -
            raw_full_path)
        atom_dict = {}
        for atom in atoms:
            if atom in ('location', 'hamlet', 'village', 'town', 'city', 'state', 'country', 'county'):
                if atom in self.metadata:
                    atom_dict[atom] = self.metadata[atom]
                else:
                    if 'lat' in self.metadata:  # We have latitude but don't have this location type
                        atom_dict[atom] = '€UNKNOWN LOCATION'   # € is a "magic char" for fallback processing
                    else:
                        atom_dict[atom] = '€NO GPS'   # € is a "magic char" for fallback processing
            elif atom in ('camera_make', 'camera_model'):
                if atom in self.metadata:
                    atom_dict[atom] = self.metadata[atom]
                else:
                    atom_dict[atom] = '€NO CAMERA INFO'
            elif atom.startswith('"'):
                atom_dict[atom] = atom.strip('"') # Pass strings straight through unchanged
            else:
                try:
                    atom_dict[atom] = time.strftime(r'%'+atom, self.metadata['date_taken'])
                except:
                    assert True, ('Unknown time format "%%%s"' % atom)
        for atom in atoms:
            #_fmt = '%%%s' % atom
            raw_full_path = re.sub('%%%s' % atom, atom_dict[atom], raw_full_path)

        # Now deal with fallbacks
        # Split the path at each |
        fallbacks = raw_full_path.split('|')
        for i in range(0, len(fallbacks)-1):    # -1 so as not to strip the final fallback
            fallback = fallbacks[i]
            if '€' in fallback:
                # strip the (LHS) fallback and its separator
                raw_full_path = raw_full_path[len(fallback)+1:]
            else: # this one is OK, strip the rest
                raw_full_path = raw_full_path[:len(fallback)]
                break
        raw_full_path = re.sub('€', '', raw_full_path)

        return raw_full_path.strip()
    def get_full_path(self):
        _return = self.__parse_full_path(self.raw_full_path)
        return _return

