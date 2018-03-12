import argparse
from datetime import datetime

from twisted.internet import reactor, defer
from twisted.names import dns, error, server


ROOT_DOMAIN = b'.n.sheddow.xyz'
IP_RESPONSE = b'127.0.0.1'


class MyDNSServerFactory(server.DNSServerFactory):

    def handleQuery(self, message, protocol, address):
        if address is not None:
            self.peer_address = address
        else:
            self.peer_address = protocol.transport.getHandle().getpeername()

        # Make peer_address available to resolvers that support that attribute
        for resolver in self.resolver.resolvers:
            if hasattr(resolver, 'peer_address'):
                resolver.peer_address = self.peer_address

        return super().handleQuery(message, protocol, address)


class DynamicResolver(object):
    """
    A resolver which calculates the answers to certain queries based on the
    query type and name.
    """

    def __init__(self):
        self._peer_address = None

    @property
    def peer_address(self):
        return self._peer_address

    @peer_address.setter
    def peer_address(self, value):
        self._peer_address = value

    def _dynamicResponseRequired(self, query):
        """
        Check the query to determine if a dynamic response is required.
        """
        return query.type == dns.A and query.name.name.endswith(ROOT_DOMAIN)

    def _doDynamicResponse(self, query):
        """
        Calculate the response to a query.
        """
        name = query.name.name
        
        msg = name[:-len(ROOT_DOMAIN)]

        print("[{time}] {ip} {msg}".format(
            time=datetime.now(),
            ip=self.peer_address[0],
            msg=msg.decode('ascii')))

        answer = dns.RRHeader(
            name=name,
            payload=dns.Record_A(address=IP_RESPONSE))
        return [answer], [], []

    def query(self, query, timeout=None):
        """
        Check if the query should be answered dynamically, otherwise dispatch to
        the fallback resolver.
        """
        if self._dynamicResponseRequired(query):
            return defer.succeed(self._doDynamicResponse(query))
        else:
            return defer.fail(error.DomainError())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=10053,
                        help="TCP/UDP port to listen on")
    args = parser.parse_args()

    factory = MyDNSServerFactory(
        clients=[DynamicResolver()]
    )

    protocol = dns.DNSDatagramProtocol(controller=factory)

    reactor.listenUDP(args.port, protocol)
    reactor.listenTCP(args.port, factory)

    reactor.run()



if __name__ == '__main__':
    raise SystemExit(main())
