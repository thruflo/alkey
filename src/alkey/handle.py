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
from .client import get_redis_client
from .constants import CHANGED_KEY
from .constants import CHANGED_SET_EXPIRES
from .constants import GLOBAL_WRITE_TOKEN
from .utils import get_object_id
from .utils import get_stamp
from .utils import get_table_id
from .utils import unpack_object_id

def handle_commit(session, get_redis=None, get_request=None, invalidate=None):
    """Gets a redis client and call the invalidate function with it.
      
          >>> from mock import Mock
          >>> mock_session = Mock()
          >>> mock_session.hash_key = 'session id'
          >>> mock_get_request = Mock()
          >>> mock_get_request.return_value = '<request>'
          >>> mock_get_redis = Mock()
          >>> mock_get_redis.return_value = '<redis client>'
          >>> mock_invalidate = Mock()
          >>> mock_kwargs = dict(get_redis=mock_get_redis,
          ...         get_request=mock_get_request, invalidate=mock_invalidate)
          >>> handle_commit(mock_session, **mock_kwargs)
          >>> mock_get_redis.assert_called_with('<request>')
          >>> mock_invalidate.assert_called_with('<redis client>', 'session id')
      
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
    invalidate(redis_client, session.hash_key)

def handle_flush(session, ctx, get_redis=None, get_request=None, record=None):
    """Get the current request and record the changed instances set::
      
          >>> from mock import Mock
          >>> mock_session = Mock()
          >>> mock_session.hash_key = 'session id'
          >>> mock_session.new = set('a')
          >>> mock_session.dirty = set('b')
          >>> mock_session.deleted = set('c')
          >>> mock_get_request = Mock()
          >>> mock_get_request.return_value = '<request>'
          >>> mock_get_redis = Mock()
          >>> mock_get_redis.return_value = '<redis client>'
          >>> mock_record = Mock()
          >>> mock_kwargs = dict(get_redis=mock_get_redis,
          ...         get_request=mock_get_request, record=mock_record)
          >>> handle_flush(mock_session, 'ctx', **mock_kwargs)
          >>> mock_get_redis.assert_called_with('<request>')
          >>> mock_record.assert_called_with('<redis client>', 'session id',
          ...         set(['a', 'c', 'b']))
      
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
    
    # Record the new, changed and deleted instances.
    instances = session.new.union(session.dirty.union(session.deleted))
    record(redis_client, session.hash_key, instances)

def handle_rollback(session, tx, get_redis=None, get_request=None, clear=None):
    """Get the current request and clear the changed instances set::
      
          >>> from mock import Mock
          >>> mock_session = Mock()
          >>> mock_session.hash_key = 'session id'
          >>> mock_tx = Mock()
          >>> mock_get_request = Mock()
          >>> mock_get_request.return_value = '<request>'
          >>> mock_get_redis = Mock()
          >>> mock_get_redis.return_value = '<redis client>'
          >>> mock_clear = Mock()
          >>> mock_kwargs = dict(get_redis=mock_get_redis,
          ...         get_request=mock_get_request, clear=mock_clear)
      
      Exits if ``tx_parent is None``::
      
          >>> mock_tx._parent = None
          >>> handle_rollback(mock_session, mock_tx, **mock_kwargs)
          >>> mock_get_redis.assert_called_with('<request>') # doctest: +ELLIPSIS
          Traceback (most recent call last):
          ...
          AssertionError: Expected call: mock('<request>')
          Not called
      
      Otherwise get the redis client using the current request and clears the
      changed instances set::
      
          >>> mock_tx._parent = 'Not None'
          >>> handle_rollback(mock_session, mock_tx, **mock_kwargs)
          >>> mock_get_redis.assert_called_with('<request>')
          >>> mock_clear.assert_called_with('<redis client>', 'session id')
      
    """
    
    # Compose.
    if get_redis is None: # pragma: no cover
        get_redis = get_redis_client
    if get_request is None: # pragma: no cover
        get_request = get_current_request
    if clear is None: # pragma: no cover
        clear = clear_changed
    
    # Exit if this is an inner transaction -- i.e.: only wipe a changed set
    # if an outer transaction is rolled back. This uses an internal ``_parent``
    # property of the transaction but that seems the most reliable way of
    # determining whether its an outer rollback or not (the values of the
    # ``session.is_active`` and ``session.transaction`` properties vary
    # according to the session config).
    if tx._parent is None:
        return
    
    # Get a redis client configured with the current scope's connection pool.
    request = get_request()
    redis_client = get_redis(request)
    
    # Clear the changed set.
    clear(redis_client, session.hash_key)

def invalidate_tokens(redis_client, session_id, key=None, get_value=None,
        global_token=None, store_value=None, table_oid=None, unpack_oid=None):
    """Invalidate tokens with a non-transactional pipeline call that minimises
      TCP overhead without blocking the redis client.
      
      Note that the implementation deletes members from the changed set the
      command after their token is changed. It's really not a problem if another
      thread / process / client either sets the token or adds the member back to
      the set in between these two commands, as either the token is updated twice,
      which is fine, or the member is added to the set twice, which is fine, or
      updated immediately before it is removed, which is fine.
      
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
    if global_token is None:
        global_token = GLOBAL_WRITE_TOKEN
    if store_value is None:
        store_value = set_token
    if table_oid is None:
        table_oid = get_table_id
    if unpack_oid is None:
        unpack_oid = unpack_object_id
    
    # Get the current members of the set, exiting if there are none.
    changed_key = u'{0}:{1}'.format(key, session_id)
    members = redis_client.smembers(changed_key)
    if not members:
        return
    
    # Get a new value for the token.
    value = get_value()
      
    # Get a pipeline to buffer multiple commands (i.e.: reduce TCP overhead)
    pipeline = redis_client.pipeline(transaction=False)
    
    # Build a set of tablenames.
    tablenames = set()
    
    # Update the token for each member of the set, deleting the member from the
    # as the next sequential command.
    for item in members:
        store_value(pipeline, item, value)
        try:
            tablenames.add(unpack_oid(item)[0])
        except IndexError:
            pass
        pipeline.srem(changed_key, item)
    
    # Update the tables.
    for item in tablenames:
        store_value(pipeline, table_oid(item), value)
    
    # Update the global write token.
    store_value(pipeline, global_token, value)
    
    # Execute the queued commands.
    pipeline.execute()

def clear_changed(redis_client, session_id, key=None):
    """Clear the changed set for this session."""
    
    # Compose.
    if key is None:
        key = CHANGED_KEY
    
    # Get the current members of the set, exiting if there are none.
    changed_key = u'{0}:{1}'.format(key, session_id)
    return redis_client.delete(changed_key)

def record_changed(redis_client, session_id, instances, expires=None, key=None,
        get_oid=None):
    """Add the instances to the changed set for this session."""
    
    # Compose.
    if expires is None:
        expires = CHANGED_SET_EXPIRES
    if key is None:
        key = CHANGED_KEY
    if get_oid is None:
        get_oid = get_object_id
    
    changed_key = u'{0}:{1}'.format(key, session_id)
    values = [get_oid(item) for item in instances]
    
    # Add and update set expiry within a transaction.
    pipeline = redis_client.pipeline()
    pipeline.sadd(changed_key, *values).expire(changed_key, expires)
    return pipeline.execute()

