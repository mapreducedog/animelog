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
        log the episode with the current watchers and play this episode. If the episode is the final episode of a title, and it exists in the anilist database, the show is automatically marked as finished. Note: This automatically marking as finished requires an internet connection
    
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
import sys
import re
import time
import itertools
import json
import os
import glob
import anilist
__autocompletion__ = True
__filter_by_airing__ = False

def successor(ep):
    if isinstance(ep, int):
        return ep + 1
    if hasattr(ep, '__iter__'):
        return ep[:-1] + [ep[-1] + 1]
def is_successor(ep, rep):
    if isinstance(ep, int):
        return rep == ep + 1
    else:
        return tuple(rep) == tuple(ep[:-1] + [ep[-1] + 1,]) or tuple(rep) == tuple(ep[:-2] + [ep[-2] + 1, 0])
def set_current_watchers(watchers):
    settings = get_settings()
    settings['current_watchers'] = list(watchers)
    write_settings(settings)
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
    return list(reduce(lambda old, new: old | set(new.keys()),get_log().values(), set()))

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
    shows = sorted(map(lambda x:x[0].replace(" ", "_") , currently_watching(watchers)))
    filetext = '''_animelog() 
{
    local cur prev shows longopts shortopts watchers
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"''' +  '''
    shows='{}' '''.format(" ".join(shows)) + '''
    longopts="{}"'''.format(" ".join(long_command_set))  + '''
    shortopts="{}"'''.format(" ".join(short_command_set)) + r'''
    watchers="{}"'''.format(" ".join(get_created_watchers())) + r'''
    if [[ ${cur} == --* ]]  ; then
        COMPREPLY=( $(compgen -W "${longopts}" -- ${cur}) )
        return 0
    elif [[ ${cur} = -* ]]; then  #first empty command
        COMPREPLY=( $(compgen -W "${shortopts}" -- ${cur}) )
        return 0
    elif [[ ${prev} == animelog ]] || [[ ${prev} == --simulate ]]; then
	#we supply a filename here
        return 0
    elif [[ ${prev} == -s ]] || [[ ${prev} == --set ]] ; then
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
        if (title, ep_nr) in anilist.get_total_episodes([title]):
            drop_title(title, watchers)
            add_to_finished(title, watchers)
            return
    except Exception as e: #REPLACE WITH requests.exceptions.ConnectionError!!!
        raise e
    add_to_log(title, ep_nr, watchers)

def add_to_log(title, ep_nr, watchers):
    log = get_log()
    if title not in log:
        log[title] = {}
    for watcher in watchers:
        if (watcher not in log[title]) or (log[title][watcher] < ep_nr):
            log[title][watcher] = ep_nr
    save_log(log)
    
def drop_title(title, watchers, save = False):
    log = get_log()
    if save:
        finish_log = get_finished()
    title, _ = parse_title(title, skip_number = True)
    if title in log:
        for watcher in set(watchers) & set(log[title].keys())   :
            del log[title][watcher]
            if save:
                finish_log[title] = finish_log.get(title, []) + [watcher]
        if not log[title]:
            del log[title]
        save_log(log)
        if save:
            save_finished(finish_log)
    

def drop_fuzzy(title, watchers, save = False):
    log = get_log()
    if save:
        finish_log = get_finished()
    title, _ = parse_title(title, skip_number = True)
    for series_title in log.copy():
        if title in series_title:
            for watcher in set(watchers) & set(log[series_title].keys()):
                del log[series_title][watcher]
                if save:
                    finish_log[series_title] = finish_log.get(series_title, []) + [watcher]
        if not log[series_title]:
            del log[series_title]
    if save:
        save_finished(finish_log)
    save_log(log)
                
def current_episode(title):
    log = get_log()
    title, _ = parse_title(title, skip_number = True)
    for series in log:
        if title in series:
            for watcher in log[series]:
                yield series, watcher, log[series][watcher]
def print_current_episode(title):
    for series,watcher,episode in current_episode(title):
        print(watcher, series,':',episode)
def get_next_airing(watchers):
    for result in anilist.get_next_airing_times(itertools.imap(lambda x:x[0], currently_watching(watchers))):
        yield result
        
def print_next_airing(watchers):
    for name, ep, date in get_next_airing(watchers):
        print(name, ep)
        print('\t', time.ctime(date))

def print_finished(watchers):   
    finished = get_finished()
    for title, watched_this in finished.iteritems():
        if set(watched_this) & set(watchers):
            print(title, watched_this)


def currently_watching(watchers):
    if not __filter_by_airing__:
        return currently_watching_unfiltered(watchers)
    return itertools.ifilter(lambda x: anilist.is_airing(x[0]), currently_watching_unfiltered(watchers))

def currently_watching_unfiltered(watchers):
    log = get_log()
    for title, watching_this in log.iteritems():
        if set(watchers) == set(watching_this):
            yield title, min(watching_this.values())



def print_currently_watching(watchers):
    for title, ep_nr in currently_watching(watchers):
        print(title, ' - ',ep_nr)
    #raw_input('press any key to close')
    
def check_new(watchers, as_next = False, check_for = None):
    prev_ep = dict(currently_watching(watchers))
    if check_for is not None:
        prev_ep = {x:prev_ep[x] for x in check_for}
    for title, ep_nr in anilist.get_latest_episode(prev_ep.keys()):
        if ep_nr > prev_ep[title]:
            if as_next:
                yield title, prev_ep[title] + 1
            else:
                yield title, ep_nr
def print_new(watchers, as_next = False):
    for title, ep_nr in check_new(watchers, as_next = as_next):
        print(title, ep_nr)
def play_title(title, watchers, play_next = False):
    '''finds the last or next episode of title for watchers and plays it'''
    ep = dict(currently_watching(watchers))[title]
    if hasattr(ep, '__iter__'):
        is_target = is_successor if play_next else lambda ep, rep: tuple(ep) == tuple(rep)
    else:
        is_target = is_successor if play_next else lambda ep, rep: ep == rep
    for filename in itertools.chain(glob.glob(os.path.join(get_video_path(), '*')), 
    glob.glob(os.path.join(get_video_path(), '*', '*'))): #for the video folder and direct subfolders
        if not os.path.isfile(filename):
            continue
        rtitle, rep = parse_title(filename)
        if rtitle == title and is_target(ep, rep):
            batfiledir = os.path.join(os.path.split(anilist.__file__)[0],'animelog.sh')
            wrapped_names = map(lambda instr: '"'+instr + '"',# if ' ' in instr else instr, 
								[batfiledir , filename])
            os.system('{} {}'.format(*wrapped_names))
            return (True, "Episode Played")
    else:
        return (False, "{} episode {} not found on drive".format(title, successor(ep) if play_next else ep))


def request_play_title(title, watchers, play_next = False):
    titles = filter(lambda this_title: title in this_title, 
                map(lambda title_watchers:title_watchers[0], 
            currently_watching(watchers)))
    if not titles:
        print('No series with "{}" found in watching database, did you finish it already?'.format(title))
        return False
    if len(titles) > 1:
        print('Multiple titles found for "{}"'.format(title))
        print("Searching for {}".format(", ".join(titles)))
    return_states = map(lambda this_title: 
                            (this_title,) + play_title(this_title, watchers, play_next = play_next), 
                        titles)
    
    #return_tup has the following format (this_title,was_played_bool, was_played_message)
    map(lambda return_tup: 
            print("Couldn't play an episode of {}:{}".format(return_tup[0], return_tup[2])),
            filter(lambda return_tup: not return_tup[1], return_states)) 
            
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
    '''animelog by MDP, logs your series, options:
    --[f]oo means type either -f or --foo
    
    '-i'                interactive mode, does not autoclose
    "series - 01.mkv"   adds that episode of that series to the log 
                        of the current watchers
                        if it does not have a numbering, 
                        it assumes its a movie and adds it to the finished
    
    
    [Watcher Manipulation]
    --[s]et john bert      sets current watchers to john and bert
    --[c]urrent            returns current watchers
    
    [Playing]
    --[p]lay_next title  plays next episode of title (for the current watchers)
    --play_[l]ast title    plays last played episode of title (for the current watchers)
    
    [Reporting]
    --[w]atching           get series current watchers are watching   
    --[w]atching john bert get series john and bert are both watching, 
                        but nobody else is 
    --[n]ext               get the next unwatched episode if it has aired, 
                        for all in -watching.
    --[n]ext john bert   same as above except for all in -watching john bert
    
    
    --new                gets the most recently aired not yet watched episode, 
                        for all in -watching
    --las[t] title         get most recently watched episode of title
    
    
    --finished           return the series current_watchers have finished

    --finished bill bob  returns the series bill and bob have finished
    --[a]iring             returns airtimes for next episode for current watchers
    --[a]iring bill bob 
    
    --[f]ilter          when used in combination of one of the above, only reports on shows that are currently airing
                        can used as animelog -fn to get --next --filter
    

    
    [Manual logging]
    --drop s1 s2 		drops these series from current_watchers
    --dropfuzzy series1  drops series with fuzzy matching        
    --finish s1 s2       adds these series to the finished 
                        list for the current watchers 
                        (and removes from the watching list), 
    --finishfuzzy s1 s2
                        matches fuzzily
    --simulate filename returns parsed filename
    
    
    note: the --new, --airing, --filter and --next require an internet connection 
    (as does the automatically finishing of series)
    the --play_next option does not require internet connection, it checks the harddrive
    
    '''
short_command_set = sorted(('-h', '-w', '-t','-s','-n','-i','-a','-p', '-f'))
long_command_set = sorted(('--help', '--watching', '--last', '--set', '--drop', '--dropfuzzy', '--finish', '--finishfuzzy', '--finished','--new', '--airing', '--play_next', '--play_last', '--simulate, --filter'))


def check_option(short_option, long_option):
    for option in ["-" + short_option, "--" + long_option]:
        if option in sys.argv:
            sys.argv.remove(option)
            return True
    for pos, string in enumerate(sys.argv[1:], 1):
        if string.startswith("--"):
            if string == "--" + long_option:
                sys.argv.pop(pos)
                return True
        elif string.startswith("-"):
            if short_option in string:
                sys.argv[pos] = string.replace(short_option, "")
                if sys.argv[pos] == '-':
                    sys.argv.pop(pos)
                return True
    return False


def main():
    global __filter_by_airing__
    #old_path = os.path.cwd()
    os.chdir(os.path.abspath(__file__).rpartition(os.path.sep)[0])

    if len(sys.argv) == 1 or sys.argv[1] in {'-h', '/?', ''}:
        print_short_help()
        return
    command = sys.argv[1]
    if command.startswith("-"):
        #-----------------------
        hold = check_option("i", "interactive")
        __filter_by_airing__ = check_option("f", "filter")
        command = sys.argv[1]
        if command in {'--help'}:
            print_long_help()
        elif command in {'-w', '--watching'}:
            print_currently_watching(sys.argv[2:] or get_current_watchers())
        elif command in {'--last', '-t'}:
            for title in sys.argv[2:]:
                print_current_episode(sys.argv[2])
        elif command in {'-s', '--set'}:
            set_current_watchers(set(sys.argv[2:]))
            update_autocompletion(get_current_watchers())
        elif '--drop' == command:
            current_watchers = get_current_watchers()
            for title in sys.argv[2:]:
                drop_title(title, current_watchers)
        elif '--dropfuzzy' == command:
            current_watchers = get_current_watchers()
            for title in sys.argv[2:]:  
                drop_fuzzy(title, current_watchers)
        elif '--finish' == command:
            current_watchers = get_current_watchers()
            for title in sys.argv[2:]:
                drop_title(title, current_watchers, save = True)
        elif '--finishfuzzy' == command:
            current_watchers = get_current_watchers()
            for title in sys.argv[2:]:
                drop_fuzzy(title, current_watchers, save = True)
        elif '--finished' == command:
            print_finished(sys.argv[2:] or  get_current_watchers())
        elif command in {'-c', '--current'}:
            print(get_current_watchers())
        elif '--new' == command:
            print_new(sys.argv[2:] or get_current_watchers())
        elif command in {'-n', '--next'}:
            print_new(sys.argv[2:] or get_current_watchers(), as_next = True)
        elif command in {'-a', '--airing'}:
            print_next_airing(sys.argv[2:] or get_current_watchers())
        elif command in {'-p', '--play_next'}:
            for title in sys.argv[2:]:
                request_play_title(title.replace("_"," "), get_current_watchers(), play_next = True)
        elif command in {'-l', '--play_last'}:
            for title in sys.argv[2:]:
                request_play_title(title.replace("_", " "), get_current_watchers(), play_next = False)
        elif command in {'--simulate',}:
            for filename in sys.argv[2:]:
                print(parse_title(filename))
        else:
            print("did not recognize the command:", ', '.join(sys.argv[1:]))
        if hold:
            raw_input("press any key")
        return
    watchers = get_current_watchers()
    log_anime(os.path.split(command)[-1], watchers)
    #os.chdir(old_path)
    #subprocess.call(["C:\Program Files\Combined Community Codec Pack\MPC\mpc-hc.exe", sys.argv[1]])
if __name__ == '__main__':
    main()
