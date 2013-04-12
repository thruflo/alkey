# -*- coding: utf-8 -*-

"""Integration test for ``alkey``, testing with mock model instances /
  session events but a real redis db.
"""

import unittest
try:
    from mock import Mock
except ImportError:
    pass

class IntegrationTest(unittest.TestCase):
    """Test token and cache key generation in response to model changes."""
    
    def setUp(self):
        """Setup a redis client on a test db"""
        
        from alkey.client import get_redis_client
        env = {
            'REDIS_URL': 'redis://localhost:6379',
            'REDIS_DB': 6
        }
        self.redis = get_redis_client(None, env=env)
    
    def tearDown(self):
        self.redis.flushdb()
    
    def makeInstance(self, tablename='users', id=1):
        """Return a mock model instance."""
        
        instance = Mock()
        instance.__tablename__ = tablename
        instance.id = id
        return instance
    
    def test_get_token_for_new_instance(self):
        """Getting a token for an instance that isn't yet in the cache
          returns a new timestamp.
        """
        
        from alkey.cache import get_token
        from alkey.utils import get_stamp
        
        stamp = get_stamp()
        
        instance = self.makeInstance()
        token = get_token(self.redis, instance)
        
        self.assertTrue(token is not None)
        self.assertTrue(token.split(' ')[0] == stamp.split(' ')[0])
    
    def test_get_token_for_instance_twice(self):
        """Getting a token for an instance in the cache returns the stored token."""
        
        import time
        from alkey.cache import get_token
        
        instance = self.makeInstance()
        token1 = get_token(self.redis, instance)
        
        time.sleep(0.1)
        
        token2 = get_token(self.redis, instance)
        self.assertTrue(token1 == token2)
    
    def test_get_token_for_another_instance(self):
        """Getting a token for a different instance does not match."""
        
        import time
        from alkey.cache import get_token
        
        instance1 = self.makeInstance(id=1)
        token1 = get_token(self.redis, instance1)
        
        time.sleep(0.1)
        
        instance2 = self.makeInstance(id=2)
        token2 = get_token(self.redis, instance2)
        
        self.assertTrue(token1 != token2)
    
    def test_get_token_set_manually(self):
        """Getting a token for an instance returns the token set using ``set_token``."""
        
        from alkey.cache import get_token
        from alkey.cache import set_token
        
        value = u'spam'
        instance = self.makeInstance()
        set_token(self.redis, instance, value)
        
        token = get_token(self.redis, instance)
        self.assertTrue(token == value)
    
    def test_get_token_for_changed_instance(self):
        """Getting a token for a changed instance returns a new token."""
        
        from alkey.cache import get_token
        from alkey.handle import record_changed
        from alkey.handle import invalidate_tokens
        
        # Get the current token.
        instance = self.makeInstance()
        token1 = get_token(self.redis, instance)
        
        # Record that the instance has changed. Aka a mock flush.
        record_changed(self.redis, [instance])
        
        # Invalidate tokens for changed instances. Aka a mock commit.
        invalidate_tokens(self.redis)
        
        # Get the token again.
        token2 = get_token(self.redis, instance)
        
        # It's changed.
        self.assertTrue(token1 != token2)
    
    def test_stores_token_for_changed_instance(self):
        """Getting a token for a changed instance in the cache returns
          the stored token.
        """
        
        import time
        from alkey.cache import get_token
        from alkey.handle import record_changed
        from alkey.handle import invalidate_tokens
        
        # Get the current token.
        instance = self.makeInstance()
        token1 = get_token(self.redis, instance)
        
        # Record that the instance has changed. Aka a mock flush.
        record_changed(self.redis, [instance])
        
        # Invalidate tokens for changed instances. Aka a mock commit.
        invalidate_tokens(self.redis)
        
        # Get the token again.
        token2 = get_token(self.redis, instance)
        
        # It's changed.
        self.assertTrue(token1 != token2)
        
        # Pause.
        time.sleep(0.1)
        
        # Get it again, its not changed.
        token3 = get_token(self.redis, instance)
        self.assertTrue(token2 == token3)
    
    def test_get_cache_key(self):
        """Getting a cache key uses the instance token."""
        
        from alkey.cache import get_cache_key_generator
        from alkey.cache import get_token
        
        instance = self.makeInstance()
        token = get_token(self.redis, instance)
        
        generator = get_cache_key_generator(None)
        cache_key = generator(instance)
        
        self.assertTrue(cache_key == token)
    
    def test_get_cache_key_multiple_instances(self):
        """Getting a cache key works for a list of instances."""
        
        from alkey.cache import get_cache_key_generator
        from alkey.cache import get_token
        
        instance1 = self.makeInstance(id=1)
        instance2 = self.makeInstance(id=2)
        token1 = get_token(self.redis, instance1)
        token2 = get_token(self.redis, instance2)
        
        generator = get_cache_key_generator(None)
        cache_key = generator(instance1, instance2)
        
        self.assertTrue(token1 in cache_key)
        self.assertTrue(token2 in cache_key)
    
    def test_unicode_key_segment(self):
        """Unicode args are concatenated directly into the key."""
        
        from alkey.cache import get_cache_key_generator
        
        generator = get_cache_key_generator(None)
        cache_key = generator(u'€')
        
        self.assertTrue(cache_key == u'€')
    
    def test_string_key_segment(self):
        """String args are decoded to unicode and concatenated directly into
          the key.
        """
        
        from alkey.cache import get_cache_key_generator
        
        generator = get_cache_key_generator(None)
        cache_key = generator('\xe2\x82\xac')
        
        self.assertTrue(cache_key == u'€')
    
    def test_object_segment(self):
        """Other args are ``unicode()``d."""
        
        from alkey.cache import get_cache_key_generator
        
        generator = get_cache_key_generator(None)
        cache_key = generator({'foo': 'bar'})
        
        self.assertTrue(cache_key == u"{'foo': 'bar'}")
    
    def test_mixed_segments(self):
        """Keys can mix instances, object_ids, strings, objects, etc."""
        
        from alkey.cache import get_cache_key_generator
        from alkey.cache import get_token
        from alkey.utils import get_object_id
        
        instance1 = self.makeInstance(id=1)
        instance2 = self.makeInstance(id=2)
        token1 = get_token(self.redis, instance1)
        token2 = get_token(self.redis, instance2)
        
        args = [
            1, 
            'file://...', 
            u'€',
            {'foo': 'bar'}
        ]
        
        generator = get_cache_key_generator(None)
        cache_key = generator(instance1, get_object_id(instance2), *args)
        
        segments = [token1, token2] + [unicode(item) for item in args]
        for segment in segments:
            self.assertTrue(segment in cache_key)
    
