from __future__ import print_function
import animelog
import database_updater
import itertools
__doc__ = "animelog by mdp\n"
static_flags = []
preprocess_flags = []

def add_docs():
    short_docs = {
        'set' : 'set the current watchers to <arg>..',
        'current': 'filter by current watchers, handles multiple current watchers in AND-wise fashion',
        'watchers': 'filter by supplied watcher(s), handles multiple watchers in AND-wise fashion',
        'update': 'retreive airing data for shows that are not yet in database',
        'full-update': 'retrieve airing data for all shows are in any watcher\'s active log',
        'minimize' : 'remove shows from database that are not in any watcher\'s active log',
        'drop' : 'remove supplied show(s) from current watchers\' active log',
        'dropfuzzy': 'as --drop, except will match shownames partially',
        'play' : 'play the result(s) of the filter, and update the current watchers\' log with this',
        'title': 'filter fuzzily by title(s), handles multiple titles in an OR-wise fashion',
        'alias' : 'add an alias for a show for retrieving airing data',
        'finish' : 'move supplied show from current watchers\' active log to their finished log',
        'simulate': 'parse a filename and outputs how it would be named in log',
        'date' : 'output the next airing date of shows in filter',
        'next': 'change episode numbers in filter to the next episode',
        'lucky' : 'select a random show out of filter (that has a file that can be played)',
        'latest' : 'change episode numbers in filter to the most recently aired episode',
        'airing' : 'filter episodes by currently airing shows',
        'unwatched': 'filter by shows that have unwatched aired episodes',
        'episode': 'when outputting, only display show title and episode number',
    }
    for flag in itertools.chain(preprocess_flags, static_flags):
        try:
            '''we pop here, because outputting the same line twice
            in the case of "linkage" (such as animelog.stream_find_file and animelog.play_from_stream)
            would be confusing and silly
            we also filter flags with no commands this way
            '''
            flag[0].__doc__ = short_docs.pop(flag[1][1]) 
        except KeyError:
            continue
    #animelog.__doc__ = ''' animelog by mdp\n'''
    for flag in filter(lambda x: any(x[1][1]) and hasattr(x[0], '__doc__'), itertools.chain(preprocess_flags, static_flags)):
        short_command = "-{1[0]}{3}, " if flag[1][0] else "\t"
        long_command = "--{1[1]}{3},  "
        explanation = "{0.__doc__}\n"
        totstring = "".join([short_command, long_command, explanation])
        __doc__ += totstring

def create_preprocess_flags():
    preprocess_flags = [
        (animelog.set_current_watchers, ('s', 'set'), True),
        ((lambda x: animelog.__filter_settings__.__setitem__(animelog.filter_by_watchers, animelog.get_current_watchers())),
        ("c", "current"), False),
        ((lambda x: database_updater.partial_update_database()), ('U', 'update'), False),
        ((lambda x: database_updater.full_update_database()), ('', 'full-update'), False),
        ((lambda x: database_updater.minimize_database()), ('', 'minimize'), False),
        ((lambda userin: [animelog.drop_title(title, animelog.get_current_watchers()) for title in userin]), ('', 'drop'), True),
        ((lambda userin: [animelog.drop_fuzzy(title, animelog.get_current_watchers()) for title in userin]), ('', 'dropfuzzy'),True),
        ((lambda userin: [animelog.drop_title(title, animelog.get_current_watchers(), save = True) for title in userin]), ('', 'finish'),True),
        ((lambda titles: [print(animelog.parse_title(title)) for title in titles]), ('', 'simulate'), True),
        ((lambda x: animelog.add_alias(x[0].replace("_"," "), x[1])), ('', 'alias'), True),
        ]
    return preprocess_flags
def create_static_flags():
    static_flags =  [
                 (animelog.filter_by_titles, ('t', 'title'), True),
                 (animelog.filter_by_watchers, ('w', 'watchers'), True),
                 (animelog.filter_by_airing, ('a', 'airing'), False),
                 (animelog.filter_by_unwatched_aired, ('u', 'unwatched'), False),
                 (animelog.stream_as_successor, ('n', 'next'), False),
                 (animelog.stream_as_latest_unwatched, ('l', 'latest'), False),
                 (animelog.stream_find_next_airdate, ('d', 'date'), False),
                 (animelog.stream_as_title_epnr, ('e', 'episode'), False),
                 (animelog.stream_find_file, ('p', 'play'), False),
                 (animelog.filter_by_lucky, ('L', 'lucky'), False),
                 (animelog.play_from_stream, ('p', 'play'), False),
                 (animelog.print_from_stream, ('', ''), False)
                ]
    return static_flags
    
def initialize():
    global static_flags, preprocess_flags
    static_flags = create_static_flags()
    preprocess_flags = create_preprocess_flags()
