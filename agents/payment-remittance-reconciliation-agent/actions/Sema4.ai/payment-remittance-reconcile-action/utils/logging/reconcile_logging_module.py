import io
import logging
import logging.config
import os
import traceback
import sys
from utils.commons.path_utils import get_full_path


def configure_logging(
    logger_name=__name__, log_config_filename="agent-validate-reconcile.conf"
):
    """
    Configure logging using a configuration file with environment-aware path resolution.

    Args:
        logger_name (str): Name of the logger (defaults to module name)
        log_config_filename (str): Name of the logging config file

    Returns:
        logging.Logger: Configured logger instance
    """
    try:
        # Use get_full_path to resolve the config file path
        config_path = get_full_path(log_config_filename)

        # Check if the file exists
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Print the content of the config file for debugging
        with open(config_path, "r") as f:
            print(f"Content of {config_path}:")
            print(f.read())

        logging.config.fileConfig(config_path)
        logger = logging.getLogger(logger_name)
        logger.info(f"Logging configured using config file: {config_path}")

    except Exception as e:
        traceback_buffer = io.StringIO()
        traceback.print_exc(file=traceback_buffer)
        traceback_str = traceback_buffer.getvalue()

        # Fallback to basic configuration
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )
        logger = logging.getLogger(logger_name)
        logger.warning(
            f"Failed to configure logging using {config_path}. "
            f"Using default configuration. Traceback: {traceback_str}"
        )

    return logger
