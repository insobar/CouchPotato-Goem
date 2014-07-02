from couchpotato.core.media._base.providers.torrent.goem import Base

log = CPLog(__name__)

autoload = 'Goem'

class Goem(MovieProvider, Base):
