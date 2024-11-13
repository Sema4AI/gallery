import io
import logging
import logging.config
import os
import traceback
import sys

ACTION_PACKAGE = "payment-remittance-validate-actions"


def configure_logging(
    logger_name=__name__, log_config_path="logging-validate-actions.conf"
):
    current_dir = os.getcwd()

    # Determine if it's a production or action package environment
    if "actions" in current_dir or "gallery" in current_dir:
        # Opened as action package
        config_path = log_config_path
    else:
        # Opened as a different environment, perhaps production
        config_path = os.path.join(
            current_dir, "actions", "MyActions", ACTION_PACKAGE, log_config_path
        )

    try:
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
            f"Failed to configure logging using {config_path}. Using default configuration. Traceback string: {traceback_str}"
        )

    return logger
