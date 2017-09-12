import animelog
import json
import requests

global_token = None
global_database = None
global_online = False
baseurl = r'https://anilist.co/api/{}'

client = {}

def get_client():
    global client
    with open('settings.json', 'r') as settingsfile:
        settings = json.load(settingsfile)
    client = settings["client"]
def clear_database():
    with open('database.json', 'w') as databasefile:
        json.dump({}, databasefile)

def load_global_database():
    global global_database
    if global_database is None:
        with open('database.json', 'r') as databasefile:
            global_database = json.load(databasefile)
    return

def save_global_database():
    with open('database.json', 'w') as databasefile:
        json.dump(global_database, databasefile)
    return

def get_token():
    params = dict(grant_type = 'client_credentials', 
            client_id = client['id'], client_secret = client['secret'])
    access = requests.post(baseurl.format('auth/access_token'), params = params)
    if access.ok:
        try:
            return access.json()['access_token']
        except ValueError as e:
            sys.stderr.write(access.text + '\n')
            raise e
    else:
        access.raise_for_status()
        raise RuntimeError("Could not connect to server!")

def get_global_token():
    global global_token
    if global_token is None:
        get_client()
        global_token = get_token()
def get_airing_data(id):
    get_global_token()
    return requests.get(baseurl.format(r'anime/{}/airing'.format(id)), params = {'access_token':global_token}).json()

def find_by_title(title):
    get_global_token()
    try:
        model = requests.get(baseurl.format(r'anime/search/{}'.format(title)), params = {'access_token':global_token}).json()
    except ValueError:
        return None
    if isinstance(model, list):
        return model[0]

def save_title_info(title):
    model = find_by_title(title)
    global_database[title] = {'exclude' : False}
    if model is not None:
        for key in ['airing_status', 'total_episodes']:
            if key in model:
                global_database[title][key] = model.get(key)
        try:
            raw_airing_data = get_airing_data(model['id'])
            if not isinstance(raw_airing_data, list):
                global_database[title]['airing_data'] = {int(key) : value for key, value in raw_airing_data.iteritems()} 
        except KeyError:
            pass
    else:
        global_database[title]['exclude'] = True

def minimize_database():
    global global_database
    load_global_database()
    log = animelog.get_log()
    global_database = dict(filter(lambda x : x[0] in log, global_database.iteritems()))
    save_global_database()
def full_update_database():
    load_global_database()
    log = animelog.get_log()
    for title, values in log.iteritems():
        if not global_database.get(title, {}).get('exclude', False) and not values.get('exclude', False):
            save_title_info(title)
    save_global_database()
def partial_update_database():
    load_global_database()
    log = animelog.get_log()
    for title, values in log.iteritems():
        if not values.get('exclude', False) and title not in global_database:
            save_title_info(title)
    save_global_database()
def single_update_database(title):
    load_global_database()
    save_title_info(title)
    save_global_database()
    
