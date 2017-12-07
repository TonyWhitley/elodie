from __future__ import absolute_import
# Project imports
import mock
import os
import re
import shutil
import sys
from tempfile import gettempdir

from nose.plugins.attrib import attr

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from . import helper
from elodie.config import load_config
from elodie.destination_folder import DestinationFolder
from elodie.media.photo import Photo
from elodie.localstorage import mock_location_db

os.environ['TZ'] = 'GMT'


def test_get_folder_path_plain():
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('plain.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())

    assert path == os.path.join('2015-12-Dec','Unknown Location'), path

def test_get_folder_path_with_title():
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('with-title.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())

    assert path == os.path.join('2015-12-Dec','Unknown Location'), path

def test_get_folder_path_with_location():
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('with-location.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())

    assert path == os.path.join('2015-12-Dec','Sunnyvale'), path

@mock.patch('elodie.config.config_file', '%s/config.ini-original-with-camera-make-and-model' % gettempdir())
def test_get_folder_path_with_camera_make_and_model():
    with open('%s/config.ini-original-with-camera-make-and-model' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
full_path=%camera_make/%camera_model
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('plain.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('Canon', 'Canon EOS REBEL T2i'), path

@mock.patch('elodie.config.config_file', '%s/config.ini-original-with-camera-make-and-model-fallback' % gettempdir())
def test_get_folder_path_with_camera_make_and_model_fallback():
    with open('%s/config.ini-original-with-camera-make-and-model-fallback' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
full_path=%camera_make|"nomake"/%camera_model|"nomodel"
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('no-exif.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('nomake', 'nomodel'), path

@mock.patch('elodie.config.config_file', '%s/config.ini-int-in-component-path' % gettempdir())
def test_get_folder_path_with_int_in_config_component():
    # gh-239
    with open('%s/config.ini-int-in-component-path' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
date=%Y
full_path=%date
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('plain.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015'), path

def test_get_folder_path_with_int_in_source_path():
    # gh-239
    destination_folder = DestinationFolder()
    temporary_folder, folder = helper.create_working_folder('int')

    origin = os.path.join(folder,'plain.jpg')
    shutil.copyfile(helper.get_file('plain.jpg'), origin)

    media = Photo(origin)
    path = destination_folder.get_folder_path(media.get_metadata())

    assert path == os.path.join('2015-12-Dec','Unknown Location'), path

@mock.patch('elodie.config.config_file', '%s/config.ini-original-default-unknown-location' % gettempdir())
def test_get_folder_path_with_original_default_unknown_location():
    with open('%s/config.ini-original-default-with-unknown-location' % gettempdir(), 'w') as f:
        f.write('')
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('plain.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015-12-Dec','Unknown Location'), path

@mock.patch('elodie.config.config_file', '%s/config.ini-custom-path' % gettempdir())
def test_get_folder_path_with_custom_path():
    with open('%s/config.ini-custom-path' % gettempdir(), 'w') as f:
        f.write("""
[MapQuest]
key=czjNKTtFjLydLteUBwdgKAIC8OAbGLUx

[Directory]
date=%Y-%m-%d
location=%country-%state-%city
full_path=%date/%location
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('with-location.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015-12-05','United States of America-California-Sunnyvale'), path

@mock.patch('elodie.config.config_file', '%s/config.ini-fallback' % gettempdir())
def test_get_folder_path_with_fallback_folder():
    with open('%s/config.ini-fallback' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
year=%Y
month=%m
full_path=%year/%month/%album|%"No Album Fool"/%month
        """)
#full_path=%year/%album|"No Album"
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('plain.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015','12','No Album Fool','12'), path

@mock.patch('elodie.config.config_file', '%s/config.ini-location-date' % gettempdir())
def test_get_folder_path_with_with_more_than_two_levels():
    with open('%s/config.ini-location-date' % gettempdir(), 'w') as f:
        f.write("""
[MapQuest]
key=czjNKTtFjLydLteUBwdgKAIC8OAbGLUx

[Directory]
year=%Y
month=%m
location=%city, %state
full_path=%year/%month/%location
        """)

    if hasattr(load_config, 'config'):
        del load_config.config

    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('with-location.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015','12','Sunnyvale, California'), path

@mock.patch('elodie.config.config_file', '%s/config.ini-location-date' % gettempdir())
def test_get_folder_path_with_with_only_one_level():
    with open('%s/config.ini-location-date' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
year=%Y
full_path=%year
        """)

    if hasattr(load_config, 'config'):
        del load_config.config

    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('plain.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == os.path.join('2015'), path

def test_get_folder_path_with_location_and_title():
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('with-location-and-title.jpg'))
    path = destination_folder.get_folder_path(media.get_metadata())

    assert path == os.path.join('2015-12-Dec','Sunnyvale'), path

def test_parse_folder_name_default():
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    place_name = {'default': u'California', 'country': u'United States of America', 'state': u'California', 'city': u'Sunnyvale'}
    mask = '%city'
    location_parts = re.findall('(%[^%]+)', mask)
    path = destination_folder.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'Sunnyvale', path

def test_parse_folder_name_multiple():
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    place_name = {'default': u'California', 'country': u'United States of America', 'state': u'California', 'city': u'Sunnyvale'}
    mask = '%city-%state-%country'
    location_parts = re.findall('(%[^%]+)', mask)
    path = destination_folder.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'Sunnyvale-California-United States of America', path

def test_parse_folder_name_static_chars():
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    place_name = {'default': u'California', 'country': u'United States of America', 'state': u'California', 'city': u'Sunnyvale'}
    mask = '%city-is-the-city'
    location_parts = re.findall('(%[^%]+)', mask)
    path = destination_folder.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'Sunnyvale-is-the-city', path

def test_parse_folder_name_key_not_found():
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    place_name = {'default': u'California', 'country': u'United States of America', 'state': u'California'}
    mask = '%city'
    location_parts = re.findall('(%[^%]+)', mask)
    path = destination_folder.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'California', path

def test_parse_folder_name_key_not_found_with_static_chars():
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    place_name = {'default': u'California', 'country': u'United States of America', 'state': u'California'}
    mask = '%city-is-not-found'
    location_parts = re.findall('(%[^%]+)', mask)
    path = destination_folder.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'California', path

def test_parse_folder_name_multiple_keys_not_found():
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    place_name = {'default': u'United States of America', 'country': u'United States of America'}
    mask = '%city-%state'
    location_parts = re.findall('(%[^%]+)', mask)
    path = destination_folder.parse_mask_for_location(mask, location_parts, place_name)
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path == 'United States of America', path

@mock.patch('elodie.config.config_file', '%s/config.ini-does-not-exist' % gettempdir())
def test_get_folder_path_definition_default():
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    path_definition = destination_folder.get_folder_path_definition()
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == [[('date', '%Y-%m-%b')], [('album', ''), ('location', '%city'), ('"Unknown Location"', '')]], path_definition

@mock.patch('elodie.config.config_file', '%s/config.ini-date-location' % gettempdir())
def test_get_folder_path_definition_date_location():
    with open('%s/config.ini-date-location' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
date=%Y-%m-%d
location=%country
full_path=%date/%location
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    path_definition = destination_folder.get_folder_path_definition()
    expected = [
        [('date', '%Y-%m-%d')], [('location', '%country')]
    ]
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == expected, path_definition

@mock.patch('elodie.config.config_file', '%s/config.ini-location-date' % gettempdir())
def test_get_folder_path_definition_location_date():
    with open('%s/config.ini-location-date' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
date=%Y-%m-%d
location=%country
full_path=%location/%date
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    path_definition = destination_folder.get_folder_path_definition()
    expected = [
        [('location', '%country')], [('date', '%Y-%m-%d')]
    ]
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == expected, path_definition

@mock.patch('elodie.config.config_file', '%s/config.ini-cached' % gettempdir())
def test_get_folder_path_definition_cached():
    with open('%s/config.ini-cached' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
date=%Y-%m-%d
location=%country
full_path=%date/%location
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    path_definition = destination_folder.get_folder_path_definition()
    expected = [
        [('date', '%Y-%m-%d')], [('location', '%country')]
    ]

    assert path_definition == expected, path_definition

    with open('%s/config.ini-cached' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
date=%uncached
location=%uncached
full_path=%date/%location
        """)
    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    path_definition = destination_folder.get_folder_path_definition()
    expected = [
        [('date', '%Y-%m-%d')], [('location', '%country')]
    ]
    if hasattr(load_config, 'config'):
        del load_config.config

@mock.patch('elodie.config.config_file', '%s/config.ini-location-date' % gettempdir())
def test_get_folder_path_definition_with_more_than_two_levels():
    with open('%s/config.ini-location-date' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
year=%Y
month=%m
day=%d
full_path=%year/%month/%day
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    path_definition = destination_folder.get_folder_path_definition()
    expected = [
        [('year', '%Y')], [('month', '%m')], [('day', '%d')]
    ]
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == expected, path_definition

@mock.patch('elodie.config.config_file', '%s/config.ini-location-date' % gettempdir())
def test_get_folder_path_definition_with_only_one_level():
    with open('%s/config.ini-location-date' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
year=%Y
full_path=%year
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    path_definition = destination_folder.get_folder_path_definition()
    expected = [
        [('year', '%Y')]
    ]
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == expected, path_definition

@mock.patch('elodie.config.config_file', '%s/config.ini-multi-level-custom' % gettempdir())
def test_get_folder_path_definition_multi_level_custom():
    with open('%s/config.ini-multi-level-custom' % gettempdir(), 'w') as f:
        f.write("""
[Directory]
year=%Y
month=%M
full_path=%year/%album|%month|%"foo"/%month
        """)

    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    path_definition = destination_folder.get_folder_path_definition()

    expected = [[('year', '%Y')], [('album', ''), ('month', '%M'), ('"foo"', '')], [('month', '%M')]]
    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == expected, path_definition

mock_location_db_json_txt = """
[
 {
  "lat": 54.9286804166667,
  "long": -2.94800427777778,
  "name": {
   "city": "Carlisle",
   "country": "UK",
   "county": "Cumbria",
   "default": "Carlisle",
   "state": "England"
  }
 },
 {
  "lat": 55.4874000277778,
  "long": -3.290884,
  "name": {
   "country": "UK",
   "county": "Scottish Borders",
   "default": "Meggethead",
   "hamlet": "Meggethead",
   "state": "Scotland"
  }
 },
 {
  "lat": 55.2033538611111,
  "long": -4.55464691666667,
  "name": {
   "country": "UK",
   "county": "South Ayrshire",
   "default": "South Ayrshire",
   "state": "Scotland"
  }
 },
 {
  "lat": 54.5187110833333,
  "long": -1.50435136111111,
  "name": {
   "country": "UK",
   "county": "Darlington",
   "default": "Great Burdon",
   "hamlet": "Great Burdon",
   "state": "England"
  }
 },
 {
  "lat": 55.92352675,
  "long": -5.15257691666667,
  "name": {
   "country": "UK",
   "default": "Colintraive",
   "state": "Scotland",
   "village": "Colintraive"
  }
 }
]
"""
multi_level_location_definition_CCCV = [
    [
        ('location', '%country/%city|%county|%village')
    ],
    [
        ('year', '%Y')
    ],
    [
        ('month', '%B')
    ]
]

multi_level_location_config_json = """
[Directory]
location=%country/%city|%county|%village
# If %country/%city not available, fall back on %country/%county
#   If %country/%county not available either, fall back on %country/%village
year=%Y
month=%B
full_path=%location/%year/%month
# -> France/Le Mans/2016
"""

@attr('universalMultiLevel')  # Revised code to allow multi-level anywhere
@mock.patch('elodie.config.config_file', '%s/config.ini-multi_level_location' % gettempdir())
def test_get_folder_path_definition_multi_level_location_definition():
    with open('%s/config.ini-multi_level_location' % gettempdir(), 'w') as f:
        f.write(multi_level_location_config_json)

    mock_location_db(mock_location_db_json_txt)

    if hasattr(load_config, 'config'):
        del load_config.config
    destination_folder = DestinationFolder()
    path_definition = destination_folder.get_folder_path_definition()

    if hasattr(load_config, 'config'):
        del load_config.config

    assert path_definition == multi_level_location_definition_CCCV, path_definition

@attr('universalMultiLevel')  # Revised code to allow multi-level anywhere
def test_get_folder_path_definition_multi_level_location_decode_unknown():
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('plain.jpg'))
    _metadata = media.get_metadata()
    # use multi_level_location_expected, no need to recalculate
    path = destination_folder.get_folder_path(_metadata, path_parts=multi_level_location_definition_CCCV)

    assert path == os.path.join('Unknown Location', '2015', 'December'), path

@attr('universalMultiLevel')  # Revised code to allow multi-level anywhere
def test_get_folder_path_definition_multi_level_location_decode_known_city():
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('with-location.jpg'))
    _metadata = media.get_metadata()
    _metadata['latitude'] = 54.9286804166667
    _metadata['longitude'] = -2.94800427777778  # see mock_location_db_json_txt
    # use multi_level_location_expected, no need to recalculate
    path = destination_folder.get_folder_path(_metadata, path_parts=multi_level_location_definition_CCCV)

    assert path == os.path.join('UK', 'Carlisle', '2015', 'December'), path


@attr('universalMultiLevel')  # Revised code to allow multi-level anywhere
def test_get_folder_path_definition_multi_level_location_decode_known_county():
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('with-location.jpg'))
    _metadata = media.get_metadata()
    _metadata['latitude'] = 55.4874000277778
    _metadata['longitude'] = -3.290884
    # use multi_level_location_expected, no need to recalculate
    path = destination_folder.get_folder_path(_metadata, path_parts=multi_level_location_definition_CCCV)

    assert path == os.path.join('UK', 'Scottish Borders', '2015', 'December'), path

@attr('universalMultiLevel')  # Revised code to allow multi-level anywhere
def test_get_folder_path_definition_multi_level_location_decode_known_village():
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('with-location.jpg'))
    _metadata = media.get_metadata()
    _metadata['latitude'] = 55.92352675
    _metadata['longitude'] = -5.15257691666667  # see mock_location_db_json_txt
    # use multi_level_location_expected, no need to recalculate
    path = destination_folder.get_folder_path(_metadata, path_parts=multi_level_location_definition_CCCV)

    assert path == os.path.join('UK', 'Colintraive', '2015', 'December'), path

multi_level_location_definition_SCCV = [
    [
        ('location', '%state/%city|%county|%village')
    ],
    [
        ('year', '%Y')
    ],
    [
        ('month', '%B')
    ]
]

@attr('universalMultiLevel')  # Revised code to allow multi-level anywhere
def test_get_folder_path_definition_multi_level_location_decode_state_known_village():
    destination_folder = DestinationFolder()
    media = Photo(helper.get_file('with-location.jpg'))
    _metadata = media.get_metadata()
    _metadata['latitude'] = 55.92352675
    _metadata['longitude'] = -5.15257691666667  # see mock_location_db_json_txt
    # use multi_level_location_expected, no need to recalculate
    path = destination_folder.get_folder_path(_metadata, path_parts=multi_level_location_definition_SCCV)

    assert path == os.path.join('Scotland', 'Colintraive', '2015', 'December'), path

