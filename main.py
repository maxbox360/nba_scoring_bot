import argparse
import logging

from dotenv import load_dotenv

from nba.nba_main import NBA
from utils.settings import configure_logging, get_env


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the NBA scoring bot")
    parser.add_argument('--debug', action='store_true', help='Enable debugging mode')
    args = parser.parse_args()

    load_dotenv()
    configure_logging()
    logger.info("Starting NBA Bluesky bot")

    username = get_env('BLUESKY_USERNAME')
    password = get_env('BLUESKY_PASSWORD')

    nba = NBA(username=username, password=password, debug=args.debug)
    nba.main()
