# Alkey

[Alkey][] is a [Redis][] backed tool for generating cache keys that implicitly
update / invalidate when [SQLAlchemy][] model instances change. It can be used
by any [SQLAlchemy][] application that has access to [Redis][]. Plus it has
(optional) integration with the [Pyramid][] framework: `config.include` the
package and generate keys using, e.g.:

    cache_key = request.cache_key('template uri', request.context)

[Alkey][] works by binding to the SQLAlchemy session's [after_flush][] and
[after_commit][] events to maintain a unique token against every model instance.
This token changes whenever a model instance is updated or deleted.

The algorithm is to record instances as changed when they're flushed to the db
in the session's dirty or deleted lists (identifiers in the format
`Alkey:tablename#row_id`, e.g.: `Alkey:users#1`, are stored in a Redis set).
Then when the flushed changes are committed, the tokens for each recorded
instance are updated. This means that a cache key constructed using the
instance tokens will miss, causing the cached value to be regenerated.

(Tokens are also updated if missing, so keys will also be invalidated if you
lose / flush your Redis data).

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
* arbitrary values that can be coerced to a unicode string

E.g. using the `alkey.cache.get_cache_key_generator` factory to instantiate:

    from alkey.cache import get_cache_key_generator
    
    key_generator = get_cache_key_generator()
    cache_key = key_generator(instance, 'alkey:users#1', 1, 'foo', {'bar': 'baz'})

Or you can directly get the instance token with `alkey.cache.get_token`, e.g.: using
either of the following:

    token = get_token(redis_client, instance)
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
    ....................
    Name               Stmts   Miss  Cover   Missing
    ------------------------------------------------
    alkey                 11      0   100%   
    alkey.cache           69      0   100%   
    alkey.client          68      0   100%   
    alkey.events          10      0   100%   
    alkey.handle          38      0   100%   
    alkey.interfaces       6      0   100%   
    alkey.tests          119      0   100%   
    alkey.utils           20      0   100%   
    ------------------------------------------------
    TOTAL                341      0   100%   
    ----------------------------------------------------------------------
    Ran 20 tests in 0.346s
    
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