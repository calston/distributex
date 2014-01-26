from twisted.internet import protocol, reactor, defer
from twisted.protocols.memcache import MemCacheProtocol
from twisted.python import log
from zope import interface

from distributex.backends import backend

import time


class ReconnectingMemCacheClientFactory(protocol.ReconnectingClientFactory):
    protocol = MemCacheProtocol

    def __init__(self, connected):
        self.connected = connected

    def buildProtocol(self, addr):
        self.client = self.protocol()
        self.addr = addr
        self.client.factory = self
        self.resetDelay()
        self.connected()
        return self.client

class MemcacheClientMixin(object):
    def __init__(self, config):
        self.memcached_factory = ReconnectingMemCacheClientFactory(self.connected)
        self.host = config.get('memcachehost', 'localhost')
        self.port = config.get('memcacheport', 11211)
        
        self.memcache = None
        reactor.connectTCP(self.host, self.port, self.memcached_factory)

    def connected(self):
        """
        Called when memcache connection is established
        """
        self.memcache = self.memcached_factory.client

    def disconnect(self):
        """
        Disconnect memcache
        """
        self.memcached_factory.stopTrying()
        return self.memcache.transport.loseConnection()

    def wait_for_connection(self):
        """
        Return a deferred which waits until we have a connection to memcache
        """
        d = defer.Deferred()

        def r(d):
            if not self.memcache:
                reactor.callLater(0, r, d)
            else:
                d.callback(True)

        r(d)
        return d

    def set_key(self, pool, key, value, expire=0):
        """
        Set a memcache key for a pool
        """
        return self.wait_for_connection().addCallback(lambda _:
            self.memcache.set('%s:%s' % (pool, key), str(value), expireTime=expire)
        )

    def get_key(self, pool, key):
        """
        Get a memcache key for a pool
        """
        return self.wait_for_connection().addCallback(lambda _:
            self.memcache.get('%s:%s' % (pool, key))
        )

    def delete_key(self, pool, key):
        """
        Delete a key for a pool
        """
        return self.wait_for_connection().addCallback(lambda _:
            self.memcache.delete('%s:%s' % (pool, key))
        )

class MemcachedBackend(MemcacheClientMixin):
    interface.implements(backend.ICacheBackend)
   
    @defer.inlineCallbacks
    def get_lock(self, pool, host):
        _, lock_s = yield self.get_key(pool, 'lockedby')
        if lock_s:
            if lock_s == host:
                defer.returnValue(True)
            else:
                defer.returnValue(False)
        else:
            _, expire = yield self.get_key(pool, 'expire')
            yield self.set_key(pool, 'lockedby', host, expire=int(expire))
            defer.returnValue(True)

    @defer.inlineCallbacks
    def release_lock(self, pool, host):
        _, lock_s = yield self.get_key(pool, 'lockedby')
        if lock_s == host:
            yield self.delete_key(pool, 'lockedby')

        defer.returnValue(None)
   
    def add_pool(self, pool, expire):
        return self.set_key(pool, 'expire', expire)

