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
'''
def load_plugin_config():
    config = load_config()

    # If plugins are defined in the config we return them as a list
    # Else we return an empty list
    if 'Plugins' in config and 'plugins' in config['Plugins']:
        return config['Plugins']['plugins'].split(',')

    return []

def load_config_for_plugin(name):
    # Plugins store data using Plugin%PluginName% format.
    key = 'Plugin{}'.format(name)
    config = load_config()

    if key in config:
        return config[key]

    return {}