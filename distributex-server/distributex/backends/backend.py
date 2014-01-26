from zope import interface

import time

class ICacheBackend(interface.Interface):
    def get_lock(self, pool, host):
        """
        Try to get a lock on a specific pool
        """

    def release_lock(self, pool, host):
        """
        Release the lock on a pool
        """

    def add_pool(self, pool, expire):
        """
        Create and configure a lock pool
        """
