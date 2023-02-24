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
        self.total = 0

        self.links = []
        self.queue = asyncio.Queue()

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

        # * find song containers
        tag = soup.find_all(class_='track_list track_table')[0]
        song_containers = tag.find_all(class_='track_row_view linked')

        # * domain url
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


async def dl_track(track_url: str, sess: ScrapeSession) -> None:
    # * get full song url
    soup = bs4.BeautifulSoup(requests.get(url=track_url).text, 'html.parser')

    song_name = soup.find(class_='trackTitle').contents[0].strip()

    # * contruct file path
    filename = f'{song_name}.mp3'
    if filename in sess.dl_dir_content:
        sess.already_here.append(song_name)
        raise CantGetTheJuice(f'{song_name:.<80} +++ already here')

    # * download file
    song_path = f'{sess.dl_dir}/{filename}'
    try:
        urllib.request.urlretrieve(track_url, song_path)
    except Exception as err:
        sess.problems.append(song_name)
        raise CantGetTheJuice(f'{song_name:.<80} --- cannot download', [err]) from err
    else:
        log.success(f'{song_name:.<80} +++ done')
        sess.downloads.append(song_name)

    # * get song meta
    album_name = soup.find(id='name-section').find('a').contents[0].contents[0]
    artist_name = soup.find(id='name-section').contents[3].contents[3].contents[1].contents[0]

    song_art_url = soup.find(id='tralbumArt').contents[1].contents[1].attrs['src']
    cover_art_path = f'{sess.art_dir}/{filename}.png'
    urllib.request.urlretrieve(song_art_url, cover_art_path)

    song = eyed3.load(path=song_path)
    song.initTag()

    song.tag.album = album_name
    song.tag.artist = artist_name
    song.tag.title = song_name

    with open(cover_art_path, 'rb') as cover_art:
        song.tag.images.set(3, cover_art.read(), 'image/jpeg')

    song.tag.save()


async def consumer(sess: ScrapeSession):
    while True:
        track_url = await sess.queue.get()

        try:
            await dl_track(track_url, sess)
        except CantGetTheJuice as err:
            log.error(err)
        finally:
            sess.queue.task_done()
            await asyncio.sleep(0.01)


async def producer(sess: ScrapeSession):
    while sess.links:
        url = sess.links.pop()

        log.verbose(f'resolving {url=} ...')

        track_urls = await flatten(url)
        sess.total += len(track_urls)

        log.notice(f'enqueuing: {json.dumps(track_urls, indent=4)}')

        for track_url in track_urls: await sess.queue.put(track_url)
        await asyncio.sleep(0.01)


async def get_all_the_juice(urls: list[str], dest: str, workers: int) -> None:
    log.info(f'starting with {workers=}')
    sess = ScrapeSession(dl_dir=dest)
    sess.links = [*urls]

    producers = [asyncio.create_task(producer(sess)) for _ in range(workers)]
    consumers = [asyncio.create_task(consumer(sess)) for _ in range(workers)]

    # await asyncio.gather(*producers, *consumers)
    # await sess.queue.join()

    # for c in consumers: c.cancel()

    log.notice(f'{str(" SUMMARY "):*^80}')
    log.notice(sess)


def dl(urls: list[str], dest: str, workers: int) -> None:
    pretend_to_be_browser()

    asyncio.run(get_all_the_juice(urls, dest, workers))
