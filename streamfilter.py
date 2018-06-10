import random

import animelog
import database_reader
import itertools

class Filter(object):
    @staticmethod
    def title(stream, filterobj):
        return itertools.ifilter(lambda x:any((True for title in filterobj[Filter.title] if animelog.parse_title(title, skip_number = True)[0] in x[0])), stream)

    #update filtersettings so that it is as if
    #supplied the current watchers as watchers argument
    @staticmethod
    def apply_current_watchers(x):
        animelog.user_interface.__filter_settings__[Filter.watchers] = animelog.get_current_watchers()

    @staticmethod
    def title_exact(stream, filterobj):
        passed_titles = map(lambda x : animelog.parse_title(x, skip_number = True)[0],filterobj[Filter.title_exact])
        return itertools.ifilter(lambda x:x[0] in passed_titles, stream)
    @staticmethod
    def watchers(stream, filterobj):
        def matches(x):
            return set(x[1]['watchers']) == set(filterobj[Filter.watchers])
        return itertools.ifilter(matches, stream)
    @staticmethod
    def unwatched_aired(stream, filterobj):
        for title, values in stream:
            aired_eps = database_reader.get_aired_episodes(title)
            try:
                if aired_eps and  (max(aired_eps) > min(values['watchers'].values())): #is in database_reader and (aired_ep1, aired_ep2 ...) > min((title, {watcher:ep_nr, ... })[1].values()))
                    yield (title, values)
            except ValueError:
                animelog.errprint("error on", title, values)

    @staticmethod
    def airing(stream, filterobj):
        return itertools.ifilter(lambda x: database_reader.is_airing(x[0]), stream)
    @staticmethod
    def lucky(stream, filterobj):
        stream = list(stream)
        found_titles = filter(lambda x: x[1].get('filename', ''), stream)
        if not found_titles:
            return stream
        your_show_today = random.choice(found_titles)
        return [your_show_today,]
