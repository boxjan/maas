# Copyright 2025 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from unittest.mock import Mock

from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
import pytest

from maasapiserver.v3.api.public.models.requests.boot_sources import (
    BootSourcesRequest,
)
from maasapiserver.v3.api.public.models.responses.boot_sources import (
    BootSourcesResponse,
)
from maasapiserver.v3.constants import V3_API_PREFIX
from maasservicelayer.services import ServiceCollectionV3
from maasservicelayer.services.boot_sources import BootSourcesService
from maasservicelayer.utils.images.boot_image_mapping import BootImageMapping
from maastesting.factory import factory
from tests.fixtures.factories.boot_sources import make_image_spec, set_resource
from tests.maasapiserver.v3.api.public.handlers.base import (
    ApiCommonTests,
    Endpoint,
)


class TestBootSourcesApi(ApiCommonTests):
    BASE_PATH = f"{V3_API_PREFIX}/boot_sources"

    @pytest.fixture
    def user_endpoints(self) -> list[Endpoint]:
        return [
            Endpoint(method="POST", path=f"{self.BASE_PATH}:fetch"),
        ]

    @pytest.fixture
    def admin_endpoints(self) -> list[Endpoint]:
        return []

    async def test_list_boot_sources(
        self,
        services_mock: ServiceCollectionV3,
        mocked_api_client_user: AsyncClient,
    ) -> None:
        # Construct a BootImageMapping with some fake image specs.
        mapping = BootImageMapping()

        releases = [factory.make_name("release") for _ in range(3)]
        arches = [factory.make_name("arch") for _ in range(3)]
        image_specs = [
            make_image_spec(os="ubuntu", arch=arch, release=release)
            for release, arch in zip(releases, arches)
        ]
        for spec in image_specs:
            set_resource(mapping, spec, {})

        print(list(mapping.items()))
        assert False

        services_mock.boot_sources = Mock(BootSourcesService)
        services_mock.boot_sources.fetch.return_value = mapping

        request = BootSourcesRequest(
            url="",
        )


        response = await mocked_api_client_user.post(f"{self.BASE_PATH}:fetch", json=jsonable_encoder(request))


        assert response.status_code == 200

        actual_response = BootSourcesResponse(**response.json())

        assert actual_response.boot_sources == mapping
