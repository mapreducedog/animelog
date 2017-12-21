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
        json.dump(global_database, databasefile, indent = 1, sort_keys = True)
    return

def get_token():
    params = dict(grant_type = 'client_credentials', 
            client_id = client['id'], client_secret = client['secret'])
    access = requests.post(baseurl.format('auth/access_token'), params = params)
    if access.ok:
        try:
            return access.json()['access_token']
        except ValueError as e:
            animelog.errprint(access.text + '\n')
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

def get_closest_match(title, models):
    def scoring_function(model_title_tup):
        model_title = model_title_tup[1]
        words_model_title = set(model_title.split(" "))
        words_title = set(title.split(" "))
        return float(len(words_title & words_model_title)) / float(len((words_title | words_model_title))) 
        
    best_scoring = max
    #exact match
    for model in models:
        if title in {
            animelog.parse_title(model['title_romaji'], True)[0], 
            animelog.parse_title(model['title_english'], True)[0]
        }:
            return model
        
    matches = []
    all_parsed_titles = []
    for model in models:
        parsed_titles = map(lambda  title_lang: animelog.parse_title(model[title_lang], True)[0], ['title_english', 'title_romaji'])
        all_parsed_titles.extend([(model, parsed_title) for 
            parsed_title in parsed_titles])
        matching_titles = filter(lambda model_title: title in model_title, parsed_titles)
        if not matching_titles:
            continue
        else:
            matches.append((model, max(matching_titles, key = len)))
    
    if not matches:
        matches = all_parsed_titles
    
    return best_scoring(matches, key = scoring_function)[0]
    
            
    
    
def find_by_id(id):
    get_global_token()
    try:
        query_result = requests.get(baseurl.format(r'anime/{}'.format(id)), params = { 'access_token' : global_token }).json()
    except ValueError:
        animelog.errprint("No ID with value {}".format(id))
    return query_result

def find_by_title(title, strict = False):
    get_global_token()
    try:
        query_result = requests.get(baseurl.format(r'anime/search/{}'.format(title)), params = {'access_token':global_token}).json()
    except ValueError:
        return None
    if isinstance(query_result, list):
        if len(query_result) == 1:
            return query_result[0]
        models = query_result
        if strict:
            for model in models:
                if title.lower() in {model['title_romaji'].lower(), model['title_english'].lower()}:
                    return model
        target_model = get_closest_match(title, models)
        try:
            print("WARNING: multiple matches in remote database for {} : {}\n"
"assuming {}, add an alias to select other".format(title, 
        "\n\t- " + "\n\t- ".join(("{0[title_romaji]} (id:{0[id]})".format(model) for model in models)), "{0[title_romaji]} (id:{0[id]})".format(target_model)))
        except UnicodeEncodeError:
            print("WARNING: multiple matches in remote database for {}: but UnicodeEncodeError, "
                  "I love you too, macross delta".format(title))
        return models[0]
    else:
        
        return query_result

def save_title_info(title, alias = None):
    if alias is not None and alias.startswith("id:"):
        model = find_by_id(alias.split("id:")[-1].strip())
    else:
        model = find_by_title(alias or title, alias or None)
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

def set_episodes(title, episodes):
    global_database.setdefault(title, {})
    global_database[title]['exclude'] = True
    global_database[title]['total_episodes'] = episodes
    global_database[title]['airing_status'] = 'finished airing'

def set_episodes_stream(stream, episodes):
    load_global_database()
    for title, values in stream:
        set_episodes(title, episodes)
    save_global_database()
    
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
            save_title_info(title, values.get('alias', None))
    save_global_database()
def partial_update_database():
    load_global_database()
    log = animelog.get_log()
    for title, values in log.iteritems():
        if not values.get('exclude', False) and title not in global_database:
            save_title_info(title, values.get('alias', None))
    save_global_database()
def single_update_database(title):
    load_global_database()
    save_title_info(title)
    save_global_database()
    
