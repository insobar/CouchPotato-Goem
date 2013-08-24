import traceback
import re
from bs4 import BeautifulSoup
from core.helpers.variable import tryInt
from core.providers.torrent.base import TorrentProvider
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog

__author__ = 'Scott Faria - scott.faria@gmail.com'

log = CPLog(__name__)


class Goem(TorrentProvider):

    http_time_between_calls = 10

    urls = {
        'test': 'http://goem.org/',
        'base_url': 'http://goem.org',
        'login': 'http://goem.org/takelogin.php',
        'login_check': 'http://goem.org/my.php',
        'search': 'http://goem.org/advanced.php?action=search&title=%s&title-tag=%s&title-tag-type=any&year=%d&page=%d',
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

    def _format_url(self, current_page, title, year, quality_tag, use_source_tag):
        if use_source_tag:
            return self.urls['search'] % (tryUrlencode(title), "", year, current_page) + self.source % quality_tag
        else:
            return self.urls['search'] % (tryUrlencode(title), quality_tag, year, current_page)

    # noinspection PyBroadException
    def _searchOnTitle(self, title, movie, quality, results):
        quality_map = self._find_quality_params(quality['identifier'])
        if quality_map is None:
            return

        quality = quality_map['tag']
        use_source_tag = quality_map['param']

        year = movie['library']['year']

        current_page = 1
        pages = -1

        while True:
            url = self._format_url(current_page, title, year, quality, use_source_tag)
            data = self.getHTMLData(url, opener=self.login_opener)

            try:
                if data:
                    html = BeautifulSoup(data)
                    if pages == -1:
                        pages = self._get_page_count(html)

                    torrent_table = html.find('table', attrs={'id': 'browse'})
                    if torrent_table:
                        torrent_rows = torrent_table.find_all('tr', attrs={'class': 'table_row'})
                        for row in torrent_rows:
                            self._add_torrent(row, results)
            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

            if current_page >= pages:
                break

    def getLoginParams(self):
        return tryUrlencode({
            'goeser': self.conf('username'),
            'gassmord': self.conf('password'),
            'login': 'submit',
        })

    def loginSuccess(self, output):
        return 'Login failed!' not in output.lower()