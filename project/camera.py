import logging
import picamera
import picamera.array
from abc import ABCMeta, abstractmethod

import cv2

LOG = logging.getLogger(__name__)


class Camera(metaclass=ABCMeta):

    @abstractmethod
    def frame_generator(self):
        raise NotImplementedError('Not yet implemented')


class USBCam(Camera):

    def frame_generator(self):
        self.video = cv2.VideoCapture(-1)
        if not self.video.isOpened():
            raise Exception('Unable to open camera')
        success, image = self.video.read()
        yield image
        self.video.release()


class PiCamera(Camera):

    def frame_generator(self):
        with picamera.PiCamera() as camera:
            with picamera.array.PiRGBArray(camera) as output:
                camera.resolution = (640, 480)
                camera.framerate = 32
                while True:
                    camera.capture(output, 'rgb', use_video_port=True)
                    yield output.array
                    output.truncate(0)
