# -*- coding: utf-8 -*-

"""Shared constant values."""

# Namespaces to look in for cache config.
CACHE_INI_NAMESPACES = ('mako.cache_args.', 'cache.')

# The key of the Redis set of changed instance identifiers.
CHANGED_KEY = 'alkey.handle.CHANGED'

# Clear old changed sets an hour after the last flush.
CHANGED_SET_EXPIRES = 60 * 60 # secs

# The special identifier used to generate the Redis key for the
# token that's updated whenever any instance is updated or deleted.
GLOBAL_WRITE_TOKEN = 'alkey:*#*' # I.e.: ``alkey:any-tablename#any-id``.

# Don't cache *anything* longer than one day.
MAX_CACHE_DURATION = 60 * 60 * 24 # secs

# The Redis key prefix of the instance tokens.
TOKEN_NAMESPACE = 'alkey.cache.TOKENS'
