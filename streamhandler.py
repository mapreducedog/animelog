import os
import glob
import itertools
import time

import animelog
import database_reader

class Stream(object):
    @staticmethod
    def __create_logstream__(filterobj):
        log = animelog.get_log()
        for item in log.iteritems():
            yield item
    @staticmethod
    def create_logstream(filterobj, this_stream = None):
        if this_stream is None:
            this_stream = Stream.__create_logstream__(filterobj)

        stream = this_stream
        for item in animelog.user_interface.static_flags:
            function = item[0]
            if filterobj[function]:
                stream = function(stream, filterobj)
                    #stream = reduce((lambda stream, key_func: check_stream(key_func[1](stream, filterobj), key_func[0]) if filterobj[key_func[0]] else stream),key_func_pairs, this_stream)

        return stream

    @staticmethod
    def create_future_stream(stream, filterobj):
        for title in filterobj[animelog.Filter.title] + filterobj[animelog.Filter.title_exact]:
            yield animelog.parse_title(title, skip_number = True)[0], {'watchers' : {watcher : 0 for watcher in filterobj[animelog.Filter.watchers] or animelog.get_current_watchers()}}

    @staticmethod
    def create_finished_stream(stream, filterobj):
        finished_log = animelog.get_finished()
        for item in finished_log.iteritems():
            yield item

    @staticmethod
    def play(stream, filterobj):
        batfiledir = '"' + os.path.join(os.path.split(database_reader.__file__)[0],'animelog.sh') + '"'
        played_any = False
        for title, values in stream:
            played_any = True
            if values.get('filename'):
                os.system(u'{} {}'.format(batfiledir, values['filename']))
            else:
                animelog.errprint(u"{} episode {} not found on drive".format(title, min(values['watchers'].values())))
        if not played_any:
            animelog.errprint("Did not find anything to play")



    @staticmethod
    def print_(stream, filterobj):
        for item in stream:
            title, values = item
            if isinstance(values, dict):
                print(title)
                for key, value in values.iteritems():
                    print(" "*4 + "{} : {}".format(key, value))
            else:
                print("{:20} {}".format(title, values))

    @staticmethod
    def only_title_epnr(stream, filterobj):
        for item in stream:
            yield item[0], min(item[1]['watchers'].values())

    @staticmethod
    def successor(stream, filterobj):
        def successor(ep):
            if isinstance(ep, int):
                return ep + 1
            if hasattr(ep, '__iter__'):
                return ep[:-1] + [ep[-1] + 1]

        for item in stream:
            title, watchers = item[0], item[1]['watchers']
            right_item = item[1].copy()
            right_item['watchers'] = {watcher: successor(episode) for watcher, episode in watchers.iteritems()}
            yield (title, right_item)
    @staticmethod
    def predecessor(stream, filterobj):
        def predecessor(ep):
            if isinstance(ep,int):
                return ep - 1
            if hasattr(ep, '__iter__'):
                return ep[:-1] + [ep[-1] - 1]

        for item in stream:
            title, watchers = item[0], item[1]['watchers']
            right_item = item[1].copy()
            right_item['watchers'] = {watcher: predecessor(episode) for watcher, episode in watchers.iteritems()}
            yield (title, right_item)
    @staticmethod
    def latest_unwatched(stream, filterobj):
        for item in stream:
            title, watchers_eps = item[0], item[1]['watchers']
            aired_eps = database_reader.get_aired_episodes(title)
            if aired_eps:
                latest = max(aired_eps)
                if latest > min(watchers_eps.values()):
                    right_item = item[1].copy()
                    right_item['watchers'] = {watcher : latest for watcher in watchers_eps.iteritems()}
                    yield (title, right_item)

    @staticmethod
    def next_airdate(stream, filterobj):
        for title, values in stream:
            airdate = database_reader.get_next_airing_time_single(title)
            if airdate:
                values['airing'] = (airdate[0], time.ctime(airdate[1]))
                yield (title, values)
    @staticmethod
    def file(stream, filterobj):
        settings = animelog.get_settings()
        recurse_depth = settings.get('recursive_depth', 2)
        ignore_exts = settings.get('ignore_exts', [".srt",".ass", ".sub"])
        for title, values in stream:
            episode = min(values['watchers'].values())
            if hasattr(episode, '__iter__'):
                episode = tuple(episode)
            for filename in sorted(
                itertools.chain(*[glob.glob(os.path.join(animelog.get_video_path(), *("*"*i))) for i in range(1, recurse_depth + 1)]),
                                   reverse = True):
                if not os.path.isfile(filename) or os.path.splitext(filename)[-1] in ignore_exts: #is directory or subtitle file
                    continue
                rtitle, repisode = animelog.parse_title(filename)
                if rtitle == title and repisode == episode:
                    values['filename'] = '"' + filename + '"'
                    yield(title, values)
                    break
            else:
                values['filename'] = ''
                yield (title, values)
