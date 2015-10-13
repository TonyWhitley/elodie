import hashlib
import json
import os

from elodie import constants

class Db(object):
    def __init__(self):
        # verify that the application directory (~/.elodie) exists, else create it
        if not os.path.exists(constants.application_directory):
            os.makedirs(constants.application_directory)

        self.hash_db = {}
        # we need to open in w incase the file doesn't exist
        with open(constants.hash_db, 'rw') as f:
            try:
                self.hash_db = json.load(f)
            except ValueError:
                pass
        
    def add_hash(self, key, value, write=False):
        self.hash_db[key] = value
        if(write == True):
            self.update_hash_db()

    def check_hash(self, key):
        return key in self.hash_db

    def get_hash(self, key):
        if(self.check_hash(key) == True):
            return self.hash_db[key]
        return None

    def update_hash_db(self):
        with open(constants.hash_db, 'w') as f:
            json.dump(self.hash_db, f)

    """
    http://stackoverflow.com/a/3431835/1318758
    """
    def checksum(self, file_path, blocksize=65536):
        hasher = hashlib.sha256()
        with open(file_path, 'r') as f:
            buf = f.read(blocksize)

            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(blocksize)
            return hasher.hexdigest()
        return None