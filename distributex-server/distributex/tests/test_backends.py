from twisted.trial import unittest

from distributex import service

class DictBackend(unittest.TestCase):
    def setUp(self):
        self.backend = service.InMemoryDictBackend()

    def test_add_pool(self):
        self.backend.add_pool('test1', 3600, [])

        self.assertTrue('test1' in self.backend.resources)

    def test_get_lock(self):
        self.backend.add_pool('test1', 3600, [])
        lock1 = self.backend.get_lock('test1', 'host1')
        lock2 = self.backend.get_lock('test1', 'host2')
        lock3 = self.backend.get_lock('test1', 'host3')

        self.assertTrue(lock1)
        self.assertFalse(lock2)
        self.assertFalse(lock3)

        self.backend.release_lock('test1', 'host1')

    def test_release_lock(self):
        self.backend.add_pool('test1', 3600, [])
        lock1 = self.backend.get_lock('test1', 'host1')
        lock2 = self.backend.get_lock('test1', 'host2')

        self.backend.release_lock('test1', 'host2')
        self.assertFalse(self.backend.get_lock('test1', 'host2'))

        self.backend.release_lock('test1', 'host1')
        self.assertTrue(self.backend.get_lock('test1', 'host2'))

        self.backend.release_lock('test1', 'host2')
