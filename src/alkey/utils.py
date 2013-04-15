# -*- coding: utf-8 -*-

"""Utility functions."""

__all__ = [
    'get_object_id',
    'get_stamp',
    'get_table_id',
    'unpack_object_id'
]

import logging
logger = logging.getLogger(__name__)

from datetime import datetime

import re
valid_object_id = re.compile(r'^alkey:[a-z_]+#[0-9]+$', re.U)
valid_write_token = re.compile(r'^alkey:([a-z_]+|[*])#[*]$', re.U)

def get_object_id(instance, table_oid=None):
    """Return an identifier for a model ``instance``.
      
      Setup::
      
          >>> from mock import Mock
          >>> mock_instance = Mock()
          >>> mock_instance.__tablename__ = 'items'
          >>> mock_instance.id = 1234
      
      Uses the SQL tablename and the row id to generate a unique object id::
      
          >>> get_object_id(mock_instance)
          u'alkey:items#1234'
      
      Can also be passed a model class::
      
          >>> mock_instance.id = '<column>'
          >>> get_object_id(mock_instance)
          u'alkey:items#*'
      
      Or an arbritrary value::
      
          >>> get_object_id('flobble')
          'flobble'
          >>> get_object_id(None)
      
    """
    
    # Compose.
    if table_oid is None:
        table_oid = get_table_id
    
    # If we've been passed a flushed sqlalchemy instance, return an instance
    # identifier.
    if hasattr(instance, '__tablename__'):
        instance_id = getattr(instance, 'id', None)
        if isinstance(instance_id, int):
            return u'alkey:{0}#{1}'.format(instance.__tablename__, instance.id)
        # Or if we've been passed an unflushed instance or a model class,
        # return a class identifier.
        return table_oid(instance.__tablename__)
    # Otherwise pass through the argument value.
    return instance

def get_stamp(datetime_instance=None):
    """Return a consistent string format for a datetime.
      
          >>> get_stamp('datetime')
          'datetime'
      
    """
    
    if datetime_instance is None:
        datetime_instance = datetime.utcnow()
    return str(datetime_instance)

def get_table_id(tablename):
    """Return an identifier for a model class.
      
          >>> get_table_id('items')
          u'alkey:items#*'
      
    """
    
    return u'alkey:{0}#*'.format(tablename)

def unpack_object_id(object_id):
    """Return ``(table_name, id)`` for ``object_id``::
      
          >>> unpack_object_id(u'alkey:questions#1234')
          (u'questions', 1234)
          >>> unpack_object_id(u'alkey:questions#*')
          (u'questions', None)
      
    """
    
    s = object_id.replace(u'alkey:', '', 1)
    parts = s.split('#')
    try:
        parts[1] = int(parts[1])
    except ValueError:
        parts[1] = None
    return tuple(parts)

