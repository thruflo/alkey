# -*- coding: utf-8 -*-

"""Provides the ``IRedisConnectionPool`` marker interface."""

__all__ = [
    'IRedisConnectionPool'
]

from zope.interface import Attribute
from zope.interface import Interface

class IRedisConnectionPool(Interface):
    """Provided by RedisConnectionPool utilities."""

