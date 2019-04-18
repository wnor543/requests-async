import asyncio
import io
import os
import ssl
import typing
from http.client import _encode
from urllib.parse import urlparse

import h11
import requests
import urllib3

import httpcore


class HTTPAdapter:
    def __init__(self):
        self.pool = httpcore.ConnectionPool()

    async def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ) -> requests.Response:

        method = request.method
        url = request.url
        headers = [(_encode(k), _encode(v)) for k, v in request.headers.items()]
        if not request.body:
            body = b''
        elif isinstance(request.body, str):
            body = _encode(request.body)
        else:
            body = request.body

        response = await self.pool.request(method, url, headers=headers, body=body, stream=stream)

        return self.build_response(request, response)

    async def close(self):
        await self.pool.close()

    def build_response(self, req, resp):
        """Builds a :class:`Response <requests.Response>` object from an httpcore
        response. This should not be called from user code, and is only exposed
        for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`
        :param req: The :class:`PreparedRequest <PreparedRequest>` used to generate the response.
        :param resp: The urllib3 response object.
        :rtype: requests.Response
        """
        response = requests.models.Response()

        # Fallback to None if there's no status_code, for whatever reason.
        response.status_code = resp.status_code

        # Make headers case-insensitive.
        response.headers = requests.structures.CaseInsensitiveDict([
            (k.decode('latin1'), v.decode('latin1')) for k, v in resp.headers
        ])

        # Set encoding.
        response.encoding = requests.utils.get_encoding_from_headers(response.headers)
        response._content = resp.body
        response.reason = resp.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        requests.cookies.extract_cookies_to_jar(response.cookies, req, resp)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response
