
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