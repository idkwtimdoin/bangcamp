import requests
import urllib
import re
import os
import click
import bs4
import eyed3
import json


def pretend_to_be_browser():
    '''this is a one time thing'''
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla')]
    urllib.request.install_opener(opener)


class ScrapeSession():
    def __init__(self, domain_url: str, dl_dir: str):
        self.domain_url = domain_url
        self.problems = []      # things that were not downloaded
        self.downloads = []     # things that were not not downloaded
        self.already_here = []  # things that were already downloaded
        self.dl_dir = dl_dir

        self.total = 0

        if not os.path.exists(dl_dir): os.mkdir(dl_dir)

        # self.art_dir = f'{dl_dir}/art'
        # if not os.path.exists(self.art_dir): os.mkdir(self.art_dir)

        self.song_url_pattern = r'https:\/\/t4.bcbits.com\/stream\/.*?token\=\w+'

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


def get_the_juice(i: int, tag: bs4.element.Tag, scrape_sess: ScrapeSession) -> None:
    ''' get the juice for 1 song
        raise: CantGetTheJuice
    '''
    # get title and href
    c: bs4.element.Tag = tag.find_next(class_='title')
    href: str = c.find_next('a')['href']
    song_name: str = c.find_next('a').contents[0].contents[0]

    # get full song url
    url = f'{scrape_sess.domain_url}{href}'
    soup = bs4.BeautifulSoup(requests.get(url=url).text, 'html.parser')
    try:
        full_url = re.findall(scrape_sess.song_url_pattern, str(soup))[0]
    except IndexError as err:
        scrape_sess.problems.append(song_name)
        raise CantGetTheJuice(f'{song_name:.<80} --- cannot extract song source url', [err]) from err

    # contruct file path
    filename = f'{song_name}.mp3'
    if filename in scrape_sess.dl_dir_content:
        scrape_sess.already_here.append(song_name)
        raise CantGetTheJuice(f'{song_name:.<80} +++ already here')

    # get song meta
    album_name = soup.find_all(id='name-section')[0].find_all('a')[0].contents[0].contents[0]
    artist_name = soup.find_all(id='name-section')[0].contents[3].contents[3].contents[1].contents[0]

    # download file
    album_path = f'{scrape_sess.dl_dir}/{album_name}' 
    song_path = f'{album_path}/{filename}'

    if not os.path.exists(album_path):
        os.mkdir(album_path)

    try:
        urllib.request.urlretrieve(full_url, song_path)
    except Exception as err:
        scrape_sess.problems.append(song_name)
        raise CantGetTheJuice(f'{song_name:.<80} --- cannot download', [err]) from err
    else:
        print(f'{song_name:.<80} +++ done')
        scrape_sess.downloads.append(song_name)

    song_art_url = soup.find_all(id='tralbumArt')[0].contents[1].contents[1].attrs['src']
    cover_art_path = f'{scrape_sess.dl_dir}/{album_name}/{album_name}.png'
    if not os.path.isfile(cover_art_path):
        urllib.request.urlretrieve(song_art_url, cover_art_path)

    song = eyed3.load(path=song_path)
    song.initTag()

    song.tag.album      = album_name
    song.tag.artist     = artist_name
    song.tag.title      = song_name
    song.tag.track_num  = i

    with open(cover_art_path, 'rb') as cover_art:
        song.tag.images.set(3, cover_art.read(), 'image/jpeg')

    song.tag.save()

def get_album(soup: bs4.BeautifulSoup, url: str, dest: str):
    # find song containers
    tag = soup.find_all(class_='track_list track_table')[0]
    song_containers = tag.find_all(class_='track_row_view linked')

    # domain url
    end_str = 'com'
    domain_url = url[:url.find(end_str) + len(end_str)]

    # bypass 403 http error
    pretend_to_be_browser()

    scrape_sess = ScrapeSession(domain_url, dest)
    scrape_sess.total = len(song_containers)

    print(f'{str(f" {scrape_sess.total} songs found "):*^80}')
    for i, cont in enumerate(song_containers):
        try:
            get_the_juice(i+1, cont, scrape_sess)
        except CantGetTheJuice as err:
            print(err)

    print(f'{str(" summary "):*^80}')
    print(scrape_sess)

def get_track(soup: bs4.BeautifulSoup, url: str, dest: str):
    # domain url
    end_str = 'com'
    domain_url = url[:url.find(end_str) + len(end_str)]

    # bypass 403 http error
    pretend_to_be_browser()

    scrape_sess = ScrapeSession(domain_url, dest)
    scrape_sess.total = 1

    print(f'{str(f" {scrape_sess.total} songs found "):*^80}')

    split_url = url.split("/")
    href= f'/{split_url[int(len(split_url))-2]}/{split_url[int(len(split_url)-1)]}'
    name_section = soup.find_all(class_="trackView")[0]
    song_name= name_section.find_all(class_="trackTitle")[0].contents[0].split('\n')[1].strip()
    album_name= name_section.find_all(class_="fromAlbum")[0].contents[0]
    artist_name = soup.find_all(id='name-section')[0].contents[3].contents[3].contents[1].contents[0]

    # get full song url
    url = f'{scrape_sess.domain_url}{href}'
    soup = bs4.BeautifulSoup(requests.get(url=url).text, 'html.parser')
    try:
        full_url = re.findall(scrape_sess.song_url_pattern, str(soup))[0]
    except IndexError as err:
        scrape_sess.problems.append(song_name)
        raise CantGetTheJuice(f'{song_name:.<80} --- cannot extract song source url', [err]) from err

    # contruct file path
    filename = f'{song_name}.mp3'
    if filename in scrape_sess.dl_dir_content:
        scrape_sess.already_here.append(song_name)
        return

    # download file
    song_path = f'{scrape_sess.dl_dir}/{filename}'

    if not os.path.exists(scrape_sess.dl_dir):
        os.mkdir(scrape_sess.dl_dir)

    try:
        urllib.request.urlretrieve(full_url, song_path)
    except Exception as err:
        scrape_sess.problems.append(song_name)
        raise CantGetTheJuice(f'{song_name:.<80} --- cannot download', [err]) from err
    else:
        print(f'{song_name:.<80} +++ done')
        scrape_sess.downloads.append(song_name)

    song_art_url = soup.find_all(id='tralbumArt')[0].contents[1].contents[1].attrs['src']
    cover_art_path = f'{scrape_sess.dl_dir}/{song_name}.png'
    if not os.path.isfile(cover_art_path):
        urllib.request.urlretrieve(song_art_url, cover_art_path)

    song = eyed3.load(path=song_path)
    song.initTag()

    song.tag.album      = album_name
    song.tag.artist     = artist_name
    song.tag.title      = song_name

    with open(cover_art_path, 'rb') as cover_art:
        song.tag.images.set(3, cover_art.read(), 'image/jpeg')

    song.tag.save()

@click.command()
@click.option('-u', '--urls', help='album/track url array', required=True)
@click.option('-D', '--dest', help='destination folder. default', default='downloads', show_default=True, metavar='my/secret/folder')
def main(urls, dest):
    url_split = list(filter(None, urls.split(',')))

    for url in url_split:
        url = url.replace(" ", "")
        print(f'downloading {url} to {dest} ...')
        # parse html
        html = requests.get(url=url)
        soup = bs4.BeautifulSoup(html.text, 'html.parser')

        if "/album/" in url:
            get_album(soup, url, dest)
        elif "/track/" in url:
            get_track(soup, url, dest)


if __name__ == '__main__': main()
