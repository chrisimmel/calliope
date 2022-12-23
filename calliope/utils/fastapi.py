from urllib.parse import urlparse

from fastapi import Request


def get_domain(request: Request) -> str:
    uri = urlparse(str(request.url))
    return f"{uri.scheme}://{uri.netloc}/"
