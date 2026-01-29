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
import time

class SubsonicError(Exception):
    """Subsonic API error occured"""

class Subsonic:
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
            try:
                body = json.loads(response.read())
                if 'error' in body:
                    dump_json(body)
                    raise SubsonicError(
                        '{} - {}'.format(body['error'], body['message'])
                    )
                # To DEBUG
                return body
            except:
                print("ERROR {}".format(response.read()))
                print(request)
                exit()
            # dump_json(body)

    @contextlib.contextmanager
    def _request(self, request):
        r = urllib.request.Request(request, headers={'User-Agent': 'Mozilla/6.0'}, method='GET')
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

class MusicPlayer:
    def __init__(self):
        config = read_config()
        self.server = Subsonic(url=config['url'], username=config['username'], password=config['password'])
        request_songs = self.server.create_request("getRandomSongs", parameters={"size":500})
        request_songs_responses = self.server.make_request(request_songs)

        self.songs = request_songs_responses['subsonic-response']['randomSongs']['song']    
        self.CURRENT_TRACK = 0
        self.music_playing = None
        self.playback_thread = threading.Thread(target=self.begin_playback_at_current_track)

    def get_current_track_info(self):
        request_info = self.server.make_request(self.server.create_request("getSong", parameters={'id': self.songs[self.CURRENT_TRACK]['id']}))
        info = request_info['subsonic-response']['song']
        return info['title'], info['artist']
    
    def play_song(self, song_id):
        request_play = self.server.create_request("stream", parameters={'id' : song_id})
        self.music_playing = playsound(request_play)

    def begin_playback_at_current_track(self):
        while self.CURRENT_TRACK <= 499:
            self.play_song(self.songs[self.CURRENT_TRACK]['id'])
            if self.music_playing is None:
                break
            self.CURRENT_TRACK += 1

    def stop_playback(self):
        try:
            self.music_playing.stop()
            self.music_playing = None
            self.playback_thread.join()
        except:
            print("STOP PLAYBACK ERROR")
            

class MusicWidget(Static):
    def __init__(self):
        super().__init__()
        self.music_player = MusicPlayer()

    BINDINGS = [
        ('space', 'play_stop', 'Plays/stops the random queue playback')
        # ('right', 'next_track', 'Changes to the next track')
    ]

    def action_play_stop(self):
        if self.music_player.music_playing is None:
            self.music_player.playback_thread.start()
        else:
            self.music_player.stop_playback()

    # def action_next_track(self):
    #     self.stop_music()
    #     self.CURRENT_TRACK[0] += 1
    #     info_label = self.get_info()
    #     self.play_thread.start()

    def compose(self):
        yield Button("← PREV", id='prev')
        info = self.music_player.get_current_track_info()
        info_label = Label("{} -- {}". format(*info), id="info-label")
        yield info_label
        yield Button("SIG →", id='sig')

class Zerosonic(App):
    BINDINGS = [
        ('q', 'quit', 'Quits the app')
    ]

    CSS_PATH = 'zero-sonic.tcss'

    music_widget = MusicWidget()

    def compose(self):
        yield Header(show_clock=True)
        yield Footer()
        yield self.music_widget

    def action_quit(self):
        self.music_widget.music_player.stop_playback()
        self.exit()


if __name__ == "__main__":
    mp = MusicPlayer()
    mp.playback_thread.start()
    print("now playing")
    time.sleep(5)
    mp.stop_playback()

    print("playback stopped")