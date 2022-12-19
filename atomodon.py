#!/usr/bin/env python3
#
# Get Mastodon feed, output Atom feed.
#
# seth@sethoscope.net
# 2022-12-19


import urllib.request
import json 
import logging
from collections import UserDict
from feedgen.feed import FeedGenerator
import html.parser
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType
try:
    import cPickle as pickle
except ImportError:
    import pickle


# I use a file-backed persistent cache during development.
# It's much faster, and I don't spam the remote server.
class Cache(UserDict):
    def __init__(self, filename):
        super().__init__(self)
        self.filename = filename
        self.enabled = bool(filename)
        if filename:
            self.load()

    def load(self):
        try:
            self.data = pickle.load(open(self.filename, 'rb'))
            logging.debug('loaded cache')            
        except FileNotFoundError:
            logging.debug('new cache')
            self.data = {}

    def save(self):
        if self.filename:
            pickle.dump(cache, open(self.filename, 'wb'), 2)
            logging.debug('cache saved')


def fetch_json(url):
    global cache
    if url in cache:
        logging.debug(f'found {url} in cache')
        return cache[url]
    logging.debug(f'fetching {url}')
    with urllib.request.urlopen(url) as response:
        response = json.load(response)
        cache[url] = response
        return response


class Person():
    def __init__(self, server, username):
        self.server = server
        self.username = username
        self.webfinger = self._webfinger(server, username)
        self.userid = self.webfinger['id']

    @staticmethod
    def _webfinger(server, username):
        url = f'https://{server}/api/v1/accounts/lookup?acct={username}'
        return fetch_json(url)


class Entry():
    def __init__(self, eob, status):
        eob.id(status['uri'])
        eob.link(href=status['url'])
        eob.updated(status['created_at'])
        eob.content(self._content(status), type='html')
        eob.title(self._title(status, maxwords=10))

    @staticmethod
    def _format_tag(tag):
        return f'<a href="{tag["url"]}">#{tag["name"]}</a>'

    def _content(self, status):
        c = ( '<p>'
              f"{status['account']['display_name']}<br>\n"
              f"@{status['account']['acct']}<br>\n"
              f"{status['content']}"
              '</p>'
             )
        if status.get('tags', False):
            c += "\n<p> " + ', '.join(self._format_tag(t) for t in status['tags']) + " </p>\n"
        if status.get('reblog', False):
            c += '\n<p>boosted:</p><blockquote>' + self._content(status['reblog']) + '</blockquote>'
        logging.debug(f'entry content: {c}')
        return c

    # parse content to make titles
    class HTMLParser(html.parser.HTMLParser):
        def html_to_text(self, html):
            self.content = ''
            self.feed(html)
            return self.content

        def handle_data(self, data):
            logging.debug(f'HTML data : {data}')
            self.content += data

    def _title(self, status, maxwords=-1):
        if status.get('reblog', False):
            return self._title(status['reblog'], maxwords)
        title = self.HTMLParser().html_to_text(status["content"])
        return ' '.join(title.split()[:maxwords])


class Feed():
    def __init__(self, person):
        self.person = person
        self.feed = FeedGenerator()
        self.fill_header()
        self.get_entries()

    def fill_header(self):
        logging.debug('filling feed header info')
        self.feed.id(self.person.webfinger['url'])
        self.feed.title(self.person.webfinger["display_name"] + "\'s Mastodon feed")
        self.feed.author({'name': self.person.webfinger['display_name']})
        self.feed.link(href=self.person.webfinger['url'], rel='alternate')
        self.feed.image(url=self.person.webfinger['avatar'])
        self.feed.subtitle(f'@{self.person.username}@{self.person.server}')

    def get_entries(self):
        entries = self.fetch_entries(self.person.server, self.person.userid)
        logging.debug(f'Got {len(entries)} entries.')
        for e in entries:
            self.add_entry(e)
        self.feed.updated(max(e.updated() for e in self.feed.entry()))
        logging.debug(f'feed last updated: {self.feed.updated()}')

    @staticmethod
    def fetch_entries(server, userid):
        url = f'https://{server}/api/v1/accounts/{userid}/statuses?exclude_replies=true'
        return fetch_json(url)

    def add_entry(self, status):
        Entry(self.feed.add_entry(order='append'), status)
   

def main():
    description = ''
    parser = ArgumentParser(description=description,
                            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--cache', help='request cache, only for testing')
    parser.add_argument('--output', metavar='FILE')
    parser.add_argument('server')
    parser.add_argument('username')
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    global cache
    cache = Cache(args.cache)
    server = args.server
    username = args.username
    person = Person(server, username)
    feed = Feed(person)
    cache.save()

    if args.output:
        feed.feed.atom_file(args.output)
    else:
        # TODO: this is not working; it puts everything inside b''
        print(feed.feed.atom_str())
    


if __name__ == '__main__':
    main()
