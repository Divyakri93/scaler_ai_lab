import logging
import sys

def setup_logging(verbose: bool = False) -> None:
    """
    Sets up the application logger with appropriate verbosity levels.
    Logs are written to stdout and are designed to avoid logging raw PII.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Reset root logger handlers to prevent duplicates
    root = logging.getLogger()
    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    root.addHandler(handler)
    root.setLevel(log_level)

    # Silence verbose logs from third-party libraries (like spaCy, urllib3, docx)
    logging.getLogger("spacy").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("docx").setLevel(logging.WARNING)
