# -*- coding: utf-8 -*-

"""Provides a ``bind`` function to bind flush and commit events to
  their respective handler functions.
"""

__all__ = [
    'bind',
]

import logging
logger = logging.getLogger(__name__)

from sqlalchemy import event

from .handle import handle_commit
from .handle import handle_flush

def bind(session_cls):
    """Handle the ``after_flush`` and ``after_commit`` events of the
      ``session_cls`` provided.
    """
    
    event.listen(session_cls, 'after_flush', handle_flush)
    event.listen(session_cls, 'after_commit', handle_commit)

