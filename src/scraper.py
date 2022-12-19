import logging
import requests
import urllib
import re
import os
import bs4
import eyed3
import json
import asyncio
import random


log = logging.getLogger(__name__)


def pretend_to_be_browser():
    '''this is a one time thing'''
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla')]
    urllib.request.install_opener(opener)


class ScrapeSession():
    SONG_URL_PATTERN = r'https:\/\/t4.bcbits.com\/stream\/.*?token\=\w+'
    ALBUM_URL_PATTERN = r'bandcamp\.com/album'
    TRACK_URL_PATTERN = r'bandcamp\.com/track'

    def __init__(self, dl_dir: str):
        self.problems = []
        self.downloads = []
        self.already_here = []
        self.dl_dir = dl_dir

        self.resolve_url_tasks = []
        self.dl_track_tasks = []

        self.resolve_q = asyncio.Queue()
        self.dl_q = asyncio.Queue()

        if not os.path.exists(dl_dir): os.mkdir(dl_dir)

        self.art_dir = f'{dl_dir}/art'
        if not os.path.exists(self.art_dir): os.mkdir(self.art_dir)

    @property
    def dl_dir_content(self): return set(os.listdir(self.dl_dir))

    def __str__(self):
        return json.dumps({
            'problems': self.problems,
            'downloaded': self.downloads,
            'dl_dir': self.dl_dir,
            'already_here': self.already_here,
            'dl_summary': f'{len(self.already_here) + len(self.downloads)} / {self.total}',
        }, indent=4)


class CantGetTheJuice(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors


async def flatten(url: str) -> None:
    def extract_track_urls(album_url: str = url) -> list:
        html = requests.get(url=album_url)
        soup = bs4.BeautifulSoup(html.text, 'html.parser')

        # find song containers
        tag = soup.find_all(class_='track_list track_table')[0]
        song_containers = tag.find_all(class_='track_row_view linked')

        # domain url
        end_str = 'com'
        domain_url = url[:url.find(end_str) + len(end_str)]

        song_urls = []
        for cont in song_containers:
            inner_cont: bs4.element.Tag = cont.find_next(class_='title')
            href: str = inner_cont.find_next('a')['href']
            song_url = domain_url + href
            song_urls.append(song_url)

        return song_urls
    
    if re.search(ScrapeSession.ALBUM_URL_PATTERN, url):
        return extract_track_urls(url)
    elif re.search(ScrapeSession.TRACK_URL_PATTERN, url):
        return [url]


async def dl_track(url: str, sess) -> None:
    log.success(f'dl {url}')


async def resolve_task(sess: ScrapeSession):
    url = await sess.resolve_q.get()

    log.verbose(f'resolving {url} ...')
    track_urls = await flatten(url)

    log.notice(json.dumps(track_urls, indent=4))

    for track_url in track_urls:
        sess.dl_q.put_nowait(dl_track(track_url))

    for _ in range(5):
        sess.dl_track_tasks.append(
            asyncio.create_task(dl_track(sess))
        )

    await asyncio.sleep(random.uniform(0.1, 0.5))
    sess.resolve_q.task_done()


async def get_all_the_juice(urls: list[str], dest: str, workers: int) -> None:
    sess = ScrapeSession(dl_dir=dest)

    for url in urls: sess.resolve_q.put_nowait(url)

    for _ in range(workers):
        sess.resolve_url_tasks.append(
            asyncio.create_task(resolve_task(sess))
        )

    await sess.resolve_q.join()
    for task in sess.resolve_url_tasks: task.cancel()

    # await sess.dl_q.join()
    # for task in sess.dl_q: task.cancel()

    await asyncio.gather(*sess.resolve_url_tasks, return_exceptions=True)
    # await asyncio.gather(*sess.dl_track_tasks, return_exceptions=True)


def dl(urls: list[str], dest: str, workers: int) -> None:
    pretend_to_be_browser()

    asyncio.run(get_all_the_juice(urls, dest, workers))
    log.success('done')
