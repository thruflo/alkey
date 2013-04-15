# -*- coding: utf-8 -*-

"""Provides a ``CacheKeyGenerator`` utility that generates a cache key when
  called with a list of arguments and ``get_token`` and ``set_token`` functions
  to get and set the token that's used as the cache key fragment for model
  instances when they're provided as args when calling the ``CacheKeyGenerator``.
  
  I.e.: if you set the token for an instance::
  
      set_token(<redis client>, <instance>, u'foo')
  
  Then the token will be in the cache key::
  
      CacheKeyGenerator(<redis client>)(<instance>, <instance>)
      // returns u'foo/foo'
  
"""

__all__ = [
    'CacheKeyGenerator',
    'get_cache_key_generator',
    'get_token_key',
    'get_token',
    'set_token'
]

import logging
logger = logging.getLogger(__name__)

from datetime import datetime

try:
    from beaker.cache import CacheManager
    from beaker.util import parse_cache_config_options
except ImportError:
    pass

from .client import get_redis_client
from .constants import CACHE_INI_NAMESPACES
from .constants import GLOBAL_WRITE_TOKEN
from .constants import MAX_CACHE_DURATION
from .constants import TOKEN_NAMESPACE
from .utils import get_object_id
from .utils import get_stamp
from .utils import valid_object_id
from .utils import valid_write_token

def get_token_key(instance, namespace=None, get_oid=None):
    """Return a token cache key."""
    
    # Compose.
    if get_oid is None:
        get_oid = get_object_id
    if namespace is None:
        namespace = TOKEN_NAMESPACE
    
    object_id = get_oid(instance)
    return u'{0}:{1}'.format(namespace, object_id)

def get_token(redis_client, instance, get_key=None, get_value=None, set_value=None):
    """Provide a standalone function to get instance tokens."""
    
    # Compose.
    if get_key is None:
        get_key = get_token_key
    if get_value is None:
        get_value = get_stamp
    if set_value is None:
        set_value = set_token
    
    # Get the token key.
    key = get_key(instance)
    
    # Implement a manual ``get and then set if None``, so that whenever
    # an instance is looked up for the first time, if not in the redis
    # db (either bc its new, or bc, say, redis fell over or was wiped)
    # then the token value is set to a new value.
    # We do this manually without a transaction because there's no
    # need to block everything to cope with an edge case, and because
    # setting the value twice in competing threads is *fine*, i.e.:
    # at worse causes one extra cache miss, not data getting stale.
    # (We don't use setnx because it always set the value on a volatile
    # key, i.e.: it would always overwrite the token every time its
    # read, no matter whether it exists or not).
    token_value = redis_client.get(key)
    if token_value is None:
        token_value = get_value()
        set_value(redis_client, instance, token_value)
    return token_value

def set_token(redis_client, instance, token_value, duration=None, get_key=None):
    """Use the ``redis_client`` to set the current token for ``instance``"""
    
    # Compose.
    if duration is None:
        duration = MAX_CACHE_DURATION
    if get_key is None:
        get_key = get_token_key
    
    key = get_key(instance)
    return redis_client.setex(key, duration, token_value)


class CacheKeyGenerator(object):
    """Call with an object or object id to get its cache key. Implements 
      `key based cache expiration <http://bit.ly/IEl4jh>`_.
    """
    
    def __call__(self, *args):
        """Returns the cache key using tokens for all of the args."""
        
        segments = []
        for arg in args:
            # Try and get a token from redis.
            oid = self.get_object_id(arg)
            is_str = isinstance(oid, basestring)
            is_oid = is_str and self.valid_object_id.match(oid)
            is_token = is_str and self.valid_write_token.match(oid)
            if is_oid or is_token:
                segment = self.get_token(self.redis, oid)
            # Otherwise fallback on using a unicode representation of the arg.
            elif isinstance(oid, unicode):
                segment = arg
            elif isinstance(oid, str):
                segment = arg.decode('utf-8', 'replace')
            else:
                segment = unicode(arg)
            segments.append(segment)
        return u'/'.join(segments)
    
    def __init__(self, redis_client, get_oid=None, get_token_=None, global_token=None,
            valid_oid=None, valid_token=None):
        """Instantiate a cache key generator with a redis client."""
        
        # Compose.
        if get_oid is None:
            get_oid = get_object_id
        if get_token_ is None:
            get_token_ = get_token
        if global_token is None:
            global_token = GLOBAL_WRITE_TOKEN
        if valid_oid is None:
            valid_oid = valid_object_id
        if valid_token is None:
            valid_token = valid_write_token
        
        # Assign.
        self.redis = redis_client
        self.get_object_id = get_oid
        self.get_token = get_token_
        self.global_write_token = global_token
        self.valid_object_id = valid_oid
        self.valid_write_token = valid_token
    

def get_cache_key_generator(request=None, generator_cls=None, get_redis=None):
    """Return an instance of ``CacheKeyGenerator`` configured with a redis
      client and the right cache duration.
    """
    
    # Compose.
    if generator_cls is None:
        generator_cls = CacheKeyGenerator
    if get_redis is None:
        get_redis = get_redis_client
    
    # Instantiate and return the cache key generator.
    return generator_cls(get_redis(request))


def get_cache_manager(request, namespaces=None, parse=None, manager_cls=None):
    """Return a configured beaker cache manager."""
    
    # Compose.
    if namespaces is None:
        namespaces = CACHE_INI_NAMESPACES
    if parse is None:
        parse = parse_cache_config_options
    if manager_cls is None:
        manager_cls = CacheManager
    
    # Unpack.
    settings = request.registry.settings
    
    # For each of the namespaces provided, if they exist then patch their
    # values into the cache_opts.
    cache_opts = {}
    for prefix in namespaces:
        for key in settings.keys():
            if key.startswith(prefix):
                name = key.split(prefix)[1].strip()
                value = settings[key]
                try:
                    value = value.strip()
                except AttributeError:
                    pass
                cache_opts[name] = value
    
    # Instantiate and return the cache manager.
    cache_manager = manager_cls(**parse(cache_opts))
    return cache_manager

