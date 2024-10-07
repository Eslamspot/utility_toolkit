import functools
import json
import logging
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

import psutil

# List of expected secret keys/names including AWS specific items
secret_items = [
    'password',
    'api_key',
    'private_key',
    'secret_key',
    'access_token',
    'refresh_token',
    'credential',
    'encryption_key',
    'aws_secret_access_key',
    'aws_access_key_id',
    'aws_session_token',
    's3_access_key',
    's3_secret_key',
    'config',
    'configurations',
    'configuration',
    'credentials',
]


def make_serializable(obj):
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: make_serializable(value) for key, value in obj.items()}
    else:
        return str(obj)


def format_duration(duration):
    from datetime import timedelta
    # Convert duration to timedelta
    duration_td = timedelta(seconds=duration)

    # Extract hours, minutes, and seconds
    hours, remainder = divmod(duration_td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format the duration string
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or (hours == 0 and minutes == 0):
        parts.append(f"{seconds:.2f}s")

    return " ".join(parts)


# Define a custom formatter to add colors
class CustomFormatter(logging.Formatter):
    """
    A custom formatter that adds colors to log messages based on their level.
    """
    grey = "\x1b[38;20m"
    green = "\x1b[32;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


# Create handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(CustomFormatter())

local_log_file_path = Path('outputs/logs/logs.log')
local_log_file_path.parent.mkdir(exist_ok=True, parents=True)

file_handler = logging.FileHandler(local_log_file_path)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Configure the root logger
logging.basicConfig(
    # level=logging.INFO,
    level=logging.DEBUG,
    handlers=[console_handler, file_handler],
)


def log_decorator(secrets=None):
    """
      A decorator that logs function calls, their arguments, and performance metrics.

      Args:
          secrets (list, optional): A list of argument names to be masked in the logs.
                                    Defaults to the predefined secret_items list.

      Returns:
          function: The decorated function with logging functionality.

      Example:
          @log_decorator(secrets=['password'])
          ... def login(username, password):
          ...     # Function implementation
          ...     return "Login successful"

          result = login("user123", "secretpass")
          # This will log something like:
          # {"function": "login", "args": ["user123"], "kwargs": {"password": "***"},
          #  "duration": "0.01", "cpu_usage": "0.5%", "memory_usage": "0.1%", "thread": "MainThread"}
      """
    if not secrets:
        secrets = secret_items

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)

            # Mask secrets
            masked_args = mask_secrets(args, secrets)
            masked_kwargs = mask_secrets(kwargs, secrets)

            start_time = time.time()
            start_process = psutil.Process()
            start_cpu_times = start_process.cpu_times()

            try:
                result = func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {str(e)}")
                raise
            finally:
                end_time = time.time()
                end_cpu_times = start_process.cpu_times()

            duration = end_time - start_time
            cpu_usage = sum(end_cpu_times) - sum(start_cpu_times)
            memory_usage = start_process.memory_percent()

            log_data = {
                "function": func.__name__,
                "args": make_serializable(masked_args),
                "kwargs": make_serializable(masked_kwargs),
                "duration": format_duration(duration),
                "cpu_time": f"{cpu_usage:.2f}",
                "memory_usage": f"{memory_usage:.2f}%",
                "thread": threading.current_thread().name,
            }

            logger.info(json.dumps(log_data))

            return result

        return wrapper

    return decorator


def mask_secrets(data, secrets):
    """
  Recursively mask secret values in data structures.

  Args:
      data: The data structure to mask secrets in.
      secrets (list): A list of keys to be considered as secrets.

  Returns:
      The data structure with secrets masked.

  Example:
      data = {"username": "user123", "password": "secretpass", "nested": {"api_key": "12345"}}
      masked_data = mask_secrets(data, ['password', 'api_key'])
      print(masked_data)
      {'username': 'user123', 'password': '***', 'nested': {'api_key': '***'}}
  """
    if isinstance(data, dict):
        return {k: "***" if k in secrets else mask_secrets(v, secrets) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return type(data)(mask_secrets(v, secrets) for v in data)
    else:
        return data


def class_log_decorator(exclude=None):
    """
      A decorator to apply logging to all methods of a class, except those specified.

      Args:
          exclude (list, optional): A list of method names to exclude from logging.
                                    Defaults to None.

      Returns:
          function: A class decorator that applies the logging decorator to all
                    methods in the class except those in the `exclude` list.

      Example:
          @class_log_decorator(exclude=['internal_method'])
          ... class UserManager:
          ...     def create_user(self, username, password):
          ...         # Method implementation
          ...         return f"User {username} created"
          ...
          ...     def internal_method(self):
          ...         # This method won't be logged
          ...         pass

          manager = UserManager()
          manager.create_user("newuser", "newpass")
          # This will log the create_user method call, but not internal_method
      """
    if exclude is None:
        exclude = []

    def class_decorator(cls):
        for name, method in cls.__dict__.items():
            if callable(method) and name not in exclude:
                setattr(cls, name, log_decorator()(method))
        return cls

    return class_decorator


def setup_logger(name, log_to_console, max_bytes=10 * 1024 * 1024, backup_count=5):
    """
      Set up a logger with both file and optional console logging.

      Args:
          name (str): The name of the logger.
          log_to_console (bool): Whether to log to console in addition to file.
          max_bytes (int, optional): Maximum size of each log file. Defaults to 10MB.
          backup_count (int, optional): Number of backup log files to keep. Defaults to 5.

      Returns:
          logging.Logger: Configured logger object.

      Example:
          logger = setup_logger("my_app_logger", log_to_console=True)
          logger.info("Application started")
          # This will log to both file and console
      """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # create rotating file handler
    file_handler = RotatingFileHandler(
        local_log_file_path, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    logger.addHandler(file_handler)

    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter())
        logger.addHandler(console_handler)

    return logger


# silent logger to just log to file and not print to console
silent_logger = setup_logger("silent_logger", log_to_console=False)

# # Examples:
# logger = setup_logger("my_app_logger", log_to_console=True)
# logger.info("Application started")
# logger.error("An error occurred")
# logger.debug("Debugging info")
# logger.warning("A warning message")
# logger.critical("A critical error")
