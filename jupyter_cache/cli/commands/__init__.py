try:
    import click_completion
except ImportError:
    pass
else:
    # Activate the completion of parameter types provided by the click_completion package
    click_completion.init()

from .cmd_cache import *  # noqa: F401,F403,E402
from .cmd_config import *  # noqa: F401,F403,E402
from .cmd_exec import *  # noqa: F401,F403,E402
from .cmd_project import *  # noqa: F401,F403,E402
