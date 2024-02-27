from unittest import TestCase

from constants import LOCAL_DIR
from profiles.data_cache import DataCache


class TestCache(DataCache):
    cache_location = LOCAL_DIR.joinpath("test_cache.json")

class TestDataCache(TestCase):

    def test_cache(self):
        cache = TestCache()
        self.assertRaises(KeyError, lambda: cache.get("key"))
        cache.update("key", "value")
        self.assertEqual("value", cache.get("key"))

        # Present in other cache
        cache2 = TestCache()
        self.assertEqual("value", cache.get("key"))
        cache2.purge()
        self.assertRaises(KeyError, lambda: cache2.get("key"))
