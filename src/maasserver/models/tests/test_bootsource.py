# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `BootSource`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from base64 import b64encode
import os

from django.core.exceptions import ValidationError
from maasserver.models import BootSource
from maasserver.testing.factory import factory
from maastesting.testcase import MAASTestCase


class TestBootSource(MAASTestCase):
    """Tests for the `BootSource` model."""

    def test_valid_boot_source_is_valid(self):
        cluster = factory.make_node_group()
        boot_source = BootSource(
            cluster=cluster,
            url="http://example.com",
            keyring_filename="/path/to/something")
        boot_source.save()
        self.assertTrue(
            BootSource.objects.filter(id=boot_source.id).exists())

    def test_cannot_set_keyring_data_and_filename(self):
        # A BootSource cannot have both a keyring filename and keyring
        # data. Attempting to set both will raise an error.
        cluster = factory.make_node_group()
        boot_source = BootSource(
            cluster=cluster, url="http://example.com",
            keyring_filename="/path/to/something",
            keyring_data=b"blahblahblahblah")
        self.assertRaises(ValidationError, boot_source.clean)

    def test_cannot_leave_keyring_data_and_filename_unset(self):
        cluster = factory.make_node_group()
        boot_source = BootSource(
            cluster=cluster, url="http://example.com",
            keyring_filename="", keyring_data=b"")
        self.assertRaises(ValidationError, boot_source.clean)

    def test_deleting_cluster_deletes_its_boot_sources(self):
        # Cluster deletion cascade-deletes the BootSource. This is
        # implicit in Django but it's worth adding a test for it all
        # the same.
        cluster = factory.make_node_group()
        boot_source = factory.make_boot_source(cluster=cluster)
        cluster.delete()
        self.assertNotIn(
            boot_source.id,
            [source.id for source in BootSource.objects.all()])

    def test_to_dict_returns_dict(self):
        boot_source = factory.make_boot_source(
            keyring_data=b"123445", keyring_filename='')
        boot_source_selection = factory.make_boot_source_selection(
            boot_source=boot_source)
        boot_source_dict = boot_source.to_dict()
        self.assertEqual(boot_source.url, boot_source_dict['path'])
        self.assertEqual(
            [boot_source_selection.to_dict()],
            boot_source_dict['selections'])

    def test_to_dict_handles_keyring_file(self):
        keyring_data = b"Some Keyring Data"
        keyring_file = self.make_file(contents=keyring_data)
        self.addCleanup(os.remove, keyring_file)

        boot_source = factory.make_boot_source(
            keyring_data=b"", keyring_filename=keyring_file)
        source = boot_source.to_dict()
        self.assertEqual(
            source['keyring_data'],
            b64encode(keyring_data))

    def test_to_dict_handles_keyring_data(self):
        keyring_data = b"Some Keyring Data"
        boot_source = factory.make_boot_source(
            keyring_data=keyring_data, keyring_filename="")
        source = boot_source.to_dict()
        self.assertEqual(
            source['keyring_data'],
            b64encode(keyring_data))
