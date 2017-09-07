import logging
from argparse import ArgumentParser

import cv2

from config_resolver import Config
from processing import detect
from raspicam.camera import PiCamera, USBCam
from raspicam.source import FileReader
from raspicam.storage import NullStorage, Storage
from raspicam.webui import make_app

LOG = logging.getLogger(__name__)


class Application:

    def __init__(self):
        self.config = None
        self.initialised = False
        self.frames = iter([])
        self.mask = None
        self.storage = NullStorage()
        self.__verbosity = 0
        self.__stream = []

    def init(self, cli_args=None):
        cli_args = cli_args or []
        if not self.initialised:
            args = self.parse_args(cli_args)
            self.config = Config('exhuma', 'raspicam', require_load=True)
            self.storage = Storage.from_config(self.config)
            self.frames = self._get_framesource()
            self.mask = self.config.get('detection', 'mask', default=None)
            self.verbosity = args.verbosity
            self.__stream = detect(self.frames, self.storage, self.mask,
                                   debug=args.debug)
            self.initialised = True
            LOG.info('Application successfully initialised.')
            return args

    def parse_args(self, cli_args):
        parser = ArgumentParser()
        parser.add_argument('ui', help='Chose a UI. One of [gui, web, cli]')
        parser.add_argument('-d', '--debug', action='store_true', default=False,
                            help='Enable debug mode')
        parser.add_argument('-v', dest='verbosity', action='count', default=0,
                            help='Increase log verbosity')
        return parser.parse_args(cli_args)

    @property
    def verbosity(self):
        return self.__verbosity

    @verbosity.setter
    def verbosity(self, value):
        self.__verbosity = value
        logger = logging.getLogger()
        logger.setLevel(max(0, logging.CRITICAL - (10 * value)))

    def _get_framesource(self):
        kind = self.config.get('framesource', 'kind').lower()
        raw_arguments = self.config.get('framesource', 'arguments', default='')
        if raw_arguments.strip():
            arguments = [arg.strip() for arg in raw_arguments.split(',')]
        else:
            arguments = []
        if kind == 'usb':
            if len(arguments) == 0:
                index = -1
            else:
                index = int(arguments[0])
            return USBCam(index).frame_generator()
        elif kind == 'raspberrypi':
            return PiCamera().frame_generator()
        elif kind == 'file':
            filename = arguments[0]
            return FileReader(filename).frame_generator()
        else:
            raise ValueError('%s is an unsupported frame source!')

    def run_gui(self):
        for frame in self.__stream:
            cv2.imshow('RaspiCam Main Window', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        # When everything done, release the capture
        # cap.release()
        cv2.destroyAllWindows()

    def run_webui(self):
        app = make_app(self.__stream, self.config)
        app.run(host='0.0.0.0', debug=True, threaded=True)

    def run_cli(self):
        for frame in self.__stream:
            pass

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.CRITICAL)
    app = Application()
    args = app.init(sys.argv[1:])

    if args.ui == 'cli':
        app.run_cli()
    elif args.ui == 'webui':
        app.run_webui()
    elif args.ui == 'gui':
        app.run_gui()
    else:
        print("ui must be cli, webui or gui")
