from __future__ import absolute_import
# Project imports
import mock
import os
import sys
import time

from nose.plugins.attrib import attr

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

import elodie.destination_folder

from elodie.destination_path_config import DestinationPath

config_string1 = """
[MapQuest]
key=your-api-key-goes-here

[Directory]
# Handled by original code, ignored by these tests

[Folder]
month=%B
year=%Y
full_path=${year}/${month}
"""
config_string1_full_path = '%Y/%B'

config_string2 = """
[Folder]
month = %B
year = %Y
location = %city|%county|%village
full_path = ${location}/${year}/${month}
"""
config_string2_full_path = '%city|%county|%village/%Y/%B'

metadata_no_GPS =   {
   "date_taken": time.strptime("2017-12-07 12:42:34", "%Y-%m-%d %H:%M:%S")
  }

metadata =   {
   "city": "Carlisle",
   "country": "UK",
   "county": "Cumbria",
   "default": "Carlisle",
   "state": "England",
   "date_taken": time.strptime("2017-12-07 12:42:34", "%Y-%m-%d %H:%M:%S"),
   "lat": 54.9286804166667,
   "long": -2.94800427777778,
  }

@attr('NewPathTest')
def test_set_config_from_text():
    config = DestinationPath()
    config._set_config(config_string1)
    conf = config._get_raw_full_path()
    assert conf == config_string1_full_path, conf

    config._set_config(config_string2)
    conf = config._get_raw_full_path()
    assert conf == config_string2_full_path, conf

@attr('NewPathTest')
def test_set_config_read_ini_file():
    config = DestinationPath()
    config_ini = os.path.join(os.getcwd(), 'elodie', 'tests', 'files', 'config_extended_1.ini')
    config.read_config_file(config_ini)
    conf = config._get_raw_full_path()
    assert conf == '%Y/%B', conf

@attr('NewPathTest')
def test_set_config_from_noFolder():
    config_string = """
[MapQuest]
key=your-api-key-goes-here

[Directory]
# Handled by original code, ignored by these tests
"""
    config = DestinationPath()
    config._set_config(config_string)
    conf = config._get_raw_full_path()
    assert conf == '', conf

@attr('NewPathTest')
def test_set_config_from_noFull_path():
    config_string = """
[MapQuest]
key=your-api-key-goes-here

[Directory]
# Handled by original code, ignored by these tests

[Folder]
time = %B
"""
    config = DestinationPath()
    config._set_config(config_string)
    conf = config._get_raw_full_path()
    assert conf == '', conf

@attr('NewPathTest')
def test_get_full_path():
    config_str = """
[Folder]
month = %B
year = %Y
location = %country/%city
full_path = ${location}/${year}/${month}
"""
    config = DestinationPath()
    config._set_config(config_str)
    full_path = config.get_full_path(metadata)
    assert full_path == 'UK/Carlisle/2017/December', full_path

@attr('NewPathTest')
def test_get_full_path_UNKNOWN_LOCATION():
    config_str = """
[Folder]
month = %B
year = %Y
location = %country/%village
full_path = ${location}/${year}/${month}
"""
    config = DestinationPath()
    config._set_config(config_str)
    full_path = config.get_full_path(metadata)
    assert full_path == 'UK/UNKNOWN LOCATION/2017/December', full_path

@attr('NewPathTest')
def test_get_full_path_TEXT():
    config_str = """
[Folder]
month = %B
year = %Y
location = %country/%city
full_path = ${location}/%"TEXT"/${year}/${month}
"""
    config = DestinationPath()
    config._set_config(config_str)
    full_path = config.get_full_path(metadata)
    assert full_path == 'UK/Carlisle/TEXT/2017/December', full_path


@attr('NewPathTest')
def test_get_full_path_fallback():
    # LHS of fallback fails - there is no village
    config_str = """
[Folder]
month = %B
year = %Y
full_path = %village/%city/${year}/${month} | %country/%county/${year}/${month}
"""
    config = DestinationPath()
    config._set_config(config_str)
    full_path = config.get_full_path(metadata)
    assert full_path == 'UK/Cumbria/2017/December', '"%s"' % full_path

@attr('NewPathTest')
def test_get_full_path_fallback2():
    # RHS of fallback fails - there is no village
    config_str = """
[Folder]
month = %B
year = %Y
full_path = %country/%city/${year}/${month} | %village/%city/${year}/${month}
"""
    config = DestinationPath()
    config._set_config(config_str)
    full_path = config.get_full_path(metadata)
    assert full_path == 'UK/Carlisle/2017/December', '"%s"' % full_path

@attr('NewPathTest')
def test_get_full_path_fallback3():
    # RHS of fallback fails - there is no village
    # Using user-defined variables for locations
    config_str = """
[Folder]
month = %B
year = %Y
location1 = %country/%city
location2 = %village/%city
full_path = ${location1}/${year}/${month} | ${location2}/${year}/${month}
"""
    config = DestinationPath()
    config._set_config(config_str)
    full_path = config.get_full_path(metadata)
    assert full_path == 'UK/Carlisle/2017/December', '"%s"' % full_path

@attr('NewPathTest')
def test_get_full_path_fallback_noGPS():
    # No GPS so location component comes out as NO GPS
    # Using user-defined variables for locations
    config_str = """
[Folder]
month = %B
year = %Y
location1 = %country/%city
location2 = %village/%city
# If neither of the above work, fall back on just country
# If that's not available we will get NO GPS
location3 = %country
full_path = ${location1}/${year}/${month} | ${location2}/${year}/${month} | ${location3}/${year}/${month}
"""
    config = DestinationPath()
    config._set_config(config_str)
    full_path = config.get_full_path(metadata_no_GPS)
    assert full_path == 'NO GPS/2017/December', '"%s"' % full_path


@attr('NewPathTest')
def test_get_full_path_fallback_noLocation():
    # GPS but no location component comes out as UNKNOWN LOCATION
    # Using user-defined variables for locations
    config_str = """
[Folder]
month = %B
year = %Y
location1 = %country/%hamlet
location2 = %village/%city
# If neither of the above work, fall back on just country
# If that's not available we will get UNKNOWN LOCATION
location3 = %village
full_path = ${location1}/${year}/${month} | ${location2}/${year}/${month} | ${location3}/${year}/${month}
"""
    config = DestinationPath()
    config._set_config(config_str)
    full_path = config.get_full_path(metadata)
    assert full_path == 'UNKNOWN LOCATION/2017/December', '"%s"' % full_path
