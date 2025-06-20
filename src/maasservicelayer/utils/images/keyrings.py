# Copyright 2025 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import hashlib

import structlog

logger = structlog.getLogger()


def write_keyring(keyring_path: str, keyring_data: bytes) -> None:
    """Write a keyring blob to a file.

    :param keyring_path: The path to the keyring file.
    :param keyring_data: The data to write to the keyring_file, as a
        base64-encoded string.
    """
    logger.debug(f"Writing keyring {keyring_path} to disk.")
    with open(keyring_path, "wb") as keyring_file:
        keyring_file.write(keyring_data)


def calculate_keyring_name(source_url: str) -> str:
    """Return a name for a keyring based on a URL.

    :param source_url: The URL of the source with which to calculate the keyring name.
    :return: A hexadecimal digest of the MD5 hash of the source URL.
    """
    return hashlib.md5(source_url.encode("utf8")).hexdigest()
