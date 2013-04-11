# -*- coding: utf-8 -*-

"""Provides a ``bind`` function to bind flush and commit events to
  their respective handler functions.
"""

__all__ = [
    'handle_commit',
    'handle_flush',
    'invalidate_tokens',
    'record_changed',
]

import logging
logger = logging.getLogger(__name__)

try: #pragma: no cover
    from pyramid.threadlocal import get_current_request
except ImportError: #pragma: no cover
    get_current_request = lambda: None

from .cache import set_token
from .utils import get_object_id
from .utils import get_stamp

CHANGED_KEY = 'alkey.handle.CHANGED'

def handle_commit(session, get_redis=None, get_request=None):
    """Get the current request and call the invalidate function."""
    
    # Compose.
    if get_redis is None:
        get_redis = get_redis_client
    if get_request is None:
        get_request = get_current_request
    if invalidate is None:
        invalidate = invalidate_tokens
    
    # Get a redis client configured with the current scope's
    # connection pool.
    request = get_request()
    redis_client = get_redis(request)
    
    # Call the invalidate function.
    invalidate(redis_client)

def handle_flush(session, ctx, get_redis=None, get_request=None, record=None):
    """Get the current request and record the changed instances."""
    
    # Compose.
    if get_redis is None:
        get_redis = get_redis_client
    if get_request is None:
        get_request = get_current_request
    if record is None:
        record = record_changed
    
    # Get a redis client configured with the current scope's
    # connection pool.
    request = get_request()
    redis_client = get_redis(request)
    
    # Record the changed instances.
    instances = session.dirty.copy()
    instances.union(session.deleted)
    record(redis_client, instances)


def _invalidate_tokens(pipeline, key=None, get_value=None, store_value=None):
    """Invalidate the tokens of the instances in the changed set."""
    
    # Compose.
    if key is None:
        key = CHANGED_KEY
    if get_value is None:
        get_value = get_stamp
    if store_value is None:
        store_value = set_token
    
    # Get a new value for the token.
    value = get_value()
    
    # Get the current members of the set.
    members = pipeline.smembers(key)
    
    # Switch mode, so the pipeline buffers the multiple set commands.
    pipeline.multi()
    
    # Update the token for each member of the set.
    for item in members:
        store_value(pipeline, item, value)
    
    # Wipe the set.
    return pipeline.srem(key, *members)

def invalidate_tokens(redis_client, invalidate=None, key=None):
    """Call ``_invalidate_tokens`` within a transactional pipeline,
      so the redis interaction avoids tcp overhead and is guaranteed to
      be consistent, i.e.: will retry in the event of an error.
    """
    
    # Compose.
    if invalidate is None:
        invalidate = _invalidate_tokens
    if key is None:
        key = CHANGED_KEY
    
    # Call ``invalidate`` in a pipeline transaction.
    return redis_client.transaction(invalidate, key)

def record_changed(redis_client, instances, key=None, get_oid=None):
    """Add the instances to the changed set redis."""
    
    # Compose.
    if key is None:
        key = CHANGED_KEY
    if get_oid is None:
        get_oid = get_object_id
    
    values = [get_oid(item) for item in instances]
    return redis_client.sadd(key, *values)

