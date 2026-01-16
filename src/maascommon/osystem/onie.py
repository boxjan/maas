# Copyright 2025 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ONIE Operating System.

ONIE (Open Network Install Environment) is a boot loader for bare metal
network switches that enables OS installation via the network.

ONIE Image Format:
- Most commonly: Self-extracting shell scripts with embedded binary data
- Typical names: onie-installer-x86_64, onie-installer-arm64, etc.
- Size: 50-500 MB (up to 1 GB for some vendors)
- MAAS stores and serves these as-is without modification
- ONIE firmware on the switch handles execution

Safety: MAAS implements strict vendor matching for ONIE images. If a switch
requests an image for a vendor that doesn't match any available ONIE images,
the boot request will fail explicitly. No fallback or generic images will be
served, as using the wrong vendor's installer can brick switches or cause
hardware damage.
"""

from functools import lru_cache
import re

from maascommon.osystem import BOOT_IMAGE_PURPOSE, OperatingSystem


class ONIEOS(OperatingSystem):
    """ONIE (Open Network Install Environment) operating system.

    ONIE is used by network switches from various vendors to enable
    network-based OS installation. This OS class handles ONIE images
    identified by vendor and version.

    Release naming format: vendor-version
    Examples:
        - mellanox-3.8.0
        - dell-2023.05
        - accton-2022.11
        - edge-core-2023.02

    Architecture support:
        - amd64 (x86_64 ONIE switches)
        - arm64 (ARMv8 ONIE switches)
        - armhf (ARMv7 ONIE switches)

    Subarchitecture mapping:
        The subarchitecture field maps to the vendor identifier from the
        DHCP vendor class identifier sent by ONIE switches.
        Examples:
            - amd64/dellemc (Dell EMC x86_64 switches)
            - amd64/mellanox (Mellanox x86_64 switches)
            - arm64/accton (Accton ARM64 switches)

    Image format:
        - Self-extracting binaries (most common)
        - Stored and served as-is by MAAS
        - No validation of image content
        - MAAS only verifies file integrity (SHA256) and authenticity (GPG)

    Critical Safety Feature:
        MAAS enforces strict vendor matching. If no exact vendor match exists
        for a boot request, the request fails. MAAS will NEVER serve a generic
        or different vendor's ONIE installer, as this can brick hardware.
    """

    name = "onie"
    title = "ONIE"

    # Supported ONIE vendors
    # This list represents major ONIE hardware vendors and is used for
    # validation and display formatting. Custom/unlisted vendors are also
    # supported if they follow the naming convention.
    SUPPORTED_VENDORS = frozenset(
        [
            "accton",
            "celestica",
            "dell",
            "dellemc",
            "emc",
            "edge-core",
            "mellanox",
            "nvidia",  # Mellanox is now NVIDIA
            "marvell",
            "quanta",
            "supermicro",
        ]
    )

    # Release name pattern: vendor-version
    # Vendor: lowercase alphanumeric with optional hyphens
    # Version: digits with dots (e.g., 3.8.0 or 2023.05)
    RELEASE_PATTERN = re.compile(
        r"^(?P<vendor>[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)-"
        r"(?P<version>\d+(?:\.\d+)*)$",
        re.IGNORECASE,
    )

    def get_boot_image_purposes(self) -> list[str]:
        """Gets the purpose of each boot image.

        ONIE images are self-extracting installers used exclusively for
        installation (XINSTALL). They cannot be used for commissioning
        or other purposes. MAAS serves these binaries as-is via HTTP/TFTP,
        and the ONIE firmware on the switch handles execution.

        Note: MAAS does not validate the image format or content. If the
        user declares it as ONIE, MAAS accepts and serves it as such,
        only verifying file integrity (SHA256) and authenticity (GPG).

        :return: List containing only XINSTALL purpose.
        """
        return [BOOT_IMAGE_PURPOSE.XINSTALL]

    def get_default_release(self) -> str | None:
        """Gets the default release to use when a release is not explicit.

        ONIE has no sensible default since the appropriate release depends
        on the specific vendor and model of the switch.

        :return: None (no default)
        """
        return None

    def get_supported_commissioning_releases(self) -> list[str]:
        """List operating system's supported commissioning releases.

        ONIE does not support commissioning - it's purely for installation.

        :return: Empty list.
        """
        return []

    def get_default_commissioning_release(self) -> str | None:
        """Return operating system's default commissioning release.

        ONIE does not support commissioning.

        :return: None
        """
        return None

    @lru_cache(maxsize=256)
    def parse_release(self, release: str) -> tuple[str, str] | None:
        """Parse a release string into vendor and version components.

        This method is cached to improve performance when parsing the same
        release strings repeatedly.

        :param release: Release string in format "vendor-version"
        :return: Tuple of (vendor, version) or None if invalid
        """
        match = self.RELEASE_PATTERN.match(release)
        if match:
            return match.group("vendor").lower(), match.group("version")
        return None

    def is_release_supported(self, release: str) -> bool:
        """Check if the given release follows expected naming convention.

        A release is considered valid if it matches the vendor-version pattern.
        Note: MAAS does not validate whether the actual image file is a valid
        ONIE installer - it trusts the user's declaration.

        :param release: Release identifier to check
        :return: True if release format matches expected pattern, False otherwise
        """
        parsed = self.parse_release(release)
        if not parsed:
            return False

        vendor, version = parsed
        # Accept any vendor that matches the pattern to allow for
        # custom/private ONIE builds from smaller vendors
        return bool(vendor and version)

    def get_release_title(self, release: str) -> str:
        """Return the title for the given release.

        Converts a release identifier like "mellanox-3.8.0" into a
        human-readable title like "Mellanox ONIE 3.8.0".

        :param release: Release identifier
        :return: Human-readable release title
        """
        parsed = self.parse_release(release)
        if not parsed:
            return release

        vendor, version = parsed

        # Capitalize vendor name properly
        vendor_title = self._format_vendor_name(vendor)

        return f"{vendor_title} ONIE {version}"

    def _format_vendor_name(self, vendor: str) -> str:
        """Format vendor name for display.

        :param vendor: Lowercase vendor identifier
        :return: Properly capitalized vendor name
        """
        # Special cases for vendor names
        vendor_names = {
            "dell": "Dell",
            "dellemc": "Dell EMC",
            "emc": "EMC",
            "mellanox": "Mellanox",
            "nvidia": "NVIDIA",
            "accton": "Accton",
            "marvell": "Marvell",
            "edge-core": "Edge-Core",
            "quanta": "Quanta",
            "celestica": "Celestica",
            "supermicro": "Supermicro",
        }
        return vendor_names.get(vendor.lower(), vendor.title())

    def get_supported_vendors(self) -> list[str]:
        """Return list of officially supported ONIE vendors.

        :return: List of vendor identifiers
        """
        return sorted(self.SUPPORTED_VENDORS)

    def get_vendor_from_release(self, release: str) -> str | None:
        """Extract vendor identifier from a release string.

        :param release: Release string in format "vendor-version"
        :return: Vendor identifier or None if invalid
        """
        parsed = self.parse_release(release)
        return parsed[0] if parsed else None

    def get_version_from_release(self, release: str) -> str | None:
        """Extract version from a release string.

        :param release: Release string in format "vendor-version"
        :return: Version string or None if invalid
        """
        parsed = self.parse_release(release)
        return parsed[1] if parsed else None

    def format_release_name(self, vendor: str, version: str) -> str:
        """Create a properly formatted release name from components.

        Note: This validates the naming format only. MAAS does not validate
        whether the actual image file is a valid ONIE installer.

        :param vendor: Vendor identifier (e.g., "mellanox")
        :param version: Version string (e.g., "3.8.0")
        :return: Formatted release name (e.g., "mellanox-3.8.0")
        :raises ValueError: If vendor or version format is invalid
        """
        # Normalize vendor to lowercase
        vendor = vendor.lower().strip()
        version = version.strip()

        if not vendor or not version:
            raise ValueError("Vendor and version must be non-empty")

        # Validate vendor format (alphanumeric with hyphens)
        if not re.match(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$", vendor):
            raise ValueError(
                f"Invalid vendor format: {vendor}. "
                "Must be lowercase alphanumeric with optional hyphens."
            )

        # Validate version format (digits with dots)
        if not re.match(r"^\d+(?:\.\d+)*$", version):
            raise ValueError(
                f"Invalid version format: {version}. "
                "Must be digits separated by dots (e.g., 3.8.0)."
            )

        release = f"{vendor}-{version}"

        # Double-check with our pattern
        if not self.RELEASE_PATTERN.match(release):
            raise ValueError(
                f"Formatted release does not match pattern: {release}"
            )

        return release

    def get_image_filetypes(self) -> dict[str, str]:
        """Return supported file types for ONIE images.

        ONIE images are typically self-extracting binaries, but they can
        also be provided as tar archives or raw disk images depending on
        the vendor.

        :return: Dictionary mapping filename patterns to file types
        """
        return self._get_image_filetypes(tgz=True, dd=True)
