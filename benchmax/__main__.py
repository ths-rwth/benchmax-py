import logging
import sys

import cli
from BenchmaxException import BenchmaxException


def main():
    """Main entry point for benchmax."""
    try:
        cli.benchmax_main()
    except MemoryError:
        logging.error("Memory exhausted!")
    except KeyboardInterrupt:
        logging.error("User abort!")
    except BenchmaxException as e:
        print(e)
    return 1


if __name__ == "__main__":
    sys.exit(main())
