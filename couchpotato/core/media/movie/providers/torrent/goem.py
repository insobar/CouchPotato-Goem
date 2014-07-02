from couchpotato.core.media._base.providers.torrent.goem import Base
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'Goem'

class Goem(MovieProvider, Base): pass
