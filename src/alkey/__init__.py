# -*- coding: utf-8 -*-

"""Allow developers to include in a Pyramid application using
  ``config.include('alkey')``.
"""

from .cache import get_cache_key_generator
from .cache import get_cache_manager
from .client import get_redis_client
from .events import bind as bind_to_events

# Taken from zope.dottedname
def _resolve_dotted(name, module=None): #pragma: no cover
    name = name.split('.')
    if not name[0]:
        if module is None:
            raise ValueError("relative name without base module")
        module = module.split('.')
        name.pop(0)
        while not name[0]:
            module.pop()
            name.pop(0)
        name = module + name
    used = name.pop(0)
    found = __import__(used)
    for n in name:
        used += '.' + n
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)
    return found


def includeme(config, bind=None, resolve=None):
    """Pyramid configuration for this package.
      
      Setup::
      
          >>> from mock import Mock
          >>> mock_config = Mock()
          >>> mock_config.registry.settings = {}
          >>> mock_bind = Mock()
          >>> mock_resolve = Mock()
      
      Binds session events to the pyramid_basemodel.Session by default::
      
          >>> mock_resolve.return_value = '<Session>'
          >>> includeme(mock_config, bind=mock_bind, resolve=mock_resolve)
          >>> mock_resolve.assert_called_with('pyramid_basemodel.Session')
          >>> mock_bind.assert_called_with('<Session>')
      
      Unless ``alkey.session_cls`` is provided in the ``settings``::
      
          >>> mock_config.registry.settings = {'alkey.session_cls': 'mock.Mock'}
          >>> includeme(mock_config, bind=mock_bind, resolve=mock_resolve)
          >>> mock_resolve.assert_called_with('mock.Mock')
      
      Adds ``cache_key``, ``cache_manager`` and ``redis`` to the request::
      
          >>> add_method = mock_config.add_request_method
          >>> add_method.assert_any_call(get_redis_client, 'redis')
          >>> add_method.assert_any_call(get_cache_key_generator, 'cache_key',
          ...         reify=True)
          >>> add_method.assert_any_call(get_cache_manager, 'cache_manager',
          ...         reify=True)
      
    """
    
    # Compose.
    if bind is None: #pragma: no cover
        bind = bind_to_events
    if resolve is None: #pragma: no cover
        resolve = _resolve_dotted
    
    # Get the session class.
    settings = config.registry.settings
    dotted_path = settings.get('alkey.session_cls', 'pyramid_basemodel.Session')
    session_cls = resolve(dotted_path)
    
    # Bind to events.
    bind(session_cls)
    
    # Extend the request.
    config.add_request_method(get_redis_client, 'redis')
    config.add_request_method(get_cache_key_generator, 'cache_key', reify=True)
    config.add_request_method(get_cache_manager, 'cache_manager', reify=True)

