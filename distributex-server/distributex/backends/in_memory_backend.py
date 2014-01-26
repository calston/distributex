from zope import interface
from distributex.backends import backend
import time


class InMemoryDictBackend(object):
    interface.implements(backend.ICacheBackend)
    
    def __init__(self, config):
        self.resources = {}

    def get_lock(self, pool, host):
        if self.resources[pool]['lockedby']:
            if self.resources[pool]['lockedby'] == host:
                # You already own this lock.
                return True
            
            if self.resources[pool]['expire']:
                locked_for = time.time() - self.resources[pool]['locktime']
                if locked_for < self.resources[pool]['expire']:
                    # Lock still valid
                    return False
            else:
                return False

        self.resources[pool]['lockedby'] = host
        self.resources[pool]['locktime'] = time.time()
        return True

    def release_lock(self, pool, host):
        if self.resources[pool]['lockedby'] == host:
            self.resources[pool]['lockedby'] = None
        
    def add_pool(self, pool, expire):
        self.resources[pool] = {
            'expire': expire,
            'lockedby': None,
            'locktime': 0
        }
