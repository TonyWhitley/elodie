"""Load config file as a singleton."""
from configparser import RawConfigParser
from os import path

from elodie import constants

config_file = '%s/config.ini' % constants.application_directory


def load_config():
    if hasattr(load_config, "config"):
        return load_config.config

    if not path.exists(config_file):
        return {}

    load_config.config = RawConfigParser()
    load_config.config.read(config_file)
    return load_config.config

def mock_config_ini(config_string):
    pass
''' A static variable is used for the config for two reasons
  1) So that mock functions can load them for testing
     (easier than creating temporary config.ini files)
  2) So the files only need to be read once
     (speeds up the testing particularly)
NOT WORKING
__config_ini__ = None

def mock_config_ini(config_string):
    """Fill location_db with data for test purposes """
    global __config_ini__
    _cfg = RawConfigParser()
    __config_ini__ = _cfg.read_string(config_string)

def load_config():
    global __config_ini__

    if __config_ini__ == None:
        load_config.config = RawConfigParser()
        load_config.config.read(config_file)
        __config_ini__ = load_config.config

    if hasattr(load_config, "config"):
        return load_config.config

    if not path.exists(config_file):
        return {}

    return __config_ini__
'''