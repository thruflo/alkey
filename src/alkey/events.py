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

def bind(session_cls, event=None, flush=None, commit=None):
    """Handle the ``after_flush`` and ``after_commit`` events of the
      ``session_cls`` provided::
      
          >>> from mock import Mock
          >>> mock_event = Mock()
          >>> bind('session', event=mock_event, flush='handle_flush',
          ...         commit='handle_commit')
          >>> mock_event.listen.assert_any_call('session', 'after_flush', 
          ...         'handle_flush')
          >>> mock_event.listen.assert_any_call('session', 'after_commit', 
          ...         'handle_commit')
      
    """
    
    # Compose.
    if event is None: # pragma: no cover
        event = sqlalchemy_event
    if flush is None: # pragma: no cover
        flush = handle_flush
    if commit is None: # pragma: no cover
        commit = handle_commit
    
    event.listen(session_cls, 'after_flush', flush)
    event.listen(session_cls, 'after_commit', commit)

