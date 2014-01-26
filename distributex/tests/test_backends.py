from twisted.trial import unittest
from twisted.internet import defer

from distributex.backends import in_memory_backend, memcached_backend

class DictBackend(unittest.TestCase):
    def setUp(self):
        self.backend = in_memory_backend.InMemoryDictBackend({})

    def test_add_pool(self):
        self.backend.add_pool('test1', 3600)

        self.assertTrue('test1' in self.backend.resources)

    def test_get_lock(self):
        self.backend.add_pool('test1', 3600)
        lock1 = self.backend.get_lock('test1', 'host1')
        lock2 = self.backend.get_lock('test1', 'host2')
        lock3 = self.backend.get_lock('test1', 'host3')

        self.assertTrue(lock1)
        self.assertFalse(lock2)
        self.assertFalse(lock3)

        self.backend.release_lock('test1', 'host1')

    def test_release_lock(self):
        self.backend.add_pool('test1', 3600)
        lock1 = self.backend.get_lock('test1', 'host1')
        lock2 = self.backend.get_lock('test1', 'host2')

        self.backend.release_lock('test1', 'host2')
        self.assertFalse(self.backend.get_lock('test1', 'host2'))

        self.backend.release_lock('test1', 'host1')
        self.assertTrue(self.backend.get_lock('test1', 'host2'))

        self.backend.release_lock('test1', 'host2')

class MemcachedBackend(unittest.TestCase):
    def setUp(self):
        self.backend = memcached_backend.MemcachedBackend({})
    
    @defer.inlineCallbacks
    def tearDown(self):
        yield self.backend.disconnect()

    @defer.inlineCallbacks
    def test_add_pool(self):
        yield self.backend.add_pool('test1', 60)

        e = yield self.backend.get_key('test1', 'expire')

        self.assertEquals(e[1], '60')

    @defer.inlineCallbacks
    def test_get_lock(self):
        yield self.backend.add_pool('test1', 60)

        lock1 = yield self.backend.get_lock('test1', 'host1')
        lock2 = yield self.backend.get_lock('test1', 'host2')

        self.assertTrue(lock1)
        self.assertFalse(lock2)

        yield self.backend.release_lock('test1', 'host1')

    @defer.inlineCallbacks
    def test_release_lock(self):
        yield self.backend.add_pool('test1', 60)
        lock1 = yield self.backend.get_lock('test1', 'host1')

        yield self.backend.release_lock('test1', 'host2')
        lock2 = yield self.backend.get_lock('test1', 'host2')
        self.assertFalse(lock2)

        yield self.backend.release_lock('test1', 'host1')
        lock2 = yield self.backend.get_lock('test1', 'host2')
        self.assertTrue(lock2)

        yield self.backend.release_lock('test1', 'host2')
