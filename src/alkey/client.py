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

from .interfaces import IRedisConnectionPool

def get_redis_config(env, default_db=0, default_stub='REDIS', parse=None):
    """Return a dict of ``{host: ..., port: ..., db: ..., max_connections: N}``
      by parsing the ``env`` config. The logic is designed to pick up the first
      value starting with ``redis://`` and use the key from that value to look
      for db and max_connections.
      
      This, in theory, allows any redis provider to be picked up. In practise
      it means:
      
      a) don't have more than one redis url in your env (if your environment does
         then pass a manually constructed env to the function that only contains
         the config you want to use)
      b) follow the REDIS_URL / REDIS_DB / REDIS_MAX_CONNECTIONS naming convention,
         e.g.: REDISCLOUD_URL / REDISCLOUD_DB / REDISCLOUD_MAX_CONNECTIONS
      
      Note also that the max connections is passed to a connection pool shared
      by this process / worker. That means that you must manage your connections
      to stay within the limits of your redis instance / redis hosting provider
      and your processes / workers. For example, if you run 2 processes each
      with 2 gunicorn workers and set max connections to 5, then you need a
      redis db that can accept 20 connections (as long as you're only ever
      connecting from those processes -- i.e.: maybe leave a few spare
      connections for debugging etc).
    """
    
    # Compose.
    if parse is None:
        parse = urlparse
    
    # Find the redis url config value.
    url = None
    url_key = None
    for k, v in env.items():
        if isinstance(v, basestring) and v.startswith(u'redis://'):
            url_key = k
            url = parse(v)
            break
    
    # If it didn't exist, complain.
    if not url:
        raise KeyError, u'Redis URL not found in env.'
    
    # Build the db and max_connections keys.
    if u'_' in url_key:
        stub = url_key.split(u'_')[0]
    else:
        stub = default_stub
    db_key = u'{0}_DB'.format(stub)
    max_connections_key = u'{0}_MAX_CONNECTIONS'.format(stub)
    
    # Get the db and max conns values.
    if env.has_key(db_key):
        db = int(env[db_key])
    else:
        db = default_db
    if env.has_key(max_connections_key):
        max_connections = int(env[max_connections_key])
    else:
        max_connections = None
    
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
    
    # Get or create a connection pool.
    pool = registry.queryUtility(IRedisConnectionPool)
    if not pool:
        config = get_config(env)
        pool = pool_cls(**config)
        directlyProvides(pool, IRedisConnectionPool)
        registry.registerUtility(pool, IRedisConnectionPool)
    
    # Return an instantiated redis client.
    return redis_cls(connection_pool=pool)

