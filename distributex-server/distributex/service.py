from twisted.application import internet, service
from twisted.web import server, resource, client
from twisted.internet import defer, reactor, threads, utils, task
from zope import interface

import yaml
import time
import cgi
import random


# Because it might be useful to support something sane like memcache, redis
# or rabbitmq in future...
class ICacheBackend(interface.Interface):
    def get_lock(self, pool, host):
        """
        Try to get a lock on a specific pool
        """

    def release_lock(self, pool, host):
        """
        Release the lock on a pool
        """

    def add_pool(self, pool, expire, hosts):
        """
        Create and configure a lock pool
        """

class InMemoryDictBackend(object):
    interface.implements(ICacheBackend)
    
    def __init__(self):
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
        
    def add_pool(self, pool, expire, hosts):
        self.resources[pool] = {
            'hosts': hosts, 
            'expire': expire,
            'lockedby': None,
            'locktime': 0
        }

class SiteRoot(resource.Resource):
    isLeaf = True
    addSlash = True

    def __init__(self, config):
        self.config = yaml.load(open(config))

        self.backend = InMemoryDictBackend()

        self.pools = {}

        for pool in self.config.get('pools', []):
            if 'servers' in pool:
                servers = pool['servers'].replace(' ', '').split(',')
            else:
                servers = []

            self.pools[pool['name']] = servers

            self.backend.add_pool(
                pool['name'], 
                pool.get('expire', 1800),
                servers
            )
        
        print self.backend.resources

    def wait_finish(self, lock, request, timer):
        if timer.running:
            timer.stop()
        request.write('YES')
        request.finish()

    def wait_bailout(self, error, request, timer):
        if timer.running:
            timer.stop()
        request.write('NO')
        request.finish()

    def wait_lock(self, d, pool, host):
        lock = self.backend.get_lock(pool, host)
        
        if lock:
            d.callback(True)

    def request_wait(self, request, pool, host):
        d = defer.Deferred()

        timer = task.LoopingCall(self.wait_lock, d, pool, host)

        d.addCallback(self.wait_finish, request, timer)
        d.addErrback(self.wait_bailout, request, timer)

        timer.start(1 + random.random(), True)

        return d

    def render_GET(self, request):
        call = request.path.replace('/', '')

        if not (('host' in request.args) and ('pool' in request.args)):
            return "INVALID"

        host = cgi.escape(request.args["host"][0])
        pool = cgi.escape(request.args["pool"][0])

        if pool in self.pools:
            if self.pools[pool]:
                # Server not allowed
                if not(host in self.pools[pool]):
                    return "NOT ALLOWED"
        else:
            return "INVALID"

        if call == 'wait':
            # Wait for a lock
            reactor.callLater(random.random()/5, self.request_wait, 
                request, pool, host)

            return server.NOT_DONE_YET

        elif call == 'release':
            # Release a lock
            self.backend.release_lock(pool, host)
            return "OK"

        elif call == 'get':
            # Get a lock, don't wait for it
            if self.backend.get_lock(pool, host):
                return "YES"
            else:
                return "NO"

        else:
            return "INVALID"
