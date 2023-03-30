from json import dumps
import json
from os import path
from urllib.parse import urljoin
import time
from requests import Session
from urllib3 import disable_warnings, exceptions

global in_game, isBanned, isPicked
in_game = False
isBanned = False
isPicked = False

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

    def banchamp(self, champion: str, backupchampion: str):
        global isBanned
        firstdata = {"championId": self.champions.get(champion), 'completed': True}
        backupdata = {"championId": self.champions.get(backupchampion), 'completed': True}
        print('banning')
        while not isBanned:
            get_session = self.request('get', '/lol-champ-select/v1/session')
            cs = get_session.json()
            cs2 = json.dumps(cs)
            cs3 = json.loads(cs2)
            cellId = cs3["localPlayerCellId"]
            for j in range(len(cs["actions"])):
                actions = cs["actions"][j]
                if not isinstance(actions, list):
                    continue
                for i in range(len(actions)):
                    if actions[i]["actorCellId"] == cellId:
                        actionType = actions[i]["type"]
                        if actionType == "ban":
                            if not actions[i]["completed"]:
                                if actions[i]["isInProgress"]:
                                    if not isBanned:
                                        for actions1 in cs['actions']:
                                            for action in actions1:
                                                if isinstance(action, dict) and action['championId'] == int(self.champions.get(champion)):
                                                    response = self.request('patch', f'/lol-champ-select/v1/session/actions/' + str(actions[i]["id"]), backupdata)
                                                    if response.status_code in [200, 204]:
                                                        print(f"{backupchampion} has been banned")
                                                        isBanned = True
                                                else:
                                                    response = self.request('patch', f'/lol-champ-select/v1/session/actions/' + str(actions[i]["id"]), firstdata)
                                                    if response.status_code in [200, 204]:
                                                        print(f"{champion} has been banned")
                                                        isBanned = True

                                                if isBanned:
                                                    return False
                                    else:
                                        return

    def pickchamp(self, champion: str, backupchampion: str):
        print('picking')
        global isPicked
        firstdata = {"championId": self.champions.get(champion), 'completed': True}
        backupdata = {"championId": self.champions.get(backupchampion), 'completed': True}
        while not isPicked:
            get_session = self.request('get', '/lol-champ-select/v1/session')
            cs = get_session.json()
            cs2 = json.dumps(cs)
            cs3 = json.loads(cs2)
            cellId = cs3["localPlayerCellId"]
            for j in range(len(cs["actions"])):
                actions = cs["actions"][j]
                if not isinstance(actions, list):
                    continue
                for i in range(len(actions)):
                    if actions[i]["actorCellId"] == cellId:
                        actionType = actions[i]["type"]
                        if actionType == "pick":
                            if not actions[i]["completed"]:
                                if actions[i]["isInProgress"]:
                                    if not isPicked:
                                        for actions1 in cs['actions']:
                                            for action in actions1:
                                                if isinstance(action, dict) and action['championId'] == int(self.champions.get(champion)):
                                                    response = self.request('patch', f'/lol-champ-select/v1/session/actions/' + str(actions[i]["id"]), backupdata)
                                                    if response.status_code in [200, 204]:
                                                        print(f"{backupchampion} has been picked")
                                                        if isinstance(action, dict) and action['championId'] == int(self.champions.get(backupchampion)) and action['completed'] == True:
                                                            isPicked = True
                                                else:
                                                    response = self.request('patch', f'/lol-champ-select/v1/session/actions/' + str(actions[i]["id"]), firstdata)
                                                    if response.status_code in [200, 204]:
                                                        print(f"{champion} has been picked")
                                                        if isinstance(action, dict) and action['championId'] == int(self.champions.get(champion)) and action['completed'] == True:
                                                            isPicked = True

                                                if isPicked:
                                                    return False

                                    else:
                                        return

if __name__ == '__main__':
    client = League('C:\Riot Games\League of Legends')
    while not client.is_playing():
        if client.is_selecting():
            if client.is_banning() and not isBanned:
                print('banning phase')
                time.sleep(1)
                client.banchamp('Malzahar', 'Vex')
            if client.is_picking() and not isPicked:
                print('picking phase')
                time.sleep(1)
                client.pickchamp('Sion', 'Pyke')
        elif client.is_found():
            isBanned = False
            isPicked = False
            client.accept()
            continue
        else:
            continue
