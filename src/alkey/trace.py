# -*- coding: utf-8 -*-

"""Provides an optional ``trace_redis`` function, which wraps Redis client calls
  so they're traceable by the New Relic python agent, e.g.:
  
      import redis
      trace_redis(redis)
  
  This will make Redis appear in your New Relic monitoring much like Memcache
  does out of the box.
"""

__all__ = [
    'trace_redis'
]

import logging
logger = logging.getLogger(__name__)

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


def trace_redis(redis, get_methods=None, wrap=None):
    """If using New Relic, call this function to trace Redis calls with the
      New Relic python agent.
    """
    
    logger.warn('trace redis')
    logger.warn(redis)
    
    # Compose.
    if get_methods is None:
        get_methods = _get_methods
    if wrap is None:
        wrap = wrap_function_trace
    
    # Trace connects.
    wrap(redis, 'Connection.connect')
    
    # Trace client calls.
    for cls_name in ('Redis', 'StrictRedis'):
        client_cls = getattr(redis, cls_name)
        for method in get_methods(client_cls):
            if not hasattr(client_cls, method):
                continue
            wrap(redis, '{0}.{1}'.format(cls_name, method))
            logger.warn(('wrap', cls_name, method))

