# Copyright 2024-2025 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

CONFIGURE_DNS_WORKFLOW_NAME = "configure-dns"


class InvalidDNSUpdateError(Exception):
    pass
