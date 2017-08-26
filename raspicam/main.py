import logging

from config_resolver import Config
import cv2

from camera import USBCam
from processing import  detect
from raspicam.webui import make_app


LOG = logging.getLogger(__name__)


class Application:

    def __init__(self, config):
        self.config = config
        self.initialised = False
        self.frames = []

    def init(self):
        if not self.initialised:
            self.frames = USBCam().frame_generator()
            self.initialised = True
            LOG.info('Application successfully initialised.')

    def run_gui(self):
        self.init()
        for frame in detect(self.frames):
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
        for frame in detect(self.frames):
            pass

logging.basicConfig(level=0)
config = Config('exhuma', 'raspicam', require_load=True)
# print(config.get('video', 'format', default='h264'))
app = Application(config)
app.run_cli()
