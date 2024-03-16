"""
Picle Cache Object
==================

Picle Cache is a dictionary like object, but capable 
to sync in-memory content with a file for persistent storage.

Implements keys expiration capability using provided ttl value.

File sync is multiprocessing and thread safe.

Trying to retrieve key value that has TTL expired will raise 
a ``KeyError``.

Only JSON serializable values supported.
"""
import os
import json
import time


class Cache(dict):
    """Picle Cache object based on dict but with added TTL and file presistence"""

    def __init__(self, filename, ttl=3600, *args, **kwargs):
        self.ttl = ttl
        self.metadata = {}  # e.g. {key_name: {"age": 0}}

        # process file details
        self.filename = filename
        self.filedir, self.data_filename = os.path.split(filename)
        self.metafile = os.path.join(self.filedir, f"{self.data_filename}.meta")
        self.lockfile = os.path.join(self.filedir, f"{self.data_filename}.lock")

        self.check_filedir()
        self.load()
        self.update(*args, **kwargs)

    def check_filedir(self):
        """Check and create directory for cache file"""
        if not os.path.exists(self.filedir):
            os.makedirs(self.filedir, exist_ok=True)

    def load(self):
        """Function to load cached data"""
        # load metadata content
        if os.path.exists(self.metafile):
            with open(self.metafile, mode="r+", encoding="utf-8") as f:
                self.metadata = json.loads(f.read())
        else:
            with open(self.metafile, mode="w", encoding="utf-8") as f:
                f.write(json.dumps({}))

        # load data content
        if os.path.exists(self.filename):
            with open(self.filename, mode="r", encoding="utf-8") as f:
                self.update(json.loads(f.read()))
        else:
            with open(self.filename, mode="w", encoding="utf-8") as f:
                f.write(json.dumps({}))

    def sync(self, timeout=10):
        """Function to dump in-memory dictionary content to a file"""
        try:
            # keep sleeping until lockfile is gone
            elapsed = 0
            while timeout > elapsed:
                # create lockfile to be multiprocess safe
                if not os.path.exists(self.lockfile):
                    with open(self.lockfile, mode="w", encoding="utf-8") as f:
                        f.write(f"LOCKED {time.ctime()}")
                    break
                elapsed += 0.1
                time.sleep(0.1)
            else:
                raise TimeoutError(
                    f"File '{self.filename}' is locked, "
                    f"{timeout}s wait timeout expired."
                )
            # check if any of the keys have TTL expired
            for k in list(self.metadata.keys()):
                if self.metadata[k]["ttl"] > time.time() - self.metadata[k]["age"]:
                    self.pop(k)
                    self.metadata.pop(k)
            # save metadata
            with open(self.metafile, mode="w", encoding="utf-8") as f:
                f.write(json.dumps(self.metadata))
            # dump in-memory data into file
            with open(self.filename, mode="w", encoding="utf-8") as f:
                f.write(json.dumps({k: v for k, v in self.items()}))
        finally:
            # remove lock file
            try:
                os.remove(self.lockfile)
            except FileNotFoundError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.sync()

    def __getitem__(self, key):
        # check if key exists
        if key not in self:
            raise KeyError()
        # check key TTL
        if self.metadata[key]["ttl"] > time.time() - self.metadata[key]["age"]:
            return dict.__getitem__(self, key)
        # TTL expired, remove key and raise KeyError
        else:
            self.pop(key)
            self.metadata.pop(key)
            raise KeyError()

    def __setitem__(self, key, val) -> None:
        self.metadata[key] = {"age": time.time(), "ttl": self.ttl}
        dict.__setitem__(self, key, val)

    def update(self, *args, **kwargs) -> None:
        for k, v in dict(*args, **kwargs).items():
            self[k] = v

    def show_ttl(self) -> dict:
        """Returns dictionary of cached key time-to-live left in seconds"""
        return {
            k: round(v["ttl"] - (time.time() - v["age"]), 3)
            for k, v in self.metadata.items()
        }
