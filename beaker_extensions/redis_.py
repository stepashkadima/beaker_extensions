import logging
import pickle
from beaker.exceptions import InvalidCacheBackendError

from beaker_extensions.nosql import Container
from beaker_extensions.nosql import NoSqlManager
from beaker_extensions.nosql import pickle

try:
    from redis import Redis
except ImportError:
    raise InvalidCacheBackendError("Redis cache backend requires the 'redis' library")

log = logging.getLogger(__name__)

class RedisManager(NoSqlManager):
    def __init__(self, namespace, url=None, data_dir=None, lock_dir=None, userid=None, **params):
        self.connection_pool = params.pop('connection_pool', None)
        NoSqlManager.__init__(self, namespace, url=url, data_dir=data_dir, lock_dir=lock_dir, **params)
        self.userid = userid or self.get_userid_from_namespace() or 'ANON'

    def get_userid_from_namespace(self):
        keys = self.db_conn.keys('beaker:%s:*' % self.namespace)
        if keys:
            key = keys[0]
            res = key.split(':userid:')[-1]
            return res if res else None

    def open_connection(self, host, port, **params):
        self.db_conn = Redis(host=host, port=int(port), connection_pool=self.connection_pool, **params)

    def __contains__(self, key):
        log.debug('%s contained in redis cache (as %s) : %s'%(key, self._format_key(key), self.db_conn.exists(self._format_key(key))))
        return self.db_conn.exists(self._format_key(key))

    def set_value(self, key, value):
        key = self._format_key(key)
        self.db_conn.set(key, pickle.dumps(value))

    def __delitem__(self, key):
        key = self._format_key(key)
        self.db_conn.delete(key)

    def _format_key(self, key):
        return 'beaker:%s:%s:userid:%s' % (self.namespace, key.replace(' ', '\302\267'), self.userid)

    def get_user_sessions(self, userid):
        keys = self.db_conn.keys('*:userid:%s' % userid)
        res = {}
        for key in keys:
            res[key] = pickle.loads(self.db_conn.get(key))
        return res

    def do_remove(self):
        self.db_conn.flush()

    def keys(self):
        raise self.db_conn.keys('beaker:%s:*' % self.namespace)


class RedisContainer(Container):
    namespace_manager = RedisManager
