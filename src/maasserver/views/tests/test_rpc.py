# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver RPC views."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

import json

from crochet import run_in_reactor
from django.core.urlresolvers import reverse
from maasserver import eventloop
from maasserver.testing.testcase import MAASServerTestCase
from provisioningserver.utils import get_all_interface_addresses
from testtools.matchers import (
    Equals,
    GreaterThan,
    IsInstance,
    KeysEqual,
    LessThan,
    MatchesAll,
    MatchesDict,
    MatchesListwise,
    )
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread


is_valid_port = MatchesAll(
    IsInstance(int), GreaterThan(0), LessThan(2 ** 16))


class RPCViewTest(MAASServerTestCase):

    # XXX 2014-03-05 gmb bug=1288001:
    #     This fails due to an apparent isolation problem.
    def test_rpc_info(self):
        self.skip("Disabled due to a test isolation problem.")
        response = self.client.get(reverse('rpc-info'))
        self.assertEqual("application/json", response["Content-Type"])
        info = json.loads(response.content)
        self.assertEqual({"eventloops": {}}, info)

    def test_rpc_info_when_rpc_running(self):
        eventloop.start().wait(5)
        self.addCleanup(lambda: eventloop.stop().wait(5))

        getServiceNamed = eventloop.services.getServiceNamed

        @run_in_reactor
        @inlineCallbacks
        def wait_for_startup():
            # Wait for the rpc and the rpc-advertise services to start.
            yield getServiceNamed("rpc").starting
            yield getServiceNamed("rpc-advertise").starting
            # Force an update, because it's very hard to track when the
            # first iteration of the rpc-advertise service has completed.
            yield deferToThread(getServiceNamed("rpc-advertise").update)
        wait_for_startup().wait(5)

        response = self.client.get(reverse('rpc-info'))

        self.assertEqual("application/json", response["Content-Type"])
        info = json.loads(response.content)
        self.assertThat(info, KeysEqual("eventloops"))
        self.assertThat(info["eventloops"], MatchesDict({
            # Each entry in the endpoints dict is a mapping from an
            # event loop to a list of (host, port) tuples. Each tuple is
            # a potential endpoint for connecting into that event loop.
            eventloop.loop.name: MatchesListwise([
                MatchesListwise((Equals(addr), is_valid_port))
                for addr in get_all_interface_addresses()
            ]),
        }))
