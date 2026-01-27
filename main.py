import configparser
from playsound3 import playsound
import contextlib
import hashlib
import json
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from textual.app import App
from textual.widgets import Footer, Header, Static, Label, Button
import threading


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
            if 'error' in body:
                dump_json(body)
                raise SubsonicError(
                    '{} - {}'.format(body['error'], body['message'])
                )
            # To DEBUG
            # dump_json(body)
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
    Zerosonic().run()    

class MusicPlayer(Static):
    BINDINGS = [
        ('space', 'play_stop', 'Plays/stops current song'),
        ('right', 'next_track', 'Changes to the next track')
    ]

    # Server stuff
    config = read_config()
    server = Subsonic(url=config['url'], username=config['username'], password=config['password'])

    # Request a random queue
    request_songs = server.create_request("getRandomSongs", parameters={"size":500})
    request_songs_responses = server.make_request(request_songs)
    songs = request_songs_responses['subsonic-response']['randomSongs']['song']

    CURRENT_TRACK = 0
    playing_music = None


    def get_info(self):
        request_info = self.server.make_request(self.server.create_request("getSong", parameters={'id': self.songs[self.CURRENT_TRACK]['id']}))
        info = request_info['subsonic-response']['song']
        return Label("Now playing: {} - {}\n".format(info['title'], info['artist']), id="info-label")
    
    info_label = Label()

    def play_loop(self):
        playsound("https://music.afostyrio.com/rest/stream.view?id=h28XCV1a3AVu2J7TEAJmzl&u=afostyrio&p=Lui0703&v=1.13.0&c=AwesomeClientName&f=xml")
        # while self.CURRENT_TRACK <= 499:
        request_play = self.server.create_request("stream", parameters={'id': self.songs[self.CURRENT_TRACK]['id']})
        self.playing_music = playsound(request_play)
        # if self.playing_music == None:
        #     break
        self.CURRENT_TRACK += 1

    play_thread = threading.Thread(target=play_loop)

    def stop_music(self):
        try:
            self.playing_music.stop()
            self.playing_music = None
            self.play_thread.join()
        except:
            self.playing_music = None
    
    def action_play_stop(self):
        if self.playing_music is None:
            self.play_thread.start()
        else:
            self.stop_music()

    def action_next_track(self):
        self.stop_music()
        self.CURRENT_TRACK += 1
        info_label = self.get_info()
        self.play_thread.start()

    def compose(self):
        yield Button("← PREV", id='prev')
        info_label = self.get_info()
        yield info_label
        yield Button("SIG →", id='sig')

class Zerosonic(App):
    BINDINGS = [
        ('q', 'quit', 'Quits the app')
    ]

    CSS_PATH = 'zero-sonic.tcss'

    music_player = MusicPlayer()

    def compose(self):
        yield Header(show_clock=True)
        yield Footer()
        yield self.music_player

    def action_quit(self):
        self.music_player.stop_music()
        self.exit()


if __name__ == "__main__":
    main()