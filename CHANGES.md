
# 0.7

Also invalidate single relations: when an instance is invalidated, we
also look for any relations that the instance "belongs to" and we
invalidate their cache as well.

For example, given somethinf like:

    class Order(...):
        user_id = ...
        user = relation(...)

Previously when saving a new order like this:

    order = Order()
    user.orders.append(order)

This would bust the user cache -- because sqlalchemy knew that the user
had been edited and would include it in the session's `dirty` map. However
if you saved an order like this:

    order = Order(user_id=1234)

Sqlalchemy didn't pick up on the user relation. So, this release introduces
an *attempt* to pick up on these changes manually.

(At the time of writing, it's been tested successfully in a proprietary app
but the tests haven't been ported here).

# 0.6

Refactor the redis integration out to `pyramid_redis` and lose the `trace` module.

# 0.5

* wrap calls to redis with a resilient function that retries on a connection
  error and fails silently when its safe to do so

# 0.4.1

* rebuild sdist without logging

# 0.4

* provide a reified `request.redis` client, instead of calling `request.redis()`
  to get a redis client.

# 0.3.1

* add optional ``alkey.trace.trace_redis`` function to integrate the redis
  client with new relic monitoring.

# 0.3

* fix major bug causing cache keys that should be different to match by adding
  the `object_id` to the cache key argument, as well as the token value:
  this means that keys generated with an instance argument will always be
  unique to that instance (instead of previously matching an instance edited
  in the same commit)

# 0.2.3

* bug fix model class write tokens
* provide (optional) `request.cache_manager`

# 0.2.2

* maintain table write tokens, e.g.: `alkey:users#*`.

# 0.2.1

* namespace the global write token to `alkey:*#*`.

# 0.2

* only invalidate tokens in response to instance changes recorded within a
  transaction that is committed successfully
* introduce the `'*#*'` global write token

# 0.1

Initial version.
