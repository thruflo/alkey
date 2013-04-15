# -*- coding: utf-8 -*-

"""Integration test for ``alkey``, testing with mock model instances /
  session events but a real redis db.
"""

import unittest
try: # pragma: no cover
    from mock import Mock
except ImportError: # pragma: no cover
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
    
    def makeInstanceClass(self, tablename='users'):
        """Return a mock model instance."""
        
        cls = Mock()
        cls.__tablename__ = tablename
        return cls
    
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
        record_changed(self.redis, 'session_id', [instance])
        
        # Invalidate tokens for changed instances. Aka a mock commit.
        invalidate_tokens(self.redis, 'session_id')
        
        # Get the token again.
        token2 = get_token(self.redis, instance)
        
        # It's changed.
        self.assertTrue(token1 != token2)
    
    def test_get_token_for_changed_instance_requires_same_session_id(self):
        """Instances changes will only be invalidated by a commit of the same
          session that flushed to record the change.
        """
        
        from alkey.cache import get_token
        from alkey.handle import record_changed
        from alkey.handle import invalidate_tokens
        
        # Get the current token.
        instance = self.makeInstance()
        token1 = get_token(self.redis, instance)
        
        # Record that the instance has changed. Aka a mock flush.
        record_changed(self.redis, 'session_1', [instance])
        
        # Invalidate tokens for changed instances. Aka a mock commit.
        invalidate_tokens(self.redis, 'session_2')
        
        # Get the token again.
        token2 = get_token(self.redis, instance)
        
        # It's not changed.
        self.assertTrue(token1 == token2)
    
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
        record_changed(self.redis, 'session_id', [instance])
        
        # Invalidate tokens for changed instances. Aka a mock commit.
        invalidate_tokens(self.redis, 'session_id')
        
        # Get the token again.
        token2 = get_token(self.redis, instance)
        
        # It's changed.
        self.assertTrue(token1 != token2)
        
        # Pause.
        time.sleep(0.1)
        
        # Get it again, its not changed.
        token3 = get_token(self.redis, instance)
        self.assertTrue(token2 == token3)
    
    def test_clears_token_for_changed_instance_after_rollback(self):
        """A cached token should not be invalidated after a rollback."""
        
        import time
        from alkey.cache import get_token
        from alkey.handle import clear_changed
        from alkey.handle import record_changed
        from alkey.handle import invalidate_tokens
        
        # Get the current token.
        instance = self.makeInstance()
        token1 = get_token(self.redis, instance)
        
        # Record that the instance has changed. Aka a mock flush.
        record_changed(self.redis, 'session_id', [instance])
        
        # Clear the changed set. Aka a mock rollback.
        clear_changed(self.redis, 'session_id')
        
        # Invalidate tokens for changed instances. Aka a mock commit.
        invalidate_tokens(self.redis, 'session_id')
        
        # Get the token again.
        token2 = get_token(self.redis, instance)
        
        # It's not changed.
        self.assertTrue(token1 == token2)
    
    def test_changed_instance_invalidates_class_token(self):
        """A class token changes whenever any instance is updated."""
        
        import time
        from alkey.cache import get_token
        from alkey.handle import record_changed
        from alkey.handle import invalidate_tokens
        
        # Get the current class token.
        instance = self.makeInstance()
        instance_class = self.makeInstanceClass()
        token1 = get_token(self.redis, instance_class)
        
        time.sleep(0.1)
        
        # The token hasn't changed.
        token2 = get_token(self.redis, instance_class)
        self.assertTrue(token1 == token2)
        
        # Record that the instance has changed. Aka a mock flush.
        record_changed(self.redis, 'session_id', [instance])
        # Invalidate tokens for changed instances. Aka a mock commit.
        invalidate_tokens(self.redis, 'session_id')
        
        # Now the class token has changed.
        token3 = get_token(self.redis, instance_class)
        
        # It's changed.
        self.assertTrue(token2 != token3)
    
    def test_any_commit_invalidates_global_write_token(self):
        """The global token changes when any changes are commited."""
        
        import time
        from alkey.cache import get_token
        from alkey.constants import GLOBAL_WRITE_TOKEN
        from alkey.handle import record_changed
        from alkey.handle import invalidate_tokens
        
        # Get the global write token.
        token1 = get_token(self.redis, GLOBAL_WRITE_TOKEN)
        
        # Pause.
        time.sleep(0.1)
        
        # Get the global token again.
        token2 = get_token(self.redis, GLOBAL_WRITE_TOKEN)
        
        # It's not changed.
        self.assertTrue(token1 == token2)
        
        # Record and commit an instance change.
        instance = self.makeInstance()
        record_changed(self.redis, 'session_id', [instance])
        invalidate_tokens(self.redis, 'session_id')
        
        # Get the global token again.
        token3 = get_token(self.redis, GLOBAL_WRITE_TOKEN)
        
        # It's changed.
        self.assertTrue(token2 != token3)
    
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
    
    def test_get_cache_key_multiple_instances(self):
        """Getting a cache key works for the global write token."""
        
        from alkey.cache import get_cache_key_generator
        from alkey.cache import get_token
        from alkey.constants import GLOBAL_WRITE_TOKEN
        
        token = get_token(self.redis, GLOBAL_WRITE_TOKEN)
        
        generator = get_cache_key_generator(None)
        cache_key = generator(GLOBAL_WRITE_TOKEN)
        
        self.assertTrue(cache_key == token)
    
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
        """Objects are coerced to a unicode string."""
        
        from alkey.cache import get_cache_key_generator
        
        generator = get_cache_key_generator(None)
        cache_key = generator({'foo': 'bar'})
        
        self.assertTrue(cache_key == u"{'foo': 'bar'}")
    
    def test_model_cls_segment(self):
        """Model classes return the write token for that table."""
        
        from alkey.cache import get_cache_key_generator
        from alkey.utils import get_stamp
        
        class Model(object):
            __tablename__ = 'blathers'
            id = '<Column>'
        
        generator = get_cache_key_generator(None)
        cache_key = generator(Model)
        
        stamp = get_stamp()
        self.assertTrue(cache_key.startswith(stamp.split(' ')[0]))
    
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
    

