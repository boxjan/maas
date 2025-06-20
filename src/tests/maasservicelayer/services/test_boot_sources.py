# Copyright 2025 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
from unittest.mock import ANY, call, MagicMock, Mock, patch

import pytest

from maasservicelayer.context import Context
from maasservicelayer.services.boot_sources import BootSourcesService
from maasservicelayer.services.configurations import ConfigurationsService
from maastesting.factory import factory


@pytest.mark.asyncio
class TestBootSourcesService:
    @patch("maasservicelayer.services.boot_sources.RepoDumper.sync")
    @patch("maasservicelayer.services.boot_sources.UrlMirrorReader")
    async def test_fetch_calls_repodumper_with_correct_urlmirrorreader(
        self,
        urlmirrorreader_mock: MagicMock,
        repodumper_sync_mock: MagicMock,
    ) -> None:
        source_url = factory.make_url()
        user_agent = "maas/3.6.4/g.12345678"

        expected_mirror_url = "streams/v1/index.sjson"

        configurations_service_mock = Mock(ConfigurationsService)

        boot_sources_service = BootSourcesService(
            context=Context(),
            configuration_service=configurations_service_mock,
        )

        boot_sources_service._fetch(source_url, user_agent=user_agent)

        repodumper_sync_mock.assert_called_once_with(
            urlmirrorreader_mock.return_value,
            expected_mirror_url,
        )
        urlmirrorreader_mock.assert_called_once_with(
            source_url,
            policy=ANY,
            user_agent=user_agent,
        )

    @patch("maasservicelayer.services.boot_sources.BootSourcesService._fetch")
    async def test_fetch_gets_maas_user_agent(
        self,
        fetch_submethod_mock: MagicMock,
    ) -> None:
        source_url = factory.make_url()
        user_agent = "maas/3.6.4/g.12345678"

        configurations_service_mock = Mock(ConfigurationsService)
        configurations_service_mock.get_maas_user_agent.return_value = (
            user_agent
        )

        boot_sources_service = BootSourcesService(
            context=Context(),
            configuration_service=configurations_service_mock,
        )

        # Test the async fetch calls the _fetch submethod with the maas user agent.
        await boot_sources_service.fetch(source_url)

        configurations_service_mock.get_maas_user_agent.assert_called_once()
        fetch_submethod_mock.assert_called_once_with(
            source_url,  # source_url
            user_agent,  # user_agent
            None,  # keyring_path
            None,  # keyring_data
            True,  # validate_products
        )

    @patch("maasservicelayer.services.boot_sources.RepoDumper.sync")
    @patch("maasservicelayer.services.boot_sources.UrlMirrorReader")
    async def test_fetch_passes_maas_user_agent_through(
        self,
        urlmirrorreader_mock: MagicMock,
        repodumper_sync_mock: MagicMock,
    ) -> None:
        source_url = factory.make_url()
        expected_mirror_url = "streams/v1/index.sjson"
        user_agent = "maas/3.6.4/g.12345678"

        configurations_service_mock = Mock(ConfigurationsService)

        boot_sources_service = BootSourcesService(
            context=Context(),
            configuration_service=configurations_service_mock,
        )

        boot_sources_service._fetch(source_url, user_agent=user_agent)

        # Also doesn't pass user agent when not set.
        repodumper_sync_mock.assert_called_once_with(
            urlmirrorreader_mock.return_value,
            expected_mirror_url,
        )
        urlmirrorreader_mock.assert_called_once_with(
            source_url,
            policy=ANY,
            user_agent=user_agent,
        )

    @patch("maasservicelayer.services.boot_sources.RepoDumper.sync")
    @patch("maasservicelayer.services.boot_sources.UrlMirrorReader")
    async def test_fetch_doesnt_pass_user_agent_on_fallback(
        self,
        urlmirrorreader_mock: MagicMock,
        repodumper_sync_mock: MagicMock,
    ) -> None:
        # This is a test covering simplestream-specific behavior that could be
        # removed should we move away from this library.
        # TODO: Remove this test if/when we stop using simplestreams.
        source_url = factory.make_url()
        user_agent = "maas/3.6.4/g.12345678"

        configurations_service_mock = Mock(ConfigurationsService)
        configurations_service_mock.get_maas_user_agent.return_value = (
            user_agent
        )

        boot_sources_service = BootSourcesService(
            context=Context(),
            configuration_service=configurations_service_mock,
        )

        urlmirrorreader_mock.side_effect = [TypeError(), MagicMock()]

        boot_sources_service._fetch(source_url, user_agent=user_agent)

        repodumper_sync_mock.assert_called()
        urlmirrorreader_mock.assert_has_calls(
            [
                call(source_url, policy=ANY, user_agent=user_agent),
                call(source_url, policy=ANY),
            ]
        )

    @patch("maasservicelayer.services.boot_sources.write_keyring")
    @patch("maasservicelayer.services.boot_sources.RepoDumper.sync")
    @patch("maasservicelayer.services.boot_sources.UrlMirrorReader")
    async def test_fetch_writes_keyring_data_to_path(
        self,
        urlmirrorreader_mock: MagicMock,
        repodumper_sync_mock: MagicMock,
        write_keyring_mock: MagicMock,
    ) -> None:
        source_url = factory.make_url()
        keyring_path = "/tmp/keyring_file"
        keyring_data = "keyring_data"
        user_agent = "maas/3.6.4/g.12345678"

        expected_mirror_url = "streams/v1/index.sjson"

        configurations_service_mock = Mock(ConfigurationsService)

        boot_sources_service = BootSourcesService(
            context=Context(),
            configuration_service=configurations_service_mock,
        )

        boot_sources_service._fetch(
            source_url,
            keyring_path=keyring_path,
            keyring_data=keyring_data,
            user_agent=user_agent,
        )

        write_keyring_mock.assert_called_once_with(
            keyring_path, keyring_data.encode("utf-8")
        )
        urlmirrorreader_mock.assert_called_once_with(
            source_url,
            policy=ANY,
            user_agent=user_agent,
        )
        repodumper_sync_mock.assert_called_once_with(
            urlmirrorreader_mock.return_value,
            expected_mirror_url,
        )

    @patch("maasservicelayer.services.boot_sources.write_keyring")
    @patch("maasservicelayer.services.boot_sources.calculate_keyring_name")
    @patch("maasservicelayer.services.boot_sources.tempdir")
    @patch("maasservicelayer.services.boot_sources.RepoDumper.sync")
    @patch("maasservicelayer.services.boot_sources.UrlMirrorReader")
    async def test_fetch_writes_keyring_data_to_tempdir(
        self,
        urlmirrorreader_mock: MagicMock,
        repodumper_sync_mock: MagicMock,
        tempdir_mock: MagicMock,
        calculate_keyring_name_mock: MagicMock,
        write_keyring_mock: MagicMock,
    ) -> None:
        source_url = factory.make_url()
        keyring_data = "keyring_data"
        user_agent = "maas/3.6.4/g.12345678"

        tmp_path = "/tmp/abc_keyrings"
        calc_keyring_name = "calculated_keyring_name"
        expected_mirror_url = "streams/v1/index.sjson"

        configurations_service_mock = Mock(ConfigurationsService)

        boot_sources_service = BootSourcesService(
            context=Context(),
            configuration_service=configurations_service_mock,
        )

        tempdir_mock.return_value.__enter__.return_value = tmp_path
        calculate_keyring_name_mock.return_value = calc_keyring_name

        boot_sources_service._fetch(
            source_url,
            user_agent=user_agent,
            keyring_path=None,
            keyring_data=keyring_data,
        )

        write_keyring_mock.assert_called_once_with(
            os.path.join(tmp_path, calc_keyring_name),
            keyring_data.encode("utf-8"),
        )
        urlmirrorreader_mock.assert_called_once_with(
            source_url,
            policy=ANY,
            user_agent=user_agent,
        )
        repodumper_sync_mock.assert_called_once_with(
            urlmirrorreader_mock.return_value,
            expected_mirror_url,
        )
