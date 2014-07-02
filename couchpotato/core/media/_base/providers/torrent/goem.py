import traceback
import re
from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog


log = CPLog(__name__)


class Base(TorrentProvider):
    http_time_between_calls = 10

    urls = {
        'test': 'http://goem.org/',
        'base_url': 'http://goem.org',
        'login': 'http://goem.org/takelogin.php',
        'login_check': 'http://goem.org/my.php',
        'search': 'http://goem.org/browse.php?search=%s&stype=2&cat=0',
    }

    source = '&source%%5B%%5D=%s'

    def _find_quality_params(self, quality_id):
        quality_id = quality_id.upper()
        if quality_id == 'HD':
            return {'tag': '1080P;720P', 'param': False}
        elif quality_id == 'SD':
            return {'tag': '-1080P;-720P', 'param': False}
        elif quality_id == '1080P':
            return {'tag': '1080P', 'param': False}
        elif quality_id == '720P':
            return {'tag': '720P', 'param': False}
        elif quality_id in ['DVDR', 'DVDRIP']:
            return {'tag': 'DVD', 'param': True}
        elif quality_id in ['BRDISK', 'BRRIP']:
            return {'tag': 'BluRay', 'param': True}
        elif quality_id in ['SCREENER', 'R5', 'TELECINE', 'TELESYNC', 'CAM']:
            return None  # Not allowed to be uploaded to goem
        else:
            return None

    def _get_page_count(self, html):
        nav_div = html.find('p', attrs={'class', 'pager'})
        if nav_div:
            page_links = nav_div.find_all('a')
            if page_links:
                pages = [0]
                for link in page_links:
                    matcher = re.search('page=(\d*)', link['href'])
                    pages.append(tryInt(matcher.group(0)))
                return max(pages)
        return 1

    def _add_torrent(self, table_row, results):
        torrent_tds = table_row.find_all('td')
        if len(torrent_tds) == 11:
            url_base = self.urls['base_url']
            torrent_id = torrent_tds[0].find('a')['href'].replace('/details.php?id=', '')
            download_url = url_base + torrent_tds[1].find('a')['href']
            details_link = torrent_tds[5].find('a')
            details_url = url_base + details_link['href']
            torrent_name = details_link.string
            torrent_seeders = tryInt(re.sub('[^0-9]', '', unicode(torrent_tds[7].find('nobr').contents[0].string)))
            torrent_leechers = tryInt(re.sub('[^0-9]', '', unicode(torrent_tds[7].find('nobr').contents[2].string)))
            torrent_size = self.parseSize(torrent_tds[9].find('span').string)

            results.append({
                'id': torrent_id,
                'name': torrent_name,
                'url': download_url,
                'detail_url': details_url,
                'size': torrent_size,
                'seeders': torrent_seeders,
                'leechers': torrent_leechers,
            })
    # noinspection PyBroadException
    def _search(self, movie, quality, results):
        quality_map = self._find_quality_params(quality['identifier'])
        if quality_map is None:
            return

        quality = quality_map['tag']
        use_source_tag = quality_map['param']

        imdb_id = movie['identifier']

        current_page = 1
        pages = -1

        while True:
            try:
                url = self.urls['search'] % imdb_id
                data = self.getHTMLData(url)

                if data:
                    html = BeautifulSoup(data)
                    if pages == -1:
                        pages = self._get_page_count(html)

                    torrent_table = html.find('table', attrs={'id': 'browse'})
                    if torrent_table:
                        torrent_rows = torrent_table.find_all('tr', attrs={'class': 'table_row'})
                        for row in torrent_rows:
                            self._add_torrent(row, results)

                    if current_page >= pages:
                        break
            except:
                log.error('Unexpected error while searching %s: %s', (self.getName(), traceback.format_exc()))
                return

    def getLoginParams(self):
        return tryUrlencode({
            'goeser': self.conf('username'),
            'gassmord': self.conf('password'),
            'login': 'submit',
        })

    def loginSuccess(self, output):
        return 'Login failed!' not in output.lower()
		
config = [{
    'name': 'goem',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'Goem',
            'description': 'See <a href="http://www.goem.org">Goem</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]
