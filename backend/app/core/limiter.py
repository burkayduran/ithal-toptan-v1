"""
Shared SlowAPI rate-limiter instance.

Import this wherever you need @limiter.limit(...) decorators.
main.py assigns this to app.state.limiter so SlowAPI's exception handler
can locate it when a RateLimitExceeded error is raised.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
