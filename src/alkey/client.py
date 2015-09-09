# -*- coding: utf-8 -*-

"""Provides ``get_redis_client``, a redis client factory that can be used
  directly, or in contect of a Pyramid application as a request method.
"""

__all__ = [
    'GetRedisClient',
    'get_redis_client'
]

import logging
logger = logging.getLogger(__name__)

from pyramid_redis import DEFAULT_SETTINGS
from pyramid_redis.hooks import RedisFactory

class GetRedisClient(object):
    def __init__(self, **kwargs):
        self.factory = kwargs.get('factory', RedisFactory())
        self.settings = kwargs.get('settings', DEFAULT_SETTINGS)

    def __call__(self, request=None):
        if request is None:
            registry = None
            settings = self.settings
        else:
            registry = request.registry
            settings = registry.settings
        return self.factory(settings, registry=registry)


get_redis_client = GetRedisClient()
