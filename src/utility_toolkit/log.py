import functools
import logging
import os
import time
from pathlib import Path


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


# Define a custom formatter to add colors
class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    green = "\x1b[32;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    bold = "\033[1m"
    grey_bold = bold + grey
    green_bold = bold + green
    yellow_bold = bold + yellow
    red_bold = bold + red

    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + bold + format + reset,
        logging.INFO: green + bold + format + reset,
        logging.WARNING: yellow + bold + format + reset,
        logging.ERROR: red + bold + format + reset,
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
    A decorator that logs the execution of a function, including its arguments and execution time.
    Optionally masks specified secret arguments.

    Args:
        secrets (list, optional): A list of argument names to be masked in the logs. Defaults to None.

    Returns:
        function: The decorated function with logging functionality.

    Example:
        @log_decorator(secrets=['password'])
        def my_function(username, password):
            pass
    """
    if not secrets:
        secrets = secret_items

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get argument names
            arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]

            # Construct a dictionary of arguments and their values
            arguments = dict(zip(arg_names, args))
            # Add keyword arguments to the dictionary
            arguments.update(kwargs)

            # Mask secret variables
            for secret in secrets:
                if secret in arguments:
                    arguments[secret] = "***"

            # Create a string representation of arguments
            args_repr = [f"{key}={value!r}" for key, value in arguments.items() if key != 'self']

            function_arguments = ", ".join(args_repr)

            start_time = time.time()
            logging.info(f"Starting '{func.__name__}' with arguments: {function_arguments}")

            result = func(*args, **kwargs)

            end_time = time.time()
            duration = end_time - start_time
            # if result too long, log the length of the result instead
            if len(str(result)) > 50:
                logging.info(f"Finished '{func.__name__}' in {duration:.2f} secs with result length: {len(str(result))}")
            else:
                logging.info(f"Finished '{func.__name__}' in {duration:.2f} secs with result: {result!r}")

            return result

        return wrapper

    return decorator


def class_log_decorator(exclude=None):
    """
    A decorator to log method calls in a class. This decorator can be used to 
    automatically apply a logging decorator to all methods in a class, except 
    those specified in the `exclude` list.

    Args:
        exclude (list, optional): A list of method names to exclude from logging. 
                                  Defaults to None.

    Returns:
        function: A class decorator that applies the logging decorator to all 
                  methods in the class except those in the `exclude` list.

    Example:
        >>> @class_log_decorator(exclude=['method_to_exclude'])
        ... class MyClass:
        ...     def method1(self):
        ...         pass
        ...     
        ...     def method2(self):
        ...         pass
        ...     
        ...     def method_to_exclude(self):
        ...         pass
        ...
        >>> obj = MyClass()
        >>> obj.method1()  # This will be logged
        >>> obj.method2()  # This will be logged
        >>> obj.method_to_exclude()  # This will not be logged
    """
    if exclude is None:
        exclude = []

    def class_decorator(cls):
        for name, method in cls.__dict__.items():
            if callable(method) and name not in exclude:
                setattr(cls, name, log_decorator()(method))
        return cls

    return class_decorator


def setup_logger(name, log_to_console):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # or whatever level you want
    logger.propagate = False  # Prevent the log messages from being passed to the root logger

    # create file handler
    file_handler = logging.FileHandler(local_log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    logger.addHandler(file_handler)

    if log_to_console:
        # create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter())
        logger.addHandler(console_handler)

    return logger


# silent logger to just log to file and not print to console
silent_logger = setup_logger("silent_logger", log_to_console=False)

# Examples:
# logging.debug('Quick zephyrs blow, vexing daft Jim.')
# logging.info('How quickly daft jumping zebras vex.')
# logging.warning('Jail zesty vixen who grabbed pay from quack.')
# logging.error('The five boxing wizards jump quickly.')


# Example usage with a class
# @class_log_decorator
# class MathOperations:
#     def add(self, x, y, password=None):
#         return x + y
#
#     def multiply(self, x, y):
#         return x * y
#
#
# math_ops = MathOperations()
# math_ops.add(5, 3, password="secret")  # This will be logged with "***" for the password
# math_ops.multiply(5, 3)  # This will be logged normally

# Example usage with modified class_log_decorator
# @class_log_decorator(exclude=['multiply'])
# class MathOperations:
#     def add(self, x, y, password=None):
#         # Function body
#         return x + y
#
#     def multiply(self, x, y):
#         # Function body
#         return x * y
# math_operations = MathOperations
# math_operations.add(x=2,y=3)
# math_operations.multiply(x=10,y=30)

# Example usage with log_decorator
# @log.class_log_decorator(exclude=["multiply"])
