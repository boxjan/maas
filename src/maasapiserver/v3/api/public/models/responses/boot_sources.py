# Copyright 2025 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from maasapiserver.v3.api.public.models.responses.base import (
    BaseHal,
    HalResponse,
)
from maasservicelayer.utils.images.boot_image_mapping import BootImageMapping


class BootSourcesResponse(HalResponse[BaseHal]):
    kind = "BootSources"
    boot_sources: object
