# -*- coding: utf-8 -*-

"""Provides a ``bind`` function to bind flush and commit events to
  their respective handler functions.
"""

__all__ = [
    'bind',
]

import logging
logger = logging.getLogger(__name__)

from sqlalchemy import event as sqlalchemy_event

from .handle import handle_commit
from .handle import handle_flush
from .handle import handle_rollback

def bind(session_cls, event=None, commit=None, flush=None, rollback=None):
    """Handle the ``after_flush`` and ``after_commit`` events of the
      ``session_cls`` provided::
      
          >>> from mock import Mock
          >>> mock_event = Mock()
          >>> bind('session', event=mock_event, commit='handle_commit',
          ...         flush='handle_flush', rollback='handle_rollback')
          >>> mock_event.listen.assert_any_call('session', 'after_commit', 
          ...         'handle_commit')
          >>> mock_event.listen.assert_any_call('session', 'after_flush', 
          ...         'handle_flush')
          >>> mock_event.listen.assert_any_call('session', 'after_soft_rollback',
          ...         'handle_rollback')
      
    """
    
    # Compose.
    if event is None: # pragma: no cover
        event = sqlalchemy_event
    if commit is None: # pragma: no cover
        commit = handle_commit
    if flush is None: # pragma: no cover
        flush = handle_flush
    if rollback is None: # pragma: no cover
        rollback = handle_rollback
    
    event.listen(session_cls, 'after_commit', commit)
    event.listen(session_cls, 'after_flush', flush)
    event.listen(session_cls, 'after_soft_rollback', rollback)
    

