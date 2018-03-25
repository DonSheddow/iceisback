import argparse
import json
import queue
from datetime import datetime
from multiprocessing import Process, Queue

from twisted.internet import reactor, defer
from twisted.names import dns, error, server

import config
from send_mail import mail_daemon


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

    def __init__(self, send_mail=False):
        self._peer_address = None
        self.send_mail = send_mail
        if send_mail:
            self.mail_queue = q = Queue()
            self.proc = Process(target=mail_daemon, args=(q,))
            self.proc.start()

    def _send_mail(self, ip, domain, time):
        msg = {"ip": ip, "domain": domain, "time": time}

        try:
            self.mail_queue.put(msg, block=False)
        except queue.Full:
            print("Unable to send email (queue is full)")

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
        return query.type == dns.A and query.name.name.endswith(config.ROOT_DOMAIN)

    def _doDynamicResponse(self, query):
        """
        Calculate the response to a query.
        """
        name = query.name.name

        time = datetime.now()
        ip = self.peer_address[0]
        domain = name.decode('ascii')
        
        print("[{time}] {ip} {domain}".format(time=time, ip=ip, domain=domain), flush=True)

        if self.send_mail:
            self._send_mail(ip, domain, time)

        answer = dns.RRHeader(
            name=name,
            payload=dns.Record_A(address=config.IP_RESPONSE))
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
    parser.add_argument("--send-mail", action="store_true",
                        help="Send an email when receiving a DNS request")
    args = parser.parse_args()

    factory = MyDNSServerFactory(
        clients=[DynamicResolver(send_mail=args.send_mail)]
    )

    protocol = dns.DNSDatagramProtocol(controller=factory)

    reactor.listenUDP(args.port, protocol)
    reactor.listenTCP(args.port, factory)

    reactor.run()



if __name__ == '__main__':
    raise SystemExit(main())
