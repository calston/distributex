# Distributex

Distributex is a simple mutex service for coordinating certain cluster
operations.

**Note**: Distributex is not designed for tasks which require high performance
or fair lock acquisition. It is a very simple Busy-waiting lock with very slow
acquisition. Do not use it for extremely large clusters either as there's 
a good chance a requester might never obtain a lock.

## Distributex server

The Distributex server provides a simple HTTP service. It is written using
Twisted, and provides a Twisted plugin. It also requires PyYAML for its 
configuration. 

You can start it as follows, or wrap it in supervisor, or pass -d, or whatever

> $ twistd -n distributex -c distributex.yaml

The configuration file is a simple YAML structure which defines lock pools. A
lock pool is a resource you want to allow things to fight over.

```
backend: memcache
pools:
    - name: pool1
      expire: 300

    - name: pool2
      expire: 300
      servers: acme1, acme2
```

You can specify either the 'memcache' backend or 'inmemory', there are pros
and cons to both. Memcache will be slower, but state is retained away from 
the Distributex server and you can scale out workers - however since the 
inmemory backend can handle about 5000 waiting locks on a single machine 
redundancy is the only real concern. Lock expiry is also a bit more reliable
and simpler in the memcache backend.

This will create two pools whose lock expires after 5 minutes. It's generally
a good idea to set an expiry to ensure something, otherwise it will default to
30 minutes. If you don't want it to expire then set it to 0, but I don't 
recommend that.

A comma separated list of servers can also be provided to prevent accidental
pool incursions. This isn't secure, nor are lock releases, since anyone can
just forge their hostname. The distributex client will pass the FQDN of the
host.

You can test the service as follows

```
$ curl "http://localhost:9889/get/?host=me&pool=pool1"
YES
$ curl "http://localhost:9889/get/?host=them&pool=pool1"
NO
$ curl "http://localhost:9889/release/?host=me&pool=pool1"
OK
$ curl "http://localhost:9889/get/?host=them&pool=pool1"
YES
$ curl "http://localhost:9889/release/?host=them&pool=pool1"
OK
```

The service also provides a 'wait' command which will leave the connection
open until a lock is obtained.


## Distributex client

A simple Python script is provided to wrap commands.

```
usage: distributex [-h] -H HOST -r POOL [-p PORT] [command]

Distributex client

positional arguments:
  command     Command to execute when lock is obtained

optional arguments:
  -h, --help  show this help message and exit
  -H HOST     Server hostname
  -r POOL     Resource pool
  -p PORT     Server port (default 9889)
  -l          Use local locking as well
```

This is useful for blocking a cron job like Puppet.

```
*/5 * * * * /usr/bin/distributex -H distributex.acme.com -r pool1 '/usr/bin/puppet agent --onetime --no-daemonize'
```

This will ensure that only one instance of Puppet in the cluster runs at any time.
You might also want to pass -l to distributex to prevent local process overlap.
