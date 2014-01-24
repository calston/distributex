from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.web import server

import distributex


class Options(usage.Options):
    optParameters = [
        ["port", "p", 9889, "The port to listen on."],
        ["config", "c", "distributex.yaml", "Config file."]
    ]

class DistributexServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "distributex"
    description = "Distributex - A simple mutex lock service"
    options = Options
    def makeService(self, options):
        return internet.TCPServer(
            int(options['port']),
            server.Site(distributex.SiteRoot(options['config']))
        )

serviceMaker = DistributexServiceMaker()
