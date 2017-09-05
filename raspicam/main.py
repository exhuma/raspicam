import logging

import cv2

from config_resolver import Config
from processing import detect
from raspicam.camera import PiCamera, USBCam
from raspicam.source import FileReader
from raspicam.storage import NullStorage, Storage
from raspicam.webui import make_app

LOG = logging.getLogger(__name__)


class Application:

    def __init__(self, config):
        self.config = config
        self.initialised = False
        self.frames = iter([])
        self.mask = None
        self.storage = NullStorage()

    def init(self):
        if not self.initialised:
            self.storage = Storage.from_config(self.config)
            self.frames = self._get_framesource()
            self.mask = self.config.get('detection', 'mask', default=None)
            self.initialised = True
            LOG.info('Application successfully initialised.')

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
        self.init()
        for frame in detect(self.frames, self.storage, self.mask):
            cv2.imshow('RaspiCam Main Window', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        # When everything done, release the capture
        # cap.release()
        cv2.destroyAllWindows()

    def run_webui(self):
        self.init()
        app = make_app(detect(self.frames, self.storage, self.mask), self.config)
        app.run(host='0.0.0.0', debug=True, threaded=True)

    def run_cli(self):
        self.init()
        for frame in detect(self.frames, self.storage, self.mask):
            pass

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=0)
    config = Config('exhuma', 'raspicam', require_load=True)
    ui = sys.argv[1]
    app = Application(config)

    if ui == 'cli':
        app.run_cli()
    elif ui == 'webui':
        app.run_webui()
    elif ui == 'gui':
        app.run_gui()
    else:
        print("ui must be cli, webui or gui")
