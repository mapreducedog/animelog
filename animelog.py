from __future__ import print_function
#builtin
from copy import deepcopy
import sys
import re
import itertools
import json
import os

#own
import database_reader
import database_updater
from streamhandler import Stream
from streamfilter import Filter
import user_interface

__autocompletion__ = True
__filter_by_airing__ = False


def errprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def set_current_watchers(watchers):
    '''set the current watchers to the supplied watchers'''
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
    title = os.path.basename(title)
    title = title.lower()
    #replace non-ascii characters by space
    #title = title.decode('utf-8','replace').encode('ascii', 'replace').replace('?',' ')
    if isinstance(title, unicode):
        title = title.encode('ascii', 'replace').replace('?',' ')
    else:
        title = title.decode('ascii', 'replace')
        title = re.sub(u'\ufffd+', ' ',title)

    if os.path.splitext(title)[-1] == '.part':
        title = os.path.splitext(title)[0]
    if '.' in title:
        title = os.path.splitext(title)[0] #truncate the filename
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
        {'reg':r'ep\s*(\d+)',},#match John the Great ep01,
        {'reg':r'e(\d+)', }, #John the Great e01
        {'reg':r'(\d+)x(\d+)', 'ep_match':lambda found: (int(found.group(1)), int(found.group(2)))} #John the Great 1x03
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

def assert_correct_arguments():
    short_command_set, long_command_set = [filter(None, prep) + filter(None, stat) for prep, stat in zip(zip(*zip(*user_interface.static_flags)[1]),
        zip(*zip(*
                 (user_interface.preprocess_flags +  user_interface.postprocess_flags)
                 )[1]))]

    long_args = map(lambda x: x[2:], filter(lambda x: x.startswith("--"), sys.argv) )
    short_args = map(lambda x: x[1:],filter(lambda x:x.startswith("-") and not x.startswith("--"), sys.argv))
    short_args = "".join(short_args)
    unmatched_args = list(filter(lambda x: x not in short_command_set, short_args)) + filter(lambda x: x not in long_command_set, long_args)
    if unmatched_args:
        raise RuntimeError("Supplied invalid argument{}: ".format("s" if len(unmatched_args) > 1 else "") + ", ".join(unmatched_args))





def update_autocompletion(watchers):
    shows = sorted(map(lambda x:x.replace(" ", "_") , currently_watching(watchers)))
    short_command_set, long_command_set = [filter(None, prep) + filter(None, stat) for prep, stat in zip(zip(*zip(*user_interface.static_flags)[1]),
        zip(*zip(*
                 (user_interface.preprocess_flags +  user_interface.postprocess_flags)
                 )[1]))]
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
    elif  [[ ${prev} == -s* ]] || [[ ${prev} == -[^-]*s* ]] ||  [[ ${prev} == --set ]] || [[ ${prev} == -w ]] || [[ ${prev} == -^[-]*w* ]] || [[ ${prev} == --watchers ]] ; then
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
    new_watchers = set(watchers)|set(finished.get(title, {}).get('watchers',[]))
    finished.setdefault(title, {})
    finished[title]["watchers"] = list(new_watchers)
    save_finished(finished)


def add_alias_stream(stream, alias):
    alias = " ".join(alias)
    modify_alias = remove_alias if not alias else lambda title : add_alias(title, alias)
    for title, values in stream:
        modify_alias(title)


def add_alias(title, alias):
    log = get_log()
    title, _ = parse_title(title, True)
    if title in log:
        log[title]['alias'] = alias
        save_log(log)
        return
    for showtitle in log:
        if title in showtitle:
            log[showtitle]['alias'] = alias
            save_log(log)
def remove_alias(title):
    log = get_log()
    title, _ = parse_title(title, True)
    if title in log:
        del log[title]['alias']
        save_log(log)
        return
    for showtitle in log:
        if title in showtitle:
            del log[showtitle]['alias']
            save_log(log)
def log_anime(title, watchers):
    title, ep_nr = parse_title(title)
    __log_anime__(title, ep_nr, watchers)

def __log_anime__(title, ep_nr, watchers):
    if ep_nr is None: #its a stand-alone film
        add_to_finished(title, watchers)
        return
    try:
        if (title, ep_nr) in database_reader.get_total_episodes([title]):
            drop_title(title, watchers, save = True)
            #add_to_finished(title, watchers) TODO: something went wrong here, resulting in not being added in finihsed,
            return
    except Exception as e: #REPLACE WITH requests.exceptions.ConnectionError!!!
        raise e
    add_to_log(title, ep_nr, watchers)

def log_anime_from_stream(stream):
    for item in stream:
        title, value = item
        __log_anime__(title, min(value['watchers'].values()), value['watchers'].keys())

def add_to_log(title, ep_nr, watchers):
    log = get_log()
    if title not in log:
        log[title] = {'watchers':{}}
    for watcher in watchers:
        if (watcher not in log[title]['watchers']) or (log[title]['watchers'][watcher] < ep_nr):
            log[title]['watchers'][watcher] = ep_nr
    save_log(log)


def drop_title(title, watchers, save = False):
    log = get_log()
    if save:
        finish_log = get_finished()
    title, _ = parse_title(title, skip_number = True)
    if title in log:
        for watcher in set(watchers) & set(log[title]['watchers'])   :
            del log[title]['watchers'][watcher]
            if save:
                finish_log.setdefault(title, {'watchers':[]})
                finish_log[title]['watchers'] = finish_log[title].get('watchers', []) + [watcher]
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
                    finish_log.setdefault(series_title, {'watchers':[]})
                    finish_log[series_title]['watchers'] = finish_log.get(series_title, {}).get('watchers', []) + [watcher]
        if not log[series_title]['watchers']:
            del log[series_title]
    if save:
        save_finished(finish_log)
    save_log(log)
    if not deleted_any:
        errprint("Couldn't {} {}, no matching title found".format("finish" if save else "drop", title))

def finish_from_stream(stream):
    drop_from_stream(stream, save = True)

def drop_from_stream(stream, save = False):
    deleted_any = False
    log = get_log()
    watchers = get_current_watchers()
    if save:
        finish_log = get_finished()
    for item in stream:
        title, values = item
        if save:
            finish_log.setdefault(title, {'watchers':[]})
        for watcher in set(watchers) & set(log[title]['watchers']):
            deleted_any = True
            del log[title]['watchers'][watcher]
            if save:
                finish_log[title]['watchers'] = list(set(finish_log.get(title, {}).get('watchers', []) + [watcher]))
        if not log[title]['watchers']:
            del log[title]

    if save:
        save_finished(finish_log)
    save_log(log)

    if not deleted_any:
        errprint("Did not {} any title, no matching title found".format("finish" if save else "drop"))


def currently_watching(watchers):
    filterobj = deepcopy(user_interface.__filter_settings__)
    filterobj[Filter.watchers] = watchers
    return (x[0] for x in Stream.create_logstream(filterobj))




def print_short_help():
    user_interface.add_docs()
    print(user_interface.__doc__)

def print_long_help():
    user_interface.add_docs()
    print(user_interface.__doc__)

def check_option(short_option, long_option, return_arguments = False):
    if not short_option:
        short_option = '_______________________________________'
    if not long_option:
        long_option = '_______________________________________'
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
                else:
                    return True
    return [] if return_arguments else False


def main():
    os.chdir(os.path.abspath(__file__).rpartition(os.path.sep)[0])

    if len(sys.argv) == 1 or sys.argv[-1] in {'-h', '/?', ''}:
        print_short_help()
        return
    if sys.argv[-1] in {'--help', }:
        print_long_help()
        return
    if not any(map(lambda x:x.startswith('-'), sys.argv[1:])):
        watchers = get_current_watchers()
        filename = os.path.split(sys.argv[1])[-1]
        log_anime(filename, watchers)
        return

    #we don't copy here, to give preprocess flags the ability to modify
    filterobj = user_interface.__filter_settings__
    #action_flags = [(lambda x: print_from_stream(stream), ("r", "report"), False)]
    for action, options,arguments in user_interface.preprocess_flags:
        return_value = check_option(options[0], options[1], arguments)
        if return_value:
            action(return_value)
    for item in user_interface.static_flags:
        key = item[0]
        if not filterobj[key]:
            filterobj[key] = check_option(item[1][0], item[1][1], item[2])

    if any(filterobj.values()):
        stream = Stream.create_logstream(filterobj)
        for action, options, arguments in user_interface.postprocess_flags:
            return_value = check_option(options[0], options[1], arguments)
            if return_value:
                if arguments:
                    action(stream, return_value)
                else:
                    action(stream)
                break
        else:
            Stream.print_(stream, filterobj)
    return filterobj

user_interface.initialize()
if __name__ == '__main__':
    assert_correct_arguments()
    a = main()
