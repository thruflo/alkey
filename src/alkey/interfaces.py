# -*- coding: utf-8 -*-

"""Marker interface."""

__all__ = [
    'IRedisClientFactory',
    'IRedisConnectionPool'
]

from zope.interface import Attribute
from zope.interface import Interface

class IRedisClientFactory(Interface):
    """Provided by redis client factories."""

class IRedisConnectionPool(Interface):
    """Provided by RedisConnectionPool utilities."""

