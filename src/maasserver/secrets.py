from typing import Any, NamedTuple, Optional

from django.db.models import Model
from hvac.exceptions import InvalidPath

from maasserver.models import Node, Secret
from maasserver.vault import get_region_vault_client, VaultClient

SIMPLE_SECRET_KEY = "secret"


class ModelSecret(NamedTuple):
    model: Model
    prefix: str
    secret_names: list[str]


MODEL_SECRETS = {
    secret.model: secret
    for secret in (ModelSecret(Node, "node", ["deploy-metadata"]),)
}


class SecretNotFound(Exception):
    """Raised when a secret is not found."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Secret '{path}' not found")


UNSET = object()


class SecretManager:
    """Handle operations on secrets."""

    def __init__(self, vault_client: Optional[VaultClient] = None):
        self._vault_client = vault_client or get_region_vault_client()

    def set_composite_secret(
        self, name: str, value: dict[str, Any], obj: Optional[Model] = None
    ):
        """Create or update a secret."""
        path = self._get_secret_path(name, obj=obj)
        if self._vault_client:
            self._vault_client.set(path, value)
        else:
            Secret.objects.update_or_create(
                path=path, defaults={"value": value}
            )

    def set_simple_secret(
        self, name: str, value: Any, obj: Optional[Model] = None
    ):
        """Create or update a simple secret."""
        self.set_composite_secret(
            name, value={SIMPLE_SECRET_KEY: value}, obj=obj
        )

    def delete_secret(self, name: str, obj: Optional[Model] = None):
        """Delete a secret, either global or for a model instance."""
        path = self._get_secret_path(name, obj=obj)
        if self._vault_client:
            self._vault_client.delete(path)
        else:
            Secret.objects.filter(path=path).delete()

    def delete_all_object_secrets(self, obj: Model):
        """Delete all known secrets for an object."""
        prefix = self._get_secret_path_prefix_for_object(obj)
        paths = tuple(
            f"{prefix}/{name}"
            for name in MODEL_SECRETS[type(obj)].secret_names
        )
        if self._vault_client:
            for path in paths:
                self._vault_client.delete(path)
        else:
            Secret.objects.filter(path__in=paths).delete()

    def get_composite_secret(
        self,
        name: str,
        obj: Optional[Model] = None,
        default: Any = UNSET,
    ):
        """Return the value for a secret.

        The secret can be either global or for a model instance.
        """
        path = self._get_secret_path(name, obj=obj)
        try:
            if self._vault_client:
                return self._get_secret_from_vault(path)

            return self._get_secret_from_db(path)
        except SecretNotFound:
            if default is UNSET:
                raise
            return default

    def get_simple_secret(
        self,
        name: str,
        obj: Optional[Model] = None,
        default: Any = UNSET,
    ):
        """Return the value for a simple secret.

        Simple secrets are stored as values of a single SIMPLE_SECRET_KEY key.

        The secret can be either global or for a model instance.
        """
        try:
            secret = self.get_composite_secret(name, obj=obj)
        except SecretNotFound:
            if default is UNSET:
                raise
            return default
        return secret[SIMPLE_SECRET_KEY]

    def _get_secret_path(self, name: str, obj: Optional[Model] = None) -> str:
        prefix = (
            self._get_secret_path_prefix_for_object(obj) if obj else "global"
        )
        return f"{prefix}/{name}"

    def _get_secret_path_prefix_for_object(self, obj: Model) -> str:
        model_secret = MODEL_SECRETS[type(obj)]
        return f"{model_secret.prefix}/{obj.id}"

    def _get_secret_from_db(self, path: str):
        try:
            return Secret.objects.get(path=path).value
        except Secret.DoesNotExist:
            raise SecretNotFound(path)

    def _get_secret_from_vault(self, path: str):
        try:
            return self._vault_client.get(path)
        except InvalidPath:
            raise SecretNotFound(path)
