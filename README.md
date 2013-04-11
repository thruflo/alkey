# Alkey

[alkey][] is a [Redis][] backed [SQLAlchemy][] instance cache. When bound
to the SQLAlchemy session's [after_flush][] and [after_commit][] events,
it maintains a unique token against each model instance that changes whenever
the instance is updated or deleted.

This allows cache keys to be constructed (e.g.: using the
`alkey.cache.CacheKeyGenerator`) that are implicitly invalidated when
content changes, without having to manually keep track of what has changed
in application code.

The main algorithm is to record instances as changed when they're flushed to
the db in the session's dirty or deleted lists (identifiers in the format `alkey:tablename#row_id`, e.g.: `alkey:users#1`, are stored in a Redis set).
Then when a transaction commits, the tokens for each recorded instance are
invalidated. This means that a cache key containing the invalidated token
will miss, causing the cached value to be regenerated.

# Usage

You need to configure or provide a [redis client][] and bind the
`alkey.handle.handle_flush` and `alkey.handle.handle_commit` functions to
your SQLAlchemy Session's `after_flush` and `after_commit` events.

## Binding to Session Events

The simplest way is to use the `alkey.bind(session)` function, e.g.:
    
    import alkey
    from myapp import Session # the sqlalchemy session you're using
    
    alkey.bind(Session)

Or bind the events to their handlers manually, e.g.:

    from alkey import handle
    from myapp import Session
    from sqlalchemy import event
    
    event.listen(Session, 'after_flush', handle.handle_flush)
    event.listen(Session, 'after_commit', handle.handle_commit)

## Configuring a Redis Client

You can then generate cache keys using the `alkey.cache.CacheKeyGenerator`
utility, or retrieve the instance tokens yourself using `alkey.cache.get_token`.

Both of these require a redis client, which is got, by default, from the
`alkey.client.get_redis_client` function. This will look in the `os.environ`
or an `env` dictionary passed in for url / db and max connections configuration.

For example, if you have `REDIS_URL=redis://localhost:6379` in your environment
variables:

    from alkey.client import get_redis_client
    redis_client = get_redis_client()

Or to pass in config explicitly:

    env = {'REDIS_URL': 'redis://...', 'REDIS_DB': 0, 'REDIS_MAX_CONNECTIONS': 5}
    redis_client = get_redis_client(env=env)

Sidebar 1: generally, it's much better to have the redis config read in from the
`os.environ`, as the redis client factory is invoked in response to the session
events, i.e.: whilst you can pass in your own env to the factory, you'd have to
manually setup the session event handling to instantiate a client with that config,
rather than using the current event handlers as they are.

Sidebar 2: note that the max connections are used to create a per (sub)process
connection pool. Read the docstring in `redis.client.get_redis_config` for the
details or just be aware that your redis db needs to be able to accept
`max connections * processes * workers` connections, or your app will blow up
when you get some traffic.

## Generating Cache Keys

You can then instantiate a `CacheKeyGenerator` and pass in any of the following
types as key fragments:

* model instances
* model instance identifiers in the format `alkey:tablename#row_id`
* arbitrary values that can be coerced to a unicode string

E.g.:

    get_cache_key = CacheKeyGenerator(redis_client)
    key = get_cache_key(instance, 'alkey:users#1', 1, 'foo', {'bar': 'baz'})

Or you can directly get the instance token with `alkey.cache.get_token`, e.g.: using
either of the following:

    token = get_token(redis_client, instance)
    token = get_token(redis_client, 'alkey:users#1')

## Pyramid Integration

If you're writing a [Pyramid][] application, you can bind to the session events
just by including the package:

    config.include('alkey')

This will, by default, use the [pyramid_basemodel][] threadlocal scoped session.
To use a different session class, provide a dotted path to it as the
`alkey.session_cls` in your .ini settings, e.g.:

    alkey.session_cls=myapp.model.Session

An appropriately configured `alkey.cache.CacheKeyGenerator` instance will then
be available as ``request.cache_key``, e.g:

    key = request.cache_key(instance1, instance2, 'arbitrary string')

Or e.g.: in a [Mako template][]:

    <%page cached=True, cache_key=${request.cache_key(1, self.uri, instance)} />

[alkey]: http://github.com/thruflo/alkey
[Redis]: http://redis.io
[SQLAlchemy]: http://www.sqlalchemy.org/
[redis client]: https://github.com/andymccurdy/redis-py
[after_flush]: http://docs.sqlalchemy.org/ru/latest/orm/events.html#sqlalchemy.orm.events.SessionEvents.after_flush
[after_commit]: http://docs.sqlalchemy.org/ru/latest/orm/events.html#sqlalchemy.orm.events.SessionEvents.after_commit
[Pyramid]: http://docs.pylonsproject.org/projects/pyramid/en/latest
[Mako template]: http://www.makotemplates.org/
[pyramid_basemodel]: http://github.com/thruflo/pyramid_basemodel
