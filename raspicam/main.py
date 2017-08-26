import logging

from config_resolver import Config
import cv2

from camera import USBCam, PiCamera
from processing import  detect

from raspicam.storage import VideoStorage, NullStorage
from raspicam.webui import make_app


LOG = logging.getLogger(__name__)


class Application:

    def __init__(self, config):
        self.config = config
        self.initialised = False
        self.frames = []
        self.storage = NullStorage()

    def init(self):
        if not self.initialised:
            self.frames = self._get_framesource()
            self.storage = VideoStorage()
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
        else:
            raise ValueError('%s is an unsupported frame source!')

    def run_gui(self):
        self.init()
        for frame in detect(self.frames, self.storage):
            cv2.imshow('frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        # When everything done, release the capture
        # cap.release()
        cv2.destroyAllWindows()

    def run_webui(self):
        app = make_app(self.frames, self.config)
        app.run(host='0.0.0.0', debug=True, threaded=True)

    def run_cli(self):
        for frame in detect(self.frames, self.storage):
            pass

logging.basicConfig(level=0)
config = Config('exhuma', 'raspicam', require_load=True)
# print(config.get('video', 'format', default='h264'))
app = Application(config)
app.run_gui()
