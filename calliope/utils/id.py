from typing import Callable
from cuid2 import cuid_wrapper

create_cuid: Callable[[], str] = cuid_wrapper()
