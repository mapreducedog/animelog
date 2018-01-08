from __future__ import print_function

import requests
import time
import sys
import json

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
        
def get_total_episodes(titles):
    for title in titles:
        model = find_by_title(title)
        if model and "total_episodes" in model:
            yield title, model['total_episodes']

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

def is_airing(title):
    model = find_by_title(title)
    return model and model.get("airing_status") == 'currently airing'

def get_aired_episodes(title):
    def match(ep_date):
        return ep_date[1] <= curtime
        
    curtime = time.time()
    model = find_by_title(title, respect_exclude = False)
    if not model:
        return None
    airing_data = model.get('airing_data', {})
    if airing_data:
        return map(lambda ep_date: int(ep_date[0]), 
               filter(match, airing_data.iteritems())
                )
    elif model.get('airing_status', None) in {'finished airing', None} and 'total_episodes' in model:
        return range(1, model['total_episodes'] + 1)
    else:
        return None
    
def get_next_airing_time_single(title):
    curtime = time.time()
    def most_recent(indic):
        
        for ep_nr, date in sorted(indic.iteritems(), key = lambda x:x[-1]):
            if date > curtime:
                return int(ep_nr), date
    model = find_by_title(title)
    if not model or model.get('airing_status', '') not in {'currently airing', 'not yet aired'}:
        return None
    return most_recent(model.get('airing_data', {}))

def get_next_airing_times(titles):
    curtime = time.time()
    def most_recent(indic):
        for ep_nr, date in sorted(indic.iteritems(), key = lambda x:x[-1]):
            if date > curtime:
                return int(ep_nr), date
            
    for title, model in get_models(titles):
        if model.get('airing_status', '') not in  {'currently airing', 'not yet aired'} or not model.get('airing_data', False) :
            continue
        yield (title,) + most_recent(model['airing_data'])
        
def get_latest_episode(titles):
    curtime = time.time()
    for title in titles:
        model = find_by_title(title)
        if not model:
            continue
        if not {'id', 'airing_status'} & set(model): #returned a weird model
            continue
        if model.get('airing_status', '') == 'finished airing':
            yield title, model['total_episodes']
            continue
        airing_data = get_airing_data(model['id'])
        if airing_data:
            yield title, int(min(airing_data, key = lambda x: curtime - airing_data[x] if airing_data[x] < curtime else float('inf')))


    
            
def get_airing_data(id):
    return requests.get(baseurl.format(r'anime/{}/airing'.format(id)), params = {'access_token':global_token}).json()
    
def get_models(titles):
    for title in titles:
        model = find_by_title(title)
        if model:
            yield title, model
            
def find_by_title(title, respect_exclude = True):
    load_global_database()
    model = global_database.get(title, None)
    if model is not None and (not (respect_exclude and model.get('exclude', False))):
        return model
    return None
        
