from __future__ import annotations

from urllib.parse import urlparse


_PLACEHOLDER_HOSTS = {
    "example.com",
    "example.org",
    "example.net",
    "example-energy-gov.cn",
}


def is_placeholder_url(url: str | None) -> bool:
    if not url:
        return True
    host = (urlparse(url).hostname or "").lower()
    return host in _PLACEHOLDER_HOSTS or host.endswith(".example.com")

