"""
This module contains the main application object.
"""

import logging
import sys
from argparse import ArgumentParser

import cv2
from config_resolver import Config

import raspicam
from raspicam.pipeline import DefaultPipeline
from raspicam.processing import detect
from raspicam.source import PiCamera, USBCam, FileReader
from raspicam.storage import Storage
from raspicam.webui import make_app

LOG = logging.getLogger(__name__)


class Application:
    '''
    The main application.

    It offers three entry-points:

    * run: A simple delegate to the other "run_" methods. The correct method is
        determined by inspecting the CLI arguments (or customised arguments
        passed to :py:meth:`~.Application.init`).
    * run_cli: Run the application on the CLI and start reading frames and
        detect motion. This is usually the entry-point you want to run!
    * run_gui: This will run a graphical UI which was originally implemented for
        debugging and development.
    * run_webui: A simple web-ui. Also implemented originally to offer a way to
        access files stored in the application storage.
    '''

    def __init__(self):
        self.config = None
        self.initialised = False
        self.frames = iter([])
        self.__cli_args = None
        self.__verbosity = 0
        self.__stream = []

    def init(self, cli_args=None, custom_pipeline=None):
        '''
        Initialises the application and parses CLI arguments.

        :param cli_args: CLI arguments
        :param custom_pipeline: An instance of
            :py:class:`raspicam.pipeline.DetectionPipeline`. If left to
            ``None``, :py:class:`raspicam.pipeline.DefaultPipeline` will be
            used.
        '''
        cli_args = cli_args or sys.argv[1:]
        if not self.initialised:
            self.__cli_args = parse_args(cli_args)
            self.config = Config('exhuma', 'raspicam', require_load=True)
            self.frames = self._get_framesource()
            storage = Storage.from_config(self.config)
            mask = self.config.get('detection', 'mask', default=None)
            pipeline = custom_pipeline or DefaultPipeline(mask, storage)
            self.__stream = detect(self.frames, debug=self.__cli_args.debug,
                                   detection_pipeline=pipeline)
            self.verbosity = self.__cli_args.verbosity
            self.initialised = True
            LOG.info('Application successfully initialised.')
        else:
            LOG.debug('Appliation is already initialised. Skipping init!')
        return self.__cli_args

    @property
    def verbosity(self):
        '''
        Returns the current application verbosity level
        '''
        return self.__verbosity

    @verbosity.setter
    def verbosity(self, value):
        '''
        Sets the application verbosity level.

        :param value: A simple verbosity level. Currently supports the values
        from 0 to 5 (inclusive).
        '''
        self.__verbosity = value
        logger = logging.getLogger()
        logger.setLevel(max(0, logging.CRITICAL - (10 * value)))

    def _get_framesource(self):
        '''
        Parsed the frame source from the config and returns an appropriate
        generator.

        The returned genereator will return a new video frame on each iteration.
        '''
        kind = self.config.get('framesource', 'kind').lower()
        raw_arguments = self.config.get('framesource', 'arguments', default='')
        if raw_arguments.strip():
            arguments = [arg.strip() for arg in raw_arguments.split(',')]
        else:
            arguments = []
        if kind == 'usb':
            if arguments:
                index = int(arguments[0])
            else:
                index = -1
            return USBCam(index).frame_generator()
        elif kind == 'raspberrypi':
            return PiCamera().frame_generator()
        elif kind == 'file':
            filename = arguments[0]
            return FileReader(filename).frame_generator()
        else:
            raise ValueError('%s is an unsupported frame source!')

    def run(self):
        '''
        Parses CLI args and delegates to the appropriate UI.
        '''
        args = self.init()
        if args.ui == 'cli':
            self.run_cli()
        elif args.ui == 'webui':
            self.run_webui()
        elif args.ui == 'gui':
            self.run_gui()
        else:
            print("ui must be cli, webui or gui")

    def run_gui(self):
        '''
        Runs the application as a simple GUI.
        '''
        for frame in self.__stream:
            cv2.imshow('RaspiCam Main Window', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        # When everything done, release the capture
        # cap.release()
        cv2.destroyAllWindows()

    def run_webui(self):
        '''
        Starts a simple web interface. Frames will *not* be automatically be
        read in this mode! If exists to offer a simple way to access stored
        files.

        It *can* be started alongside either the GUI or CLI mode.
        '''
        app = make_app(self.__stream, self.config)
        app.run(host='0.0.0.0', debug=True, threaded=True)

    def run_cli(self):
        '''
        Runs the application in CLI mode.
        '''
        for _ in self.__stream:
            pass


def parse_args(cli_args):
    '''
    Parse CLI arguments and return the parsed object.
    '''
    parser = ArgumentParser()
    parser.add_argument('ui', help='Chose a UI. One of [gui, web, cli]')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='Enable debug mode')
    parser.add_argument('-v', dest='verbosity', action='count', default=0,
                        help='Increase log verbosity')
    parser.add_argument('--version', action='store_true', default=False,
                        help='Show version and exit')
    return parser.parse_args(cli_args)


def main():
    '''
    Main entry-point of the application.
    '''

    logging.basicConfig(level=logging.CRITICAL)
    app = Application()
    parsed_args = app.init()
    if parsed_args.version:
        print('raspicam v%s' % raspicam.__version__)
        return 0
    app.run()


if __name__ == '__main__':
    main()
