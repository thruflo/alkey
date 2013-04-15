# Alkey

[Alkey][] is a [Redis][] backed tool for generating cache keys that implicitly
update / invalidate when [SQLAlchemy][] model instances change, e.g.:

    from alkey.cache import get_cache_key_generator
    key_generator = get_cache_key_generator()
    
    # The `cache_key` will be invalidated when `instance1` or `instance2` change.
    cache_key = key_generator(instance1, instance2)

It can be used by any [SQLAlchemy][] application that has access to [Redis][].
Plus it has (optional) integration with the [Pyramid][] framework:
`config.include` the package and generate keys using, e.g.:

    cache_key = request.cache_key(request.context)

## How it Works

[Alkey][] works by binding to the SQLAlchemy session's [after_flush][] and
[after_commit][] events to maintain a unique token, in Redis, against every
model instance. As long as the model instance has a unique `id` property, this
token will change whenever the instance is updated or deleted. In addition,
Alkey maintains a global write token and a token against each database table.
You can use these to generate cache keys that invalidate:

* when an *instance* changes
* when a *table* changes; or
* when *anything* changes

The main algorithm is to record instances as changed when they're flushed to
the db in the session's new, dirty or deleted lists (identifiers in the format
`alkey:tablename#row_id`, e.g.: `alkey:users#1`, are stored in a Redis set).
Then, when the session's transaction is committed, the tokens for each recorded
instance (plus their table and the global write token) are updated. This means
that a cache key that contains the tokens will miss, causing the cached value
to be regenerated.

New tokens are generated when instances are looked up that are not already
in the cache. So keys will always be invalidated if you lose / flush your
Redis data.

> Note also that changes recorded during a transaction that's
subsequently rolled back will be discarded (i.e.: the tokens will not be updated)
*unless* the rolled-back transaction is a sub-transaction. In that case &mdash; if
your application code explicitly uses sub-transactions &mdash; rollbacks may lead
to unnecessary cache-misses.

## Configuring a Redis Client

[Alkey][] looks in the `os.environ` (i.e.: you need to provide
[environment variables][]) for a values to configure a [redis client][]:

* `REDIS_URL`: a connection string including any authenticaton information, e.g.:
  `redis://username:password@hostname:port`
* `REDIS_DB`: defaults to `0`
* `REDIS_MAX_CONNECTIONS`: the maximum number of connections for the client's
  connection pool (defaults to not set)

The parsing logic is intelligent enough to pick up environment variables
provided by popular [Heroku addons][] like `REDISTOGO_URL` and `OPENREDIS_URL`,
etc. Read the `alkey.client.get_redis_config` docstring for the gory details.
Alternatively, if you'd prefer to provide your own redis client, register an `alkey.interfaces.IRedisClientFactory` function or an
`alkey.interfaces.IRedisConnectionPool` instance. Read 
`alkey.client.get_redis_client` to see how.

## Binding to Session Events

Use the `alkey.events.bind` function, e.g.:
    
    from alkey import events
    from myapp import Session # the sqlalchemy session you're using
    
    events.bind(Session)

## Generating Cache Keys

You can then instantiate an `alkey.cache.CacheKeyGenerator` and call it with
any of the following types as positional arguments to generate a cache key:

* SQLAlchemy model instances
* model instance identifiers in the format `alkey:tablename#row_id`
* SQLAlchemy model classes
* model class identifiers in the format `alkey:tablename#*`
* the `alkey.constants.GLOBAL_WRITE_TOKEN`, which has the value `alkey:*#*`
* arbitrary values that can be coerced to a unicode string

E.g. using the `alkey.cache.get_cache_key_generator` factory to instantiate:

    from alkey.cache import get_cache_key_generator
    
    key_generator = get_cache_key_generator()
    cache_key = key_generator(instance, 'alkey:users#1', 1, 'foo', {'bar': 'baz'})

Or, for example, imagine you have a `users` table, of which `user` is an instance
with an `id` of `1`:

    # Invalidate when this user changes.
    cache_key = key_generator(user)
    cache_key = key_generator('alkey:users#1')

    # Invalidate when any user is inserted, updated or deleted.
    cache_key = key_generator(user.__class__)
    cache_key = key_generator('alkey:users#*')

    # Invalidate when any instance of any type is inserted, updated or deleted.
    cache_key = key_generator('alkey:*#*')

Or you can directly get the instance token with `alkey.cache.get_token`, e.g.:

    from alkey.cache import get_token
    from alkey.client import get_redis_client
    
    redis_client = get_redis_client()
    
    token = get_token(redis_client, user)
    token = get_token(redis_client, 'alkey:users#1')

## Pyramid Integration

If you're writing a [Pyramid][] application, you can bind to the session events
by just including the package:

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

## Tests

[Alkey][] has been developed and tested against Python2.7. To run the tests,
install `mock`, `nose` and `coverage` and either hack the `setUp` method in
`alkey.tests:IntegrationTest` or have a Redis db available at
`redis://localhost:6379`. Then, e.g.:

    $ nosetests alkey --with-doctest --with-coverage --cover-tests --cover-package alkey
    ..........................
    Name               Stmts   Miss  Cover   Missing
    ------------------------------------------------
    alkey                 11      0   100%   
    alkey.cache           74      0   100%   
    alkey.client          73      0   100%   
    alkey.constants        6      0   100%   
    alkey.events          12      0   100%   
    alkey.handle          76      0   100%   
    alkey.interfaces       6      0   100%   
    alkey.tests          184      0   100%   
    alkey.utils           30      0   100%   
    ------------------------------------------------
    TOTAL                472      0   100%   
    ----------------------------------------------------------------------
    Ran 26 tests in 0.566s
    
    OK

[alkey]: http://github.com/thruflo/alkey
[Redis]: http://redis.io
[SQLAlchemy]: http://www.sqlalchemy.org/
[redis client]: https://github.com/andymccurdy/redis-py
[after_flush]: http://docs.sqlalchemy.org/ru/latest/orm/events.html#sqlalchemy.orm.events.SessionEvents.after_flush
[after_commit]: http://docs.sqlalchemy.org/ru/latest/orm/events.html#sqlalchemy.orm.events.SessionEvents.after_commit
[Pyramid]: http://docs.pylonsproject.org/projects/pyramid/en/latest
[Mako template]: http://www.makotemplates.org/
[pyramid_basemodel]: http://github.com/thruflo/pyramid_basemodel
[environment variables]: http://blog.akash.im/per-project-environment-variables-with-forema
[Heroku addons]: https://www.google.co.uk/search?q=Heroku+addons+redis