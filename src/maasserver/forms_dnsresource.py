# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""DNSResource form."""

__all__ = [
    "DNSResourceForm",
]

from collections import Iterable

from django import forms
from maasserver.forms import MAASModelForm
from maasserver.models.dnsresource import DNSResource
from maasserver.models.domain import Domain
from maasserver.models.staticipaddress import StaticIPAddress
from netaddr import IPAddress
from netaddr.core import AddrFormatError


class DNSResourceForm(MAASModelForm):
    """DNSResource creation/edition form."""

    name = forms.CharField(label="Name")
    domain = forms.ModelChoiceField(
        label="Domain",
        queryset=Domain.objects.all())
    address_ttl = forms.IntegerField(
        required=False, min_value=0, max_value=(1 << 31) - 1,
        label="Time To Live (seconds)",
        help_text="For how long is the answer valid?")
    ip_addresses = forms.CharField(
        required=False, label="IP Addresseses",
        help_text="The IP (or list of IPs), either as IDs or as addresses")

    class Meta:
        model = DNSResource
        fields = (
            'name',
            'domain',
            'address_ttl',
            'ip_addresses',
            )

    def clean_ip(self, ipaddr):
        """Process one IP address (id or address) and return the id."""
        # If it's a simple number, then assume it's already an id.
        # If it's an IPAddress, then look up the id.
        # Otherwise, just return the input, which is likely to result in an
        # error later.
        if isinstance(ipaddr, int) or ipaddr.isdigit():
            return int(ipaddr)
        try:
            IPAddress(ipaddr)
        except (AddrFormatError, ValueError):
            # We have no idea, pass it on through and see what happens.
            return ipaddr
        ips = StaticIPAddress.objects.filter(ip=ipaddr)
        if ips.count() > 0:
            return ips.first().id
        return ipaddr

    def clean(self):
        cleaned_data = super().clean()
        if self.data.get('ip_addresses', '') != '':
            ip_addresses = self.data.get('ip_addresses')
            if isinstance(ip_addresses, str):
                ip_addresses = ip_addresses.split()
            elif isinstance(ip_addresses, Iterable):
                ip_addresses = list(ip_addresses)
            else:
                ip_addresses = [ip_addresses]
            cleaned_data['ip_addresses'] = [
                self.clean_ip(ipaddr) for ipaddr in ip_addresses]
        return cleaned_data
