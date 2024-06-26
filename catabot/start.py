import logging
import os
from argparse import ArgumentParser
from logging.handlers import TimedRotatingFileHandler

from catabot.tgbot import TelegramBot


class CataBot:

    def __init__(self):
        self.args = self._parse_args()
        self._init_logger(self.args.logfile, self.args.loglevel)
        self.tgbot = TelegramBot(self._get_bot_token(), self.args.clean, self.args.debug)

    def _parse_args(self):
        parser = ArgumentParser(description="CDDA_Bot: CDDA itembrowser for Telegram")

        # Logfile path
        parser.add_argument(
            "-log",
            dest="logfile",
            help="path to logfile",
            default=os.path.join('log', 'catabot.log'),
            required=False,
            metavar="FILE")

        # Log level
        parser.add_argument(
            "-lvl",
            dest="loglevel",
            type=int,
            choices=[0, 10, 20, 30, 40, 50],
            help="Disabled, Debug, Info, Warning, Error, Critical",
            default=30,
            required=False)

        # Save logfile
        parser.add_argument(
            "--no-logfile",
            dest="savelog",
            action="store_false",
            help="don't save logs to file",
            required=False,
            default=True)

        # Clean pending updates
        parser.add_argument(
            "--clean",
            dest="clean",
            action="store_true",
            help="clean any pending telegram updates before polling",
            required=False,
            default=False)

        # Bot token
        parser.add_argument(
            "-token",
            dest="token",
            help="Telegram bot token",
            required=False,
            default=None)

        # Debug mode
        parser.add_argument(
            "--debug",
            dest="debug",
            help="run TeleBot in debug mode",
            action="store_true",
            required=False,
            default=False,
        )

        return parser.parse_args()

    # Configure logging
    def _init_logger(self, logfile, level):
        logger = logging.getLogger()
        logger.setLevel(level)

        log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'

        # Log to console
        console_log = logging.StreamHandler()
        console_log.setFormatter(logging.Formatter(log_format))
        console_log.setLevel(level)

        logger.addHandler(console_log)

        # Save logs if enabled
        if self.args.savelog:
            # Create 'log' directory if not present
            log_path = os.path.dirname(logfile)
            if not os.path.exists(log_path):
                os.makedirs(log_path)

            file_log = TimedRotatingFileHandler(
                logfile,
                when="H",
                encoding="utf-8")

            file_log.setFormatter(logging.Formatter(log_format))
            file_log.setLevel(level)

            logger.addHandler(file_log)

    # Read bot token from file or args
    def _get_bot_token(self):
        if self.args.token:
            return self.args.token

        try:
            token_file = os.path.join('config', 'token.txt')
            if os.path.isfile(token_file):
                with open(token_file, 'r') as file:
                    return file.read().strip()
            else:
                exit(f"ERROR: No token file found at '{token_file}'")
        except KeyError as e:
            cls_name = f"Class: {type(self).__name__}"
            logging.error(f"{repr(e)} - {cls_name}")
            exit("ERROR: Can't read bot token")

    def start(self):
        self.tgbot.bot_start_polling()
        self.tgbot.bot_idle()
