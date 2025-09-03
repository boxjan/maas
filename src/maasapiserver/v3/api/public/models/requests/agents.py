# Copyright 2025 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from pydantic import BaseModel, Field

from maasservicelayer.builders.agents import AgentBuilder


class AgentRequest(BaseModel):
    secret: str = Field(description="")
    rack_id: int = Field(description="")
    rackcontroller_id: int = Field(description="")

    def to_builder(self) -> AgentBuilder:
        return AgentBuilder(
            secret=self.secret,
            rack_id=self.rack_id,
            rackcontroller_id=self.rackcontroller_id,
        )
