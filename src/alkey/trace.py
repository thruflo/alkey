# -*- coding: utf-8 -*-

"""Provides an optional ``trace_redis`` function, which wraps Redis client calls
  so they're traceable by the New Relic python agent, e.g.:
  
      trace_redis()
  
  Or to be explict about the redis module you want to trace::
  
      import redis as my_redis
      from alkey.trace import trace_redis
      
      trace_redis(redis_module=my_redis)
  
  This will make Redis appear in your New Relic monitoring (much like Memcache
  does out of the box). Note that tracing comes with a performance hit.
"""

__all__ = [
    'trace_redis'
]

import logging
logger = logging.getLogger(__name__)

import redis as default_redis_module

try:
    from newrelic.api.function_trace import wrap_function_trace
except ImportError:
    wrap_function_trace = None

def _get_methods(client_cls):
    """Get the methods provided by a redic client class."""
    
    keys = map(lambda k: k.lower(), client_cls.RESPONSE_CALLBACKS.keys())
    # Special case ``delete``.
    if 'del' in keys:
        keys.remove('del')
        keys.append('delete')
    return keys


def trace_redis(redis_module=None, get_methods=None, wrap=None):
    """If using New Relic, call this function to trace Redis calls with the
      New Relic python agent.
    """
    
    # Compose.
    if redis_module is None:
        redis_module = default_redis_module
    if get_methods is None:
        get_methods = _get_methods
    if wrap is None:
        wrap = wrap_function_trace
    
    # Trace connects.
    wrap(redis_module, 'Connection.connect')
    
    # Trace client calls.
    for cls_name in ('Redis', 'StrictRedis'):
        client_cls = getattr(redis_module, cls_name)
        for method in get_methods(client_cls):
            if not hasattr(client_cls, method):
                continue
            wrap(redis_module, '{0}.{1}'.format(cls_name, method))

