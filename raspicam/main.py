"""
This module contains the main application object.
"""

import logging
import sys
from argparse import ArgumentParser

import cv2
from threading import Thread
from time import sleep

from config_resolver import Config

import raspicam
from raspicam.pipeline import DefaultPipeline, pusher
from raspicam.processing import detect
from raspicam.source import PiCamera, USBCam, FileReader
from raspicam.storage import Storage
from raspicam.web.colorize import colorize_werkzeug
from raspicam.webui import make_app

LOG = logging.getLogger(__name__)


class NullWeb:
    def shutdown(self):
        pass

    def join(self):
        pass

    def is_alive(self):
        return False


class GuiThread(Thread):

    def __init__(self, reader_thread):
        super().__init__()
        self._log = logging.getLogger(__name__ + '.gui')
        self.daemon = True
        self.__reader = reader_thread
        self.__keep_running = True

    def run(self):
        while self.__keep_running:
            frame = self.__reader.frame
            if frame is None:
                self._log.debug('No frame available yet. Waiting...')
                sleep(0.1)
                continue
            cv2.imshow('RaspiCam Main Window', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.__keep_running = False
        cv2.destroyAllWindows()

    def shutdown(self):
        self.__keep_running = False


class WebThread(Thread):

    def __init__(self, app):
        super().__init__()
        self._log = logging.getLogger(__name__ + '.web')
        self.__app = app
        self.daemon = True

    def run(self):
        self._log.info('Running Web Server')
        self.__app.run(host='0.0.0.0', threaded=True)

    def shutdown(self):
        import http.client
        conn = http.client.HTTPConnection("localhost", 5000)
        try:
            conn.request("POST", "/shutdown")
            res = conn.getresponse()
            if res.status != 200:
                self._log.error('Something went wrong sending the shutdown command to '
                        'the webui: %s', res.reason)
        except ConnectionRefusedError:
            LOG.info('Connection to web-thread lost. Shutdown successful!')


class ReaderThread(Thread):

    def __init__(self, stream):
        super().__init__()
        self._log = logging.getLogger(__name__ + '.reader')
        self.keep_running = True
        self.daemon = True
        self.__stream = stream
        self.__frame = None

    @property
    def frame(self):
        return self.__frame

    def shutdown(self):
        self.keep_running = False

    def run(self):
        while self.keep_running:
            try:
                self.__frame = next(self.__stream)
            except StopIteration:
                break


class Application:
    '''
    The main application.

    Use "run" to start it.
    '''

    def __init__(self):
        self.config = None
        self.initialised = False
        self.frames = iter([])
        self.run_web = False
        self.run_gui = False
        self.__verbosity = 0
        self.__stream = []

    def init_scripted(self, frame_source, debug, verbosity, storage=None,
                      mask=None, custom_pipeline=None, pusher_client=None):
        if not self.initialised:
            self.frames = frame_source
            pipeline = custom_pipeline or DefaultPipeline(mask, storage)

            if pusher_client:
                pipeline.operations.insert(5, pusher_client)
                LOG.info('Pusher client inserted into pipelint at position #5')

            stream = detect(self.frames, debug=debug,
                            detection_pipeline=pipeline)
            self.reader_thread = ReaderThread(stream)
            self.verbosity = verbosity
            self.initialised = True
            LOG.info('Application successfully initialised.')
        else:
            LOG.debug('Appliation is already initialised. Skipping init!')

    def init(self, cli_args=None):
        '''
        Initialises the application and parses CLI arguments.

        :param cli_args: CLI arguments
        :param custom_pipeline: An instance of
            :py:class:`raspicam.pipeline.DetectionPipeline`. If left to
            ``None``, :py:class:`raspicam.pipeline.DefaultPipeline` will be
            used.
        '''
        cli_args = cli_args or sys.argv[1:]
        args = parse_args(cli_args)
        self.config = Config('exhuma', 'raspicam', require_load=True)
        kind = self.config.get('framesource', 'kind').lower()
        raw_arguments = self.config.get('framesource', 'arguments', default='')
        frame_source = self._get_framesource(kind, raw_arguments)
        storage = Storage.from_config(self.config)
        mask = self.config.get('detection', 'mask', default=None)

        pusher_app_id = self.config.get('pusher', 'app_id')
        if pusher_app_id:
            pusher_client = pusher(
                app_id=pusher_app_id,
                key=self.config.get('pusher', 'key'),
                secret=self.config.get('pusher', 'secret'),
                cluster=self.config.get('pusher', 'cluster', default='eu'),
                ssl=self.config.get('pusher', 'ssl', default='True')[0].lower() in ('y1t')
            )
            LOG.info('Pusher client created: %r', pusher_client)
        else:
            pusher_client = None

        self.run_web = args.run_web
        self.run_gui = args.run_gui
        self.init_scripted(frame_source, args.debug, args.verbosity, storage,
                           mask, pusher_client=pusher_client)
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
        if value > 0:
            logging.getLogger('werkzeug').setLevel(logging.INFO)
            colorize_werkzeug()

    def _get_framesource(self, kind, raw_arguments):
        '''
        Parsed the frame source from the config and returns an appropriate
        generator.

        The returned genereator will return a new video frame on each iteration.
        '''
        if raw_arguments.strip():
            arguments = [arg.strip() for arg in raw_arguments.split(',')]
        else:
            arguments = []
        if kind == 'usb':
            if arguments:
                index = int(arguments[0])
            else:
                index = -1
            self.source = USBCam(index)
        elif kind == 'raspberrypi':
            self.source = PiCamera()
        elif kind == 'file':
            filename = arguments[0]
            self.source = FileReader(filename)
        else:
            raise ValueError('%s is an unsupported frame source!')
        return self.source.frame_generator()

    def run(self):
        self.reader_thread.start()

        if self.run_web:
            webapp = make_app(self.reader_thread, self.config)
            web_thread = WebThread(webapp)
            web_thread.start()
        else:
            web_thread = NullWeb()

        if self.run_gui:
            gui_thread = GuiThread(self.reader_thread)
            gui_thread.start()

        while True:
            try:
                sleep(0.1)
            except KeyboardInterrupt:
                LOG.info('Intercepted CTRL+C')
                if self.run_gui:
                    gui_thread.shutdown()
                web_thread.shutdown()
                self.reader_thread.shutdown()

            if self.run_gui and not gui_thread.is_alive():
                LOG.debug('GUI exited')
                break

            if not isinstance(web_thread, NullWeb) and not web_thread.is_alive():
                LOG.debug('Web server exited (possible call to /shutdown)')
                break
            elif isinstance(web_thread, NullWeb) and not self.reader_thread.is_alive():
                LOG.debug('Reader server exited.')
                break

        web_thread.shutdown()
        web_thread.join()
        if self.run_gui:
            gui_thread.join()

        if self.reader_thread.is_alive():
            self.reader_thread.shutdown()
            self.reader_thread.join()

        LOG.info('all finished')





def parse_args(cli_args):
    '''
    Parse CLI arguments and return the parsed object.
    '''
    parser = ArgumentParser()
    parser.add_argument('-g', '--run-gui', help='Enable simple desktop GUI',
                        default=False, action='store_true')
    parser.add_argument('-w', '--run-web', help='Enable simple web UI',
                        default=False, action='store_true')
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
    LOG.debug('exiting')


if __name__ == '__main__':
    main()
