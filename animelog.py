'''animelog by MDP, logs your series    
synopsis: 
    animelog [--simulate] <filename>
    animelog -[i][f](w|n|a) [<watcher>..]

    animelog [--interactive] ][--filter] 
        (--watching|--next|--airing|--new|--finished) [<watcher>...]
    animelog -[i]s <watcher>...
    animelog [--interactive] --set <watcher>...
    animelog -[i](p|l|t) (<title>|<partial-title>)..
    animelog -[--interactive] (--play_next| --play_last| --last|--dropfuzzy|--finishfuzzy) (<title>|<partial-title>)...
    animelog -[--interactive] (--drop|--finish) <title>    

usage:
    <filename>
        log the episode with the current watchers and play this episode. If the episode is the final episode of a title, and it exists in the database_reader database, the show is automatically marked as finished. Note: This automatically marking as finished requires an internet connection
    
    [Modifying Flags]
    -i, --interactive:
        this flag will prevent closing of the program
    -f, --filter
        this flag, when used with --watching, --next will cause these to only return titles that are currently airing. Note: This requires internet connection
    [Playing]
    -p (<title> | <partial-title>), --play_next (<title> | <partial-title>)..
        find and play the next episode 
    -l title, --play_la
    [Watchers]
    -s <watcher>..., --set <watcher>...
        set current watchers to supplied watchers
    -c, --current
        output current watchers
    
    [Reports]
    -w [<watcher> ...], --watching [<watcher> ...]
        output the titles and episodes number the supplied watchers or current watchers (if none supplied) are watching. 
    -n [<watcher> ..], --next [<watcher> ...]
        output the titles and the numbers of the next episode the supplied watchers or current watchers (if none supplied), if that episode number has aired. Note : This requires an internet connection
    --new [<watcher> ..]
        output titles and the latest episode number that has aired and not yet watched for the supplied watchers or current watchers (if none supplied). Note : This requires an internet connection
    -a [<watcher>..], --airing [<watcher>...]
        output the airing time and episode number for the next airing episode of each show the supplied watchers or current watchers (if none supplied) are watching. Note : This requires an internet connection
    
    -t (<title> | <partial-title>)..., --last (<title> | <partial-title>)...
        for each title supplied, output its watchers and their last watched episode number.
    
    [Manual logging]
        
        
    --drop <title>...
        remove the supplied title(s) from the current watchers
    --dropfuzzy (<title> | <partial-title>)....
        as above but matches fuzzily
    --finish <title>...
        remove the supplied titles from current watchers and adds it to their finished titles
    --finishfuzzy (<title> | <partial-title>)...
        as above but matches fuzzily
    
    --simulate <filename>....
        parse supplied filenames and ouput the result
        
        
FILES:
    /etc/bash_completion.d/animelog
        autocompletion is written here if enabled (set __autocompletion__ = True in animelog.py)
        in order for it to work, you have to allow writing this directory and alias animelog.sh to animelog
'''

from __future__ import print_function
from copy import deepcopy
import sys
import random
import re
import time
import itertools
import json
import os
import glob
import database_reader
import database_updater
__autocompletion__ = True
__filter_by_airing__ = False


def errprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def successor(ep):
    if isinstance(ep, int):
        return ep + 1
    if hasattr(ep, '__iter__'):
        return ep[:-1] + [ep[-1] + 1]
def set_current_watchers(watchers):
    settings = get_settings()
    settings['current_watchers'] = list(watchers)
    write_settings(settings)
    update_autocompletion(watchers)
def write_settings(data):
    with open('settings.json', 'w') as settingsfile:
        json.dump(data, settingsfile, indent = 1)
def get_settings():
    with open('settings.json', 'r') as settingsfile:
        settings = json.load(settingsfile)
    return settings
def get_video_path():
    return get_settings()['video_path']
def get_current_watchers():
    return get_settings()['current_watchers']
def parse_title(title, skip_number = False):
    def match_re(reg = None, ti_match = lambda ti, found: ti[:found.start()], 
        ep_match = lambda found: int(found.group(1))):
        found = re.search(reg, title)
        if not found:
            return None
        return ti_match(title, found).strip(), ep_match(found)
    title = os.path.split(title)[-1]
    title = title.lower()
    if '.' in title:
        title = title[:title.rfind('.')] #truncate the filename
        title = title.replace('.', ' ')

    title = title.replace('_',' ') # Bla_the_bla_-_07 >> Bla the bla - 07
    title = title.replace('dvd', '') #Who the f does this
	
    title = re.sub(r'\[[^\[]*?\]', '',title) #replace [subgroup] and [resolution]
    title = re.sub(r'\([^)]*?\)', '', title) #replace (resolution)
    title = re.sub(r'(v|V)\d+', '', title) #bla - 03v2 -> bla - 03
    if skip_number:
        return title, None

    match_patterns = [ #in order of most expected frequency
        {'reg': r'(\s*-+\s*)(\d+)','ep_match':lambda found: int(found.group(2))}, #match John the Great - 05
        {'reg':r's(\d+)e(\d+)', 'ep_match':lambda found: (int(found.group(1)), int(found.group(2)))}, #match John the Great s01e05
        {'reg':r'ep\s*(\d+)',},#match John the Great ep01
    ]
    
    for possible_match in itertools.imap(lambda kwargs: match_re(**kwargs), match_patterns):       
        if possible_match:
            return possible_match
    
    #this part wouldnt fit to neatly in "match_patterns"
    found = re.findall(r'\d+',title) #match John the great 05
    if not found:
        return title.strip(), None
    #Remove the resolution from  "John the great 05 720"
    found = filter(lambda x: x not in {'720','480','1080'}, found)
    if found:
        ep_nr = int(found[-1]) #In case of John the 5th 12
        title = title[:title.rfind(found[-1])]
        return title.strip(), ep_nr
    else: #the only number in the title was the resolution
        return title.strip(), None 

def get_created_watchers():
    return list(reduce(lambda old, new: old | set(new),(title_value['watchers'] for title_value in get_log().itervalues()), set()))

def get_log():
    with open('log.json', 'r') as fp:
        data = json.load(fp)
    return data

def save_log(data):
    with open('log.json', 'w') as fp:
        json.dump(data, fp, indent = 1)
    if __autocompletion__:
        update_autocompletion(get_current_watchers())
def update_autocompletion(watchers):
    shows = sorted(map(lambda x:x.replace(" ", "_") , currently_watching(watchers)))
    short_command_set, long_command_set = [filter(None, prep) + filter(None, stat) for prep, stat in zip(zip(*zip(*static_flags)[1]),zip(*zip(*preprocess_flags)[1]))] 
    short_command_set = [x for x in sorted(short_command_set)]
    long_command_set = ['--'+x for x in sorted(long_command_set)]
    
    filetext = '''_animelog() 
{
    select_successors() { 
        for letter in ${shortopts}
            do
                if [[ "${cur}" != *${letter}* ]]
                    then echo ${letter}
                fi
        done
        }
    local cur prev shows longopts shortopts watchers
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"''' +  '''
    shows="{}" '''.format(" ".join(shows)) + '''
    longopts="{}"'''.format(" ".join(long_command_set))  + '''
    shortopts="{}"'''.format(" ".join(short_command_set)) + r'''
    watchers="{}"'''.format(" ".join(get_created_watchers())) + r'''
    if [[ ${cur} == --* ]]  ; then
        COMPREPLY=( $(compgen -W "${longopts}" -- ${cur}) )
        return 0
    elif [[ ${cur} = -* ]]; then  #first empty command
        flatshortopts=$(select_successors)
        COMPREPLY=( $(compgen -W "${flatshortopts}" -P ${cur}) )
        #COMPREPLY=( $(compgen -W "${shortopts}" -- ${cur}) )
        return 0
    elif [[ ${prev} == animelog ]] || [[ ${prev} == --simulate ]]; then
	#we supply a filename here
        return 0
    elif [[ ${prev} == -!(-)*s* ]] || [[ ${prev} == --set ]] || [[ ${prev} == -!(-)*w* ]] || [[ ${prev} == --watchers ]] ; then
    	#supply a watcher
    	COMPREPLY=( $(compgen -W "${watchers}" -- ${cur}) )
   	return 0
    else
        COMPREPLY=( $(compgen -W "${shows}" -- ${cur}) )
        return 0 
    fi
}
complete -o default -F _animelog animelog
'''
    with open("/etc/bash_completion.d/animelog", "w") as outfile:
        outfile.write(filetext)

def get_finished():
    with open('finished.json', 'r') as fp:
        data = json.load(fp)
    return data
def save_finished(data):
    with open('finished.json', 'w') as fp:
        json.dump(data, fp, indent = 1)

def add_to_finished(title, watchers):
    finished = get_finished()
    finished[title] = list(set(watchers)|set(finished.get(title, [])))
    save_finished(finished)
def log_anime(title, watchers):
    title, ep_nr = parse_title(title)
    if ep_nr is None: #its a stand-alone film
        add_to_finished(title, watchers)
        return
    try:
        if (title, ep_nr) in database_reader.get_total_episodes([title]):
            drop_title(title, watchers)
            add_to_finished(title, watchers)
            return
    except Exception as e: #REPLACE WITH requests.exceptions.ConnectionError!!!
        raise e
    add_to_log(title, ep_nr, watchers)

def add_to_log(title, ep_nr, watchers):
    log = get_log()
    if title not in log:
        log[title] = {'watchers':{}}
    for watcher in watchers:
        if (watcher not in log[title]) or (log[title][watcher] < ep_nr):
            log[title]['watchers'][watcher] = ep_nr
    save_log(log)
    
    
def drop_title(title, watchers, save = False):
    log = get_log()
    if save:
        finish_log = get_finished()
    title, _ = parse_title(title, skip_number = True)
    if title in log:
        for watcher in set(watchers) & set(log[title]['watchers'])   :
            del log[title][watcher]
            if save:
                finish_log[title]['watchers'] = finish_log.get(title, {}).get('watchers', []) + [watcher]
        if not log[title]['watchers']:
            del log[title]
        save_log(log)
        if save:
            save_finished(finish_log)
    else:
        errprint("Couldn't {} {}, no exactly matching title found".format("finish" if save else "drop", title))

def drop_fuzzy(title, watchers, save = False):
    log = get_log()
    deleted_any = False
    if save:
        finish_log = get_finished()
    title, _ = parse_title(title, skip_number = True)
    for series_title in log.copy():
        if title in series_title:
            for watcher in set(watchers) & set(log[series_title]['watchers']):
                del log[series_title]['watchers'][watcher]
                deleted_any = True
                if save:
                    finish_log[series_title]['watchers'] = finish_log.get(series_title, {}).get('watchers', []) + [watcher]
        if not log[series_title]['watchers']:
            del log[series_title]
    if save:
        save_finished(finish_log)
    save_log(log)
    if not deleted_any:
        errprint("Couldn't {} {}, no matching title found".format("finish" if save else "drop", title))
def print_from_stream(stream, filterobj):
    for item in stream:
        title, value = item
        print(title, value)
def currently_watching(watchers):
    filterobj = deepcopy(__filter_settings__)
    filterobj['filter_by_watchers'] = watchers
    return (x[0] for x in get_logstream(filterobj))
    

def get_logstream(filterobj, this_stream = None):
    if this_stream is None:
        this_stream = get_unfiltered_logstream(filterobj)
 
    stream = this_stream
    for keyname, function in key_func_pairs:
        if filterobj[keyname]:
            stream = function(stream, filterobj)
    #stream = reduce((lambda stream, key_func: check_stream(key_func[1](stream, filterobj), key_func[0]) if filterobj[key_func[0]] else stream),key_func_pairs, this_stream)
           
    return stream

def check_stream(stream, name):
    print(name)
    for item in stream:
        print(item)
        yield item
    
def filter_by_lucky(stream, filterobj):
    stream = list(stream)
    found_titles = filter(lambda x: x[1].get('filename', ''), stream)
    if not found_titles:
        return stream
    your_show_today = random.choice(found_titles)
    return [your_show_today,]

def get_unfiltered_logstream(filterobj):
    log = get_log()
    for item in log.iteritems():
        yield item
        
def filter_by_titles(stream, filterobj):
    if filterobj["filter_by_titles_strict"]:
        return itertools.ifilter(lambda x:x[0] in map(lambda x : parse_title(x, skip_number = True)[0],filterobj["filter_by_titles"]), stream)
    else:
        return itertools.ifilter(lambda x:any((True for title in filterobj["filter_by_titles"] if parse_title(title, skip_number = True)[0] in x[0])), stream)
def filter_by_watchers(stream, filterobj):
    def matches(x):
        return set(x[1]['watchers']) == set(filterobj["filter_by_watchers"])
    return itertools.ifilter(matches, stream)
def filter_by_airing(stream, filterobj):
    return itertools.ifilter(lambda x: database_reader.is_airing(x[0]), stream)
def stream_exclude_watchers(stream, filterobj):
    for item in stream:
        title, watchers_eps = item
        yield (title, {watcher:ep for watcher, ep in watchers_eps if watcher not in filterobj["exclude_watchers"]})

def filter_by_unwatched_aired(stream, filterobj):
    for title, values in stream:
        aired_eps = database_reader.get_aired_episodes(title)
        try:
            if aired_eps and  (max(aired_eps) > min(values['watchers'].values())): #is in database_reader and (aired_ep1, aired_ep2 ...) > min((title, {watcher:ep_nr, ... })[1].values()))
                yield (title, values)
        except ValueError:
            print("error on", item)
def stream_find_next_airdate(stream, filterobj):
    for title, values in stream:
        airdate = database_reader.get_next_airing_time_single(title)
        if airdate:
            values['airing'] = (airdate[0], time.ctime(airdate[1]))
            yield (title, values)
            
def stream_as_successor(stream, filterobj):
    for item in stream:
        title, watchers = item[0], item[1]['watchers']
        right_item = item[1].copy()
        right_item['watchers'] = {watcher: successor(episode) for watcher, episode in watchers.iteritems()}
        yield (title, right_item)
def stream_as_latest_unwatched(stream, filterobj):
    for item in stream:
        title, watchers_eps = item[0], item[1]['watchers']
        aired_eps = database_reader.get_aired_episodes(title)
        if aired_eps:
            latest = max(aired_eps)
            if latest > min(watchers_eps.values()):
                right_item = item[1].copy()
                right_item['watchers'] = {watcher : latest for watcher in watchers_eps.iteritems()}
                yield (title, right_item)
                
def stream_find_file(stream, filterobj):
    for title, values in stream:
        episode = min(values['watchers'].values())
        if hasattr(episode, '__iter__'):
            episode = tuple(episode)
        for filename in itertools.chain(glob.glob(os.path.join(get_video_path(), '*')), 
            glob.glob(os.path.join(get_video_path(), '*', '*'))):
            if not os.path.isfile(filename):
                continue
            rtitle, repisode = parse_title(filename)
            if rtitle == title and repisode == episode:
                values['filename'] = '"' + filename + '"'
                yield(title, values)
                break
        else:
            values['filename'] = ''
            yield (title, values)
def stream_as_title_epnr(stream, filterobj):
    for item in stream:
        yield item[0], min(item[1]['watchers'].values())
def play_from_stream(stream, filterobj):
    batfiledir = '"' + os.path.join(os.path.split(database_reader.__file__)[0],'animelog.sh') + '"'
    played_any = False
    for title, values in stream:
        played_any = True
        if values.get('filename'):
            os.system('{} {}'.format(batfiledir, values['filename']))
        else:
            errprint("{} episode {} not found on drive".format(title, min(values['watchers'].values())))
    if not played_any:
        errprint("Did not find anything to play")
def play_single_item(title, episode):
    if hasattr(episode, '__iter__'):
        episode = tuple(episode)
    for filename in itertools.chain(glob.glob(os.path.join(get_video_path(), '*')), 
        glob.glob(os.path.join(get_video_path(), '*', '*'))):
        if not os.path.isfile(filename):
            continue
        rtitle, repisode = parse_title(filename)
        if rtitle == title and repisode == episode:
            batfiledir = os.path.join(os.path.split(database_reader.__file__)[0],'animelog.sh')
            wrapped_names = map(lambda instr: '"'+instr + '"',# if ' ' in instr else instr, 
								[batfiledir , filename])
            os.system('{} {}'.format(*wrapped_names))
            return (True, "Episode Played")
    else:
        return (False, "{} episode {} not found on drive".format(title, episode))

def print_short_help():
    print('''animelog by MDP, logs your series, options:
    -f, --filter            flag: output only currently airing anime
    -i, --interactive       keep prompt open.
    
    -s <watcher>..., --set <watcher>...  set current watchers
    -c, --current           output current watchers
    
    -p <title>.., --play_next <title>..   play next episode for titles
    -l, --last,             play most recently watched episode of title
    
    -w <watcher>.., --watching <watcher>... 
                    output titles that are being watched
    
    --help          print long help
    
    ''')


def print_long_help():
    print(__doc__)
 

def check_option(short_option, long_option, return_arguments = False):
    if not short_option:
        short_option = '_______________________________________'
    for option in ["-" + short_option,
                   "--" + long_option]:
        if option in sys.argv:
            pos = sys.argv.index(option)
            if return_arguments:
                return list(itertools.takewhile(lambda x: not x.startswith("-"), sys.argv[pos + 1:]))
            else:
                return True
    for pos, string in enumerate(sys.argv[1:], 1):
        if string.startswith("-") and not string.startswith('--'):
            if short_option in string:
                if return_arguments:
                    return list(itertools.takewhile(lambda x: not x.startswith("-"), sys.argv[pos + 1:]))
                return True
    return [] if return_arguments else False


def main():
    #old_path = os.path.cwd()
    os.chdir(os.path.abspath(__file__).rpartition(os.path.sep)[0])
    command = sys.argv[1]
    
    if len(sys.argv) == 1 or sys.argv[-1] in {'-h', '/?', ''}:
        print_short_help()
        return
    if sys.argv[-1] in {'--help', }:
        print_long_help()
        return
    if not any(map(lambda x:x.startswith('-'), sys.argv[1:])):
        watchers = get_current_watchers()
        log_anime(os.path.split(command)[-1], watchers)
        return
    
    filterobj = __filter_settings__
    #action_flags = [(lambda x: print_from_stream(stream), ("r", "report"), False)]
    for action, options,arguments in preprocess_flags:
        return_value = check_option(options[0], options[1], arguments)
        if return_value:
            action(return_value)
    for key, options in static_flags:
        if not filterobj[key]:
            filterobj[key] = check_option(options[0], options[1], isinstance(filterobj[key], list))
    
    if any(filterobj.values()):
        filterobj['report'] = not filterobj['play']
        stream = get_logstream(filterobj)
    #watchers = get_current_watchers()
    #log_anime(os.path.split(command)[-1], watchers)
    #os.chdir(old_path)
    #subprocess.call(["C:\Program Files\Combined Community Codec Pack\MPC\mpc-hc.exe", sys.argv[1]])

__filter_settings__ =  {   "hold":False,
                    "filter_by_airing":False, 
                    "filter_by_unwatched_aired": False, 
                    "filter_by_titles": [],
                    "filter_by_titles_strict": False,
                    "filter_by_watchers": [],
                    "as_successor": False,
                    "as_latest_unwatched":False,
                    "as_title_epnr": False,
                    "exclude_watchers": [],
                    "lucky":False,
                    "play": False,
                    "report":False,
                    "next_airdate":False
                }

    
preprocess_flags = [
        (set_current_watchers, ('s', 'set'), True),
        ((lambda x: __filter_settings__.__setitem__("filter_by_watchers", get_current_watchers())),
        ("c", "current"), False),
        ((lambda x: database_updater.partial_update_database()), ('U', 'update'), False),
        ((lambda x: database_updater.full_update_database()), ('', 'full-update'), False),
        ((lambda x: database_updater.minimize_database()), ('', 'minimize'), False),
        ((lambda userin: [drop_title(title, get_current_watchers()) for title in userin]), ('', 'drop'), True),
        ((lambda userin: [drop_fuzzy(title, get_current_watchers()) for title in userin]), ('', 'dropfuzzy'),True),
        ((lambda userin: [drop_title(title, get_current_watchers(), save = True) for title in userin]), ('', 'finish'),True)
        ]
        #((lambda x: filterobj.__setitem__("filter_by_titles", x)), ('', 'drop'),True)


static_flags =  [("hold", ("i", "interactive")), 
                     ("filter_by_airing", ('a', 'airing')),
                    ("filter_by_unwatched_aired", ('u',  'unwatched')),
                    ('filter_by_titles', ('t', 'title')), 
                    ('filter_by_watchers',( 'w', 'watchers')),
                    ('as_successor',('n', 'next')),
                    ("as_latest_unwatched", ('l', 'latest')),
                    ("as_title_epnr", ('e', 'episode')),
                    ("play", ("p", "play")),
                    ("lucky",("L", "lucky")),
                    ("next_airdate",("d", "date"))
                ]

key_func_pairs = [("filter_by_titles", filter_by_titles),
                       ("exclude_watchers", stream_exclude_watchers),
                       ("filter_by_watchers", filter_by_watchers),
                       ("filter_by_airing", filter_by_airing),
                       ("filter_by_unwatched_aired", filter_by_unwatched_aired),
                       ("as_successor", stream_as_successor),
                       ("as_latest_unwatched", stream_as_latest_unwatched),
                       ("as_title_epnr",stream_as_title_epnr),
                       ("next_airdate", stream_find_next_airdate),
                       ("play", stream_find_file),
                       ("lucky", filter_by_lucky),
                       ("play", play_from_stream),
                       ("report", print_from_stream)
                     ]

if __name__ == '__main__':
    main()
