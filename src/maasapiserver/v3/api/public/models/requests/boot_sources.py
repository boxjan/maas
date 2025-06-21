# Copyright 2025 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import base64

from pydantic import BaseModel, Field, validator

from maasservicelayer.builders.bootsources import BootSourceBuilder
from maasservicelayer.exceptions.catalog import ValidationException


class BootSourceRequest(BaseModel):
    url: str = Field(
        description="URL of SimpleStreams server providing boot source "
        "information."
    )
    keyring_filename: str | None = Field(
        default="",
        description="File path to keyring to use for verifying signatures of "
        "the boot sources.",
    )
    keyring_data: str | None = Field(
        default="",
        description="Base64-encoded keyring data used for signature "
        "verification. Optional alternative to providing a keyring "
        "file path.",
    )
    # priority   <=== missing

    @validator("keyring_data")
    def validate_b64_keyring_data(cls, v: str):
        if v is None or v == "":
            return None
        try:
            return base64.b64decode(v)
        except Exception as e:
            raise ValidationException.build_for_field(
                field="definition",
                message=f"keyring_data must be valid Base64-encoded binary data: {e}",
            ) from e

    def to_builder(self) -> BootSourceBuilder:
        return BootSourceBuilder(
            url=self.url,
            keyring_filename=self.keyring_filename,
            keyring_data=self.keyring_data,
        )


class BootSourceFetchRequest(BaseModel):
    url: str = Field(
        description="URL of SimpleStreams server providing boot source information."
    )

    keyring_path: str | None = Field(
        default=None,
        description="File path to keyring to use for verifying signatures of the boot sources.",
    )
    keyring_data: str | None = Field(
        default=None,
        description="Keyring data to use for verifying signatures of the boot sources.",
    )
    user_agent: str | None = Field(
        default=None,
        description="User agent to use when fetching boot sources.",
    )
    validate_products: bool = Field(
        default=True,
        description="Whether to validate products in the boot sources.",
    )
