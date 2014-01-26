from twisted.application import internet, service
from twisted.web import server, resource, client
from twisted.internet import defer, reactor, threads, utils, task
from zope import interface

import yaml
import time
import cgi
import random

from distributex.backends import in_memory_backend, memcached_backend

class SiteRoot(resource.Resource):
    isLeaf = True
    addSlash = True

    def __init__(self, config):
        self.backends = {
            'memcache': memcached_backend.MemcachedBackend,
            'inmemory': in_memory_backend.InMemoryDictBackend
        }
        self.config = yaml.load(open(config))
        self.ready = False
        reactor.callWhenRunning(self.setup)

    @defer.inlineCallbacks
    def setup(self):
        # Initialise the configured backend
        self.backend = self.backends[
            self.config.get('backend', 'inmemory')
        ](self.config)

        self.pools = {}

        # Construct our pools 
        for pool in self.config.get('pools', []):
            if 'servers' in pool:
                servers = pool['servers'].replace(' ', '').split(',')
            else:
                servers = []

            self.pools[pool['name']] = servers

            expire = pool.get('expire', 1800)

            yield defer.maybeDeferred(
                self.backend.add_pool, pool['name'], expire
            )
        
        self.ready = True
        defer.returnValue(None)

    def request_finish(self, request, result):
        request.write(result)
        request.finish()

    def wait_finish(self, lock, request, timer):
        if timer.running:
            timer.stop()

        self.request_finish(request, 'YES')

    def wait_bailout(self, error, request, timer):
        if timer.running:
            timer.stop()

        self.request_finish(request, 'NO')

    @defer.inlineCallbacks
    def wait_lock(self, d, pool, host):
        lock = yield defer.maybeDeferred(
            self.backend.get_lock, pool, host
        )
        
        if lock:
            d.callback(True)

    def request_wait(self, request, pool, host):
        d = defer.Deferred()

        timer = task.LoopingCall(self.wait_lock, d, pool, host)

        d.addCallback(self.wait_finish, request, timer)
        d.addErrback(self.wait_bailout, request, timer)

        timer.start(1 + random.random(), True)

        return d
    
    def request_release(self, request, pool, host):
        d = defer.maybeDeferred(
            self.backend.release_lock, pool, host
        ).addCallback(lambda _: self.request_finish(request, 'OK'))

    def request_getlock(self, request, pool, host):
        d = defer.maybeDeferred(
            self.backend.get_lock, pool, host
        ).addCallback(
            lambda l: self.request_finish(request, l and 'YES' or 'NO')
        )

    def handle_request(self, request):
        if not self.ready:
            reactor.callLater(0, self.handle_request, request)

        else:
            call = request.path.replace('/', '')

            if not (('host' in request.args) and ('pool' in request.args)):
                self.request_finish(request, 'INVALID')
                return

            host = cgi.escape(request.args["host"][0])
            pool = cgi.escape(request.args["pool"][0])

            if pool in self.pools:
                if self.pools[pool]:
                    # Server not allowed
                    if not(host in self.pools[pool]):
                        self.request_finish(request, 'INVALID')
                        return
            else:
                self.request_finish(request, 'INVALID')
                return

            if call == 'wait':
                # Wait for a lock
                reactor.callLater(random.random()/5, self.request_wait, 
                    request, pool, host)

            elif call == 'release':
                # Release a lock
                self.request_release(request, pool, host)

            elif call == 'get':
                # Get a lock, don't wait for it
                self.request_getlock(request, pool, host)

            else:
                self.request_finish(request, 'INVALID')

    def render_GET(self, request):
        self.handle_request(request)
        return server.NOT_DONE_YET
