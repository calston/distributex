from zope import interface
from distributex.backends import backend
import time


class InMemoryDictBackend(object):
    interface.implements(backend.ICacheBackend)
    
    def __init__(self, config):
        self.resources = {}

    def get_lock(self, pool, host):
        if self.resources[pool]['expire']:
            # Expire any stale lock
            locked_for = time.time() - self.resources[pool]['locktime']
            if locked_for > self.resources[pool]['expire']:
                lockby = self.resources[pool]['lockedby']

        lockby = self.resources[pool]['lockedby']
        maxlocks = self.resources[pool]['maxlocks']
        if lockby:
            if host in lockby:
                return True

            if len(lockby) < maxlocks:
                self.resources[pool]['lockedby'].append(host)
                return True
            else:
                return False
        else:
            self.resources[pool]['lockedby'] = [host]
            self.resources[pool]['locktime'] = time.time()
            return True

    def release_lock(self, pool, host):
        if host in self.resources[pool]['lockedby']:
            self.resources[pool]['lockedby'].remove(host)
        
    def add_pool(self, pool, expire, maxlocks=None):
        self.resources[pool] = {
            'expire': expire,
            'lockedby': [],
            'locktime': 0,
            'maxlocks': maxlocks
        }
