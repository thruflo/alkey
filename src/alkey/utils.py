# -*- coding: utf-8 -*-

"""Utility functions."""

__all__ = [
    'get_object_id',
    'get_stamp',
    'unpack_object_id'
]

import logging
logger = logging.getLogger(__name__)

from datetime import datetime

import re
valid_object_id = re.compile(r'^alkey:[a-z_]+#[0-9]+$')

def get_object_id(instance):
    """Return an identifier for a model ``instance``.
      
      Setup::
      
          >>> from mock import Mock
          >>> mock_instance = Mock()
          >>> mock_instance.__tablename__ = 'items'
          >>> mock_instance.id = 1234
      
      Uses the SQL tablename and the row id to generate a unique object id::
      
          >>> get_object_id(mock_instance)
          u'alkey:items#1234'
      
      Unless it was passed a something else, in which case it returns it.
      
          >>> get_object_id('flobble')
          'flobble'
          >>> get_object_id(None)
      
    """
    
    # If we've been passed an object id, return it.
    if hasattr(instance, '__tablename__'):
        return u'alkey:{0}#{1}'.format(instance.__tablename__, instance.id)
    return instance

def get_stamp(datetime_instance=None):
    """Return a consistent string format for a datetime.
      
          >>> get_stamp('datetime')
          'datetime'
      
    """
    
    if datetime_instance is None:
        datetime_instance = datetime.utcnow()
    return str(datetime_instance)

def unpack_object_id(object_id):
    """Return ``(table_name, id)`` for ``object_id``::
      
          >>> unpack_object_id(u'alkey:questions#1234')
          (u'questions', 1234)
      
    """
    
    s = object_id.replace(u'alkey:', '', 1)
    parts = s.split('#')
    parts[1] = int(parts[1])
    return tuple(parts)

