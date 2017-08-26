import logging

from config_resolver import Config
import cv2

from camera import USBCam
from processing import  detect
from raspicam.webui import make_app


class Application:

    def __init__(self, config):
        self.config = config
        self.frame_generator = USBCam().frame_generator()

    def run_gui(self):
        for frame in detect(self.frame_generator):
            cv2.imshow('frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        # When everything done, release the capture
        # cap.release()
        cv2.destroyAllWindows()

    def run_webui(self):
        app = make_app(self.frame_generator, self.config)
        app.run(host='0.0.0.0', debug=True, threaded=True)

    def run_cli(self):
        for frame in detect(self.frame_generator):
            pass

logging.basicConfig(level=0)
config = Config('exhuma', 'raspicam', require_load=True)
# print(config.get('video', 'format', default='h264'))
app = Application(config)
app.run_cli()
