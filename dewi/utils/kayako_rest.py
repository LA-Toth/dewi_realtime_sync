# Copyright 2017-2018 Laszlo Attila Toth
# Distributed under the terms of the GNU Lesser General Public License v3


import base64
import hashlib
import hmac
import random
import ssl
import typing
import urllib.parse
import urllib.request

from dewi.utils.xml import create_dict_from_xml_string


class AlreadyProcessed(RuntimeError):
    pass


class Host:
    def __init__(self, api_url: str, api_key: str, secret: str, unsafe_ssl: bool = False):
        self.api_url = api_url
        self.api_key = api_key
        self.secret = secret
        self.unsafe_ssl = unsafe_ssl


class Request:
    def __init__(self, host: Host, endpoint: str, params: typing.Optional[dict] = None):
        self.api_host = host
        self.salt = str(random.getrandbits(32))
        self.signature = self._generate_signature()
        self.endpoint = endpoint
        self.params = dict(params) if params else dict()
        self.url = self.api_host.api_url + '?e=' + self.endpoint
        self.params['apikey'] = self.api_host.api_key
        self.params['salt'] = self.salt
        self.params['signature'] = self.signature
        self._processed_once = False

    def _generate_signature(self):
        digest = hmac.new(
            self.api_host.secret.encode('UTF-8'),
            msg=self.salt.encode('UTF-8'), digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest)

    def _generate_url(self):
        self.url += '&' + self._prepare_parameters(self.params)

    def _prepare_parameters(self, params: typing.Optional[dict]):
        if not params:
            return dict()

        result = list()
        for key, value in params.items():
            if isinstance(value, (list, tuple)):
                for v in value:
                    result.append((key + '[]', v))
            else:
                result.append((key, value))

        return urllib.parse.urlencode(result)

    def _urlopen(self, *args, **kwargs):
        if self.api_host.unsafe_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            kwargs.update(dict(context=ctx))

        return urllib.request.urlopen(*args, **kwargs)

    def fetch(self):
        self._check_if_processed()
        self._generate_url()
        with self._urlopen(self.url) as response:
            return response.read()

    def put(self):
        self._check_if_processed()
        request = urllib.request.Request(self.url, method='PUT',
                                         data=self._prepare_parameters(self.params).encode('UTF-8'))
        with self._urlopen(request) as response:
            return response.read()

    def post(self):
        self._check_if_processed()
        request = urllib.request.Request(self.url, method='POST',
                                         data=self._prepare_parameters(self.params).encode('UTF-8'))
        with self._urlopen(request) as response:
            return response.read()

    def _check_if_processed(self):
        if self._processed_once:
            raise AlreadyProcessed()

        self._processed_once = True


class Connection:
    def __init__(self, host: Host):
        self._host = host
        self._salt = str(random.getrandbits(32))
        self._signature = self._generate_signature()
        self._params = dict()
        self._params['apikey'] = self._host.api_key
        self._params['salt'] = self._salt
        self._params['signature'] = self._signature

    @property
    def host(self):
        return self._host

    def _generate_signature(self):
        digest = hmac.new(
            self._host.secret.encode('UTF-8'),
            msg=self._salt.encode('UTF-8'), digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest)

    def _generate_url(self, endpoint: str):
        return f'{self._host.api_url}?e={endpoint}'

    def _generate_fetch_url(self, endpoint: str, params: typing.Optional[dict] = None):
        return f'{self._host.api_url}?e={endpoint}&' + self._prepare_parameters(params)

    def _prepare_parameters(self, params: typing.Optional[dict]) -> str:
        params_ = dict(params) if params else dict()
        params_.update(self._params)

        result = list()
        for key, value in params_.items():
            if isinstance(value, (list, tuple)):
                for v in value:
                    result.append((key + '[]', v))
            else:
                result.append((key, value))

        return urllib.parse.urlencode(result)

    def _urlopen(self, *args, **kwargs):
        if self._host.unsafe_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            kwargs.update(dict(context=ctx))

        return urllib.request.urlopen(*args, **kwargs)

    def fetch(self, endpoint: str, params: typing.Optional[dict] = None):
        url = self._generate_fetch_url(endpoint, params)
        with self._urlopen(url) as response:
            return response.read()

    def put(self, endpoint: str, params: typing.Optional[dict]):
        url = self._generate_url(endpoint)
        request = urllib.request.Request(url, method='PUT',
                                         data=self._prepare_parameters(params).encode('UTF-8'))
        with self._urlopen(request) as response:
            return response.read()

    def post(self, endpoint: str, params: typing.Optional[dict]):
        url = self._generate_url(endpoint)
        request = urllib.request.Request(url, method='POST',
                                         data=self._prepare_parameters(params).encode('UTF-8'))
        with self._urlopen(request) as response:
            return response.read()


def ensure_connection(host_or_connection: typing.Union[Host, Connection]) -> Connection:
    if isinstance(host_or_connection, Connection):
        return host_or_connection
    else:
        return Connection(host_or_connection)


def get_response_as_dict(h: Host, endpoint: str, params: typing.Optional[dict] = None):
    r = Request(h, endpoint, params)
    return create_dict_from_xml_string(r.fetch().decode('UTF-8'))
