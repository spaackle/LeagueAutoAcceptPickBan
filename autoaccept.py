from json import dumps
import json
from os import path
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import time
from requests import Session
from urllib3 import disable_warnings, exceptions

global in_game, banning, picking
in_game = False
banning = False
picking = False

class League:
    def __init__(self, league: str):
        with open('champions.txt', 'rb') as file:
            self.champions = {(r := i.split(':'))[0]: r[1] for i in file.read().decode().splitlines()}
        with open(path.join(league, 'lockfile'), 'r', encoding='UTF-8') as lockfile:
            port, self.__password, protocol = lockfile.read().split(':')[2:]
        self.base_url = f'{protocol}://127.0.0.1:{port}/'
        self.__session = Session()
        self.__session.auth = ('riot', self.__password)
        self.__session.verify = False
        disable_warnings(exceptions.InsecureRequestWarning)
        self.summoner = self.request('get', '/lol-summoner/v1/current-summoner').json()

    def request(self, method, endpoint, data=None):
        return self.__session.request(method, urljoin(self.base_url, endpoint), data=dumps(data))

    def is_found(self):
        return self.request('get', '/lol-lobby/v2/lobby/matchmaking/search-state').json().get('searchState') == 'Found'

    def is_searching(self):
        value = self.request('get', '/lol-lobby/v2/lobby/matchmaking/search-state').json().get('searchState')
        return value == 'Searching'

    def is_selecting(self):
        return self.request('get', '/lol-champ-select/v1/session').json().get('actions')

    def is_banning(self):
        req_phase = self.request('get', '/lol-champ-select/v1/session')
        cs = req_phase.json()
        for actions in cs['actions']:
            for action in actions:
                if isinstance(action, dict) and action['type'] == "ban":
                    if action['isInProgress']:
                        return True
                    else:
                        return False
        return False

    def is_picking(self):
        req_phase = self.request('get', '/lol-champ-select/v1/session')
        cs = req_phase.json()
        for actions in cs['actions']:
            for action in actions:
                if isinstance(action, dict) and action['type'] == "pick":
                    if action['isInProgress']:
                        return True
                    else:
                        return False
        return False

    def is_playing(self):
        global in_game
        while not in_game:
            try:
                request_game_data = requests.get('/liveclientdata/allgamedata', verify=False)
                game_data = request_game_data.json()['gameData']['gameTime']
                if game_data > 0 and not in_game:
                    return True
                    in_game = True
            except (Exception,):
                return False

    def accept(self):
        self.request('post', '/lol-matchmaking/v1/ready-check/accept')

    def banchamp(self, champion: str):
        req_phase = self.request('get', '/lol-champ-select/v1/session')
        data = {"championId": self.champions.get(champion), 'completed': True}
        isBanned = False
        cs = req_phase.json()
        cs2 = json.dumps(cs)
        rootCSelect = json.loads(cs2)
        localPlayerCellId = rootCSelect["localPlayerCellId"]
        cellId = rootCSelect["localPlayerCellId"]
        for j in range(len(cs["actions"])):
            actions = cs["actions"][j]
            if not isinstance(actions, list):
                continue
            for i in range(len(actions)):
                if actions[i]["actorCellId"] == cellId:
                    actionType = actions[i]["type"]
                    if actionType == "ban":
                        if not actions[i]["completed"]:
                            if not isBanned:
                                response = self.request('patch', f'/lol-champ-select/v1/session/actions/' + str(actions[i]["id"]), data)
                                if response.status_code not in (200, 204):
                                    print(f"Error selecting champion: {response.status_code} - {response.text}")
                            else:
                                isBanned = True

    def pickchamp(self, champion: str):
        req_phase = self.request('get', '/lol-champ-select/v1/session')
        data = {"championId": self.champions.get(champion), 'completed': True}
        isPicked = False
        cs = req_phase.json()
        cs2 = json.dumps(cs)
        rootCSelect = json.loads(cs2)
        cellId = rootCSelect["localPlayerCellId"]
        for j in range(len(cs["actions"])):
            actions = cs["actions"][j]
            if not isinstance(actions, list):
                continue
            for i in range(len(actions)):
                if actions[i]["actorCellId"] == cellId:
                    actionType = actions[i]["type"]
                    if actionType == "pick":
                        if not actions[i]["completed"]:
                            if not isPicked:
                                response = self.request('patch', f'/lol-champ-select/v1/session/actions/' + str(actions[i]["id"]), data)
                                if response.status_code not in (200, 204):
                                    print(f"Error selecting champion: {response.status_code} - {response.text}")
                            else:
                                isPicked = True

if __name__ == '__main__':
    client = League('C:\Riot Games\League of Legends')
    while not client.is_playing():
        if client.is_selecting():
            if client.is_banning():
                print('banning phase')
                time.sleep(1)
                client.banchamp('Vex')
            elif client.is_picking():
                print('picking phase')
                time.sleep(1)
                client.pickchamp('Yuumi')
        elif client.is_found():
            client.accept()
            continue
        else:
            continue
