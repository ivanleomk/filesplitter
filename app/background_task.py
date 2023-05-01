import inspect
import logging
import uuid
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


def background_task_wrapper(func: Callable) -> Callable:
    task_name = func.__name__

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> None:
        task_id = uuid.uuid4()

        func_args = inspect.signature(func).bind(*args, **kwargs).arguments
        func_args_str = ", ".join("{}={!r}".format(*item) for item in func_args.items())

        logger.info(f"[{task_id}] Started {task_name} with arguments: {func_args_str}")

        try:
            await func(*args, **kwargs)
            logger.info(f"[{task_id}] Finished {task_name} Successfully")
        except Exception as e:  # 4
            logger.error(f"[{task_id}] Failed Permanently {task_name} with error: {e}")
            # 5

    return wrapper
