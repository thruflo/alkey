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
from .constants import CHANGED_KEY
from .utils import get_object_id
from .utils import get_stamp

def handle_commit(session, get_redis=None, get_request=None, invalidate=None):
    """Gets a redis client and call the invalidate function with it.
      
          >>> from mock import Mock
          >>> mock_get_request = Mock()
          >>> mock_get_request.return_value = '<request>'
          >>> mock_get_redis = Mock()
          >>> mock_get_redis.return_value = '<redis client>'
          >>> mock_invalidate = Mock()
          >>> mock_kwargs = dict(get_redis=mock_get_redis,
          ...         get_request=mock_get_request, invalidate=mock_invalidate)
          >>> handle_commit('session', **mock_kwargs)
          >>> mock_get_redis.assert_called_with('<request>')
          >>> mock_invalidate.assert_called_with('<redis client>')
      
    """
    
    # Compose.
    if get_redis is None: # pragma: no cover
        get_redis = get_redis_client
    if get_request is None: # pragma: no cover
        get_request = get_current_request
    if invalidate is None: # pragma: no cover
        invalidate = invalidate_tokens
    
    # Get a redis client configured with the current scope's
    # connection pool.
    request = get_request()
    redis_client = get_redis(request)
    
    # Call the invalidate function.
    invalidate(redis_client)

def handle_flush(session, ctx, get_redis=None, get_request=None, record=None):
    """Get the current request and record the changed instances.
      
          >>> from mock import Mock
          >>> mock_session = Mock()
          >>> mock_session.dirty = set('a')
          >>> mock_session.deleted = set('b')
          >>> mock_get_request = Mock()
          >>> mock_get_request.return_value = '<request>'
          >>> mock_get_redis = Mock()
          >>> mock_get_redis.return_value = '<redis client>'
          >>> mock_record = Mock()
          >>> mock_kwargs = dict(get_redis=mock_get_redis,
          ...         get_request=mock_get_request, record=mock_record)
          >>> handle_flush(mock_session, 'ctx', **mock_kwargs)
          >>> mock_get_redis.assert_called_with('<request>')
          >>> mock_record.assert_called_with('<redis client>', set(['a', 'b']))
      
    """
    
    # Compose.
    if get_redis is None: # pragma: no cover
        get_redis = get_redis_client
    if get_request is None: # pragma: no cover
        get_request = get_current_request
    if record is None: # pragma: no cover
        record = record_changed
    
    # Get a redis client configured with the current scope's
    # connection pool.
    request = get_request()
    redis_client = get_redis(request)
    
    # Record the changed instances.
    instances = session.dirty.union(session.deleted)
    record(redis_client, instances)


def invalidate_tokens(redis_client, key=None, get_value=None, store_value=None):
    """Invalidate tokens with a non-transactional pipeline call that minimises
      TCP overhead without blocking the redis client.
      
      Note that the implementation deletes members from the changed set the
      command after their token is changed. It's really not a problem if another
      thread / process / client either sets the token or adds the member back to
      the set in between these two commands, as either the token is updated twice,
      which is fine, or the member is added to the set twice, which is fine, or
      removed immediately before it is removed, which is fine.
      
      The upshot of which is that there's no need to run the commands in a
      transaction, or (more importantly) to watch the changed key to make sure
      members aren't added to the set whilst the transaction is completed. This
      means we don't need to block redis / stop flushes from another client adding
      members to the set as we do this block operation.
    """
    
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
    members = redis_client.smembers(key)
    
    # Get a pipeline to buffer multiple commands (i.e.: reduce TCP overhead)
    pipeline = redis_client.pipeline(transaction=False)
    
    # Update the token for each member of the set, deleting the member from the
    # as the next sequential command.
    for item in members:
        store_value(pipeline, item, value)
        pipeline.srem(key, item)
    
    # Execute the queued commands.
    pipeline.execute()

def record_changed(redis_client, instances, key=None, get_oid=None):
    """Add the instances to the changed set redis."""
    
    # Compose.
    if key is None:
        key = CHANGED_KEY
    if get_oid is None:
        get_oid = get_object_id
    
    values = [get_oid(item) for item in instances]
    return redis_client.sadd(key, *values)

