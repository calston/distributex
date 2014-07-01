from zope import interface
from distributex.backends import backend
import time


class InMemoryDictBackend(object):
    interface.implements(backend.ICacheBackend)
    
    def __init__(self, config):
        self.resources = {}

    def get_priority(self, pool, host):
        prio = self.resources[pool]['lockprio']
        prio_list = sorted(prio.items(), key=lambda i: i[1])

        return prio_list[0][0] == host

    def get_lock(self, pool, host):
        lockby = self.resources[pool]['lockedby']
        maxlocks = self.resources[pool]['maxlocks']

        if self.resources[pool]['expire']:
            # Expire any stale lock
            locked_for = time.time() - self.resources[pool]['locktime']
            if locked_for > self.resources[pool]['expire']:
                if len(lockby) >= maxlocks:
                    # Remove the oldest lock
                    dropped = self.resources[pool]['lockedby'].pop(0)
                    lockby = self.resources[pool]['lockedby']
                    if dropped in self.resources[pool]['lockprio']:
                        del self.resources[pool]['lockprio'][dropped]

        if lockby:
            if host in lockby:
                # Host has lock already
                return True

            if len(lockby) < maxlocks:
                # Semaphore
                self.resources[pool]['lockedby'].append(host)
            else:
                # Don't return a lock
                if not host in self.resources[pool]['lockprio']:
                    self.resources[pool]['lockprio'][host] = time.time()
                return False

        if self.resources[pool]['lockprio']:
            if not self.get_priority(pool, host):
                # Pass over this lock request, reduce age
                self.resources[pool]['lockprio'][host] -= 2
                return False
            
            if host in self.resources[pool]['lockprio']:
                del self.resources[pool]['lockprio'][host]
           
        if not lockby:
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
            'lockprio': {},
            'maxlocks': maxlocks
        }
