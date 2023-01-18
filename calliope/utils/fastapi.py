from urllib.parse import urlparse

from fastapi import Request


def get_base_url(request: Request) -> str:
    uri = urlparse(str(request.url))
    return f"{uri.scheme}://{uri.netloc}/"
