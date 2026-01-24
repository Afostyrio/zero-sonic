import configparser
from playsound3 import playsound
import libopensonic
import contextlib
import hashlib
import json
import random
import sys
import urllib.error
import urllib.parse
import urllib.request


class SubsonicError(Exception):
    """Subsonic API error occured"""

class Subsonic():
    API_VERSION = '1.15.0'
    CLIENT_NAME = 'zero-sonic'
    RESPONSE_FORMAT = 'json'

    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password

    def create_request(self, endpoint, parameters=None):
        salt, token = self.get_salt_and_token(self.password)
        request = f"{self.url}/rest/{endpoint}.view?u={self.username}&t={token}&s={salt}&v={self.API_VERSION}&c={self.CLIENT_NAME}&f={self.RESPONSE_FORMAT}"
        for parameter in parameters:
            request = request + f"&{parameter}={parameters[parameter]}"
        return request

    @staticmethod
    def get_salt_and_token(password):
        salt = random.randint(0, 100000)
        m = hashlib.md5('{}{}'.format(password, salt).encode())
        token = m.hexdigest()
        return salt, token

    def make_request(self, request):
        with self._request(request) as response:
            body = json.loads(response.read())
            dump_json(body)
            return body

    @contextlib.contextmanager
    def _request(self, request):
        r = urllib.request.Request(request, method='GET')
        try:
            with urllib.request.urlopen(r, timeout=60) as response:
                yield response
        except urllib.error.HTTPError as error:
            yield error.fp

def read_config():
    config = configparser.ConfigParser()
    config.read("config.conf")
    config = config['SERVER']
    return {
        'username': config['username'],
        'password': config['password'],
        'url': config['url']
    }

def dump_json(data):
    json.dump(data, sys.stdout, sort_keys=True, indent=2, ensure_ascii=False)
    sys.stdout.write('\n')

def main():
    config = read_config()
    server = Subsonic(url=config['url'], username=config['username'], password=config['password'])
    request = server.create_request("getRandomSongs", parameters={"size": 20})
    response = server.make_request(request=request)
    

if __name__ == "__main__":
    main()