import logging
import os


RUNTIME_LOGGER = logging.getLogger("pythonagents.runtime")


def configure_runtime_logger(level: str | None = None) -> None:
    """Configure global runtime logging level and default log format."""
    normalized_level = (level or os.getenv("AGENT_LOG_LEVEL", "INFO")).upper()
    numeric_level = getattr(logging, normalized_level, logging.INFO)

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )

    RUNTIME_LOGGER.setLevel(numeric_level)
