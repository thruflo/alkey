# -*- coding: utf-8 -*-

"""Provides ``get_redis_client``, a redis client factory that can be used
  directly, or in contect of a Pyramid application as a request method.
  
  This uses ``get_redis_config`` to parse redis connection / db / pooling
  config out of the os.environ / config provided.
"""

__all__ = [
    'get_redis_client'
    'get_redis_config'
]

import logging
logger = logging.getLogger(__name__)

import os
from urlparse import urlparse

import redis

from zope.component import getGlobalSiteManager
from zope.interface import directlyProvides

from .interfaces import IRedisClientFactory
from .interfaces import IRedisConnectionPool

def get_redis_config(env, default_db=0, default_stub='REDIS', parse=None):
    """Return a dict of ``{host: ..., port: ..., db: ..., max_connections: N}``
      by parsing the ``env`` config. The logic is designed to pick up the first
      value starting with ``redis://`` and use the key from that value to look
      for db and max_connections. This, in theory, allows any redis provider
      to be picked up:
      
      Requires a redis url in the ``env``::
      
          >>> env = {}
          >>> get_redis_config(env) #doctest: +ELLIPSIS
          Traceback (most recent call last):
          ...
          KeyError: u'Redis URL not found in env.'
          >>> env = {'REDIS_URL': u'redis://username:password@hostname:6379'}
          >>> get_redis_config(env)
          {'host': u'hostname', 'password': u'password', 'db': 0, 'port': 6379}
          
      Actually the key can be any name (the implementation looks for the
      ``redis://...`` value)::
      
          >>> env = {'FOO': u'redis://username:password@hostname:6379'}
          >>> get_redis_config(env)
          {'host': u'hostname', 'password': u'password', 'db': 0, 'port': 6379}
      
      If provided, ``REDIS_DB`` and ``REDIS_MAX_CONNECTIONS`` will be parsed::
      
          >>> env = {
          ...     'REDIS_URL': u'redis://hostname:6379',
          ...     'REDIS_DB': '3',
          ...     'REDIS_MAX_CONNECTIONS': '12'
          ... }
          >>> get_redis_config(env)
          {'host': u'hostname', 'db': 3, 'port': 6379, 'max_connections': 12}
      
      Note that the values will *either* be picked up from the ``REDIS_*`` keys
      *or* from keys matching the stub of the redis url key, with the matching
      stub taking precedence::
      
          >>> env = {
          ...     'REDISTOGO_URL': u'redis://hostname:6379',
          ...     'REDIS_DB': '1',
          ...     'REDISTOGO_DB': '2',
          ...     'REDISTOGO_MAX_CONNECTIONS': '3'
          ... }
          >>> get_redis_config(env)
          {'host': u'hostname', 'db': 2, 'port': 6379, 'max_connections': 3}
          >>> env = {
          ...     'REDISTOGO_URL': u'redis://hostname:6379',
          ...     'REDISTOGO_DB': '4',
          ...     'REDIS_MAX_CONNECTIONS': '5'
          ... }
          >>> get_redis_config(env)
          {'host': u'hostname', 'db': 4, 'port': 6379, 'max_connections': 5}
      
      Note that the max connections is passed to a connection pool shared
      by this process / worker. That means that you must manage your connections
      to stay within the limits of your redis instance / redis hosting provider
      and your processes / workers.
      
      For example, if you run 2 processes each with 2 gunicorn workers and set
      max connections to 5, then you need a redis db that can accept 20
      connections (as long as you're only ever connecting from those processes
      -- i.e.: maybe leave a few spare connections for debugging etc).
    """
    
    # Compose.
    if parse is None:
        parse = urlparse
    
    # Find the redis url config value.
    url = None
    url_key = None
    for k, v in env.items():
        matches = False
        if isinstance(v, unicode) and v.startswith(u'redis://'):
            matches = True
        elif isinstance(v, str) and v.startswith('redis://'):
            matches = True
        if matches:
            url_key = k
            url = parse(v)
            break
    
    # If it didn't exist, complain.
    if not url:
        raise KeyError, u'Redis URL not found in env.'
    
    # Build the db and max_connections keys.
    stubs = []
    if u'_' in url_key:
        stubs.append(url_key.split(u'_')[0])
    stubs.append(default_stub)
    db_keys = [u'{0}_DB'.format(item) for item in stubs]
    max_connections_keys = [u'{0}_MAX_CONNECTIONS'.format(item) for item in stubs]
    
    # Get the db and max conns values.
    db = default_db
    for key in db_keys:
        if env.has_key(key):
            db = int(env[key])
            break
    max_connections = None
    for key in max_connections_keys:
        if env.has_key(key):
            max_connections = int(env[key])
            break
    
    # Build and return the config data.
    config = {
        'host': url.hostname,
        'port': url.port,
        'db': db
    }
    if url.password:
        config['password'] = url.password
    if max_connections is not None:
        config['max_connections'] = max_connections
    return config

def get_redis_client(request=None, env=None, get_config=None, get_registry=None,
        redis_cls=None, pool_cls=None):
    """Returns a ``redis`` client using a connection pool that's either
      registered in the application registry, or in a global zope component
      architecture registry.
      
      This allows the function to be called within the contex of a Pyramid
      application (which uses request.registry) *or* directly from any context
      (script or application) that doesn't use Pyramid.
    """
    
    # Test jig.
    if env is None:
        env = os.environ
    if get_config is None:
        get_config = get_redis_config
    if get_registry is None:
        get_registry = getGlobalSiteManager
    if redis_cls is None:
        redis_cls = redis.StrictRedis
    if pool_cls is None:
        pool_cls = redis.ConnectionPool
    
    # Get the target ``registry``.
    has_registry = request and hasattr(request, 'registry')
    registry = request.registry if has_registry else get_registry()
    
    # If the application / user has registered their own redis client factory
    # then use that.
    factory = registry.queryUtility(IRedisClientFactory)
    if factory:
        return factory(request=request)
    
    # Otherwise, get or create a connection pool.
    pool = registry.queryUtility(IRedisConnectionPool)
    if not pool:
        config = get_config(env)
        pool = pool_cls(**config)
        directlyProvides(pool, IRedisConnectionPool)
        registry.registerUtility(pool, IRedisConnectionPool)
    
    # And use it to instantiate a redis client.
    return redis_cls(connection_pool=pool)

