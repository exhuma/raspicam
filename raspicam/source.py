"""
Module which regroups all frame sources.
"""
import logging
from abc import ABCMeta, abstractmethod

import cv2


LOG = logging.getLogger(__name__)


class Source(metaclass=ABCMeta):
    '''
    Abstract class for frame sources.

    This is called "Camera" for historic reasons, and this will be refactored in
    the near future.
    '''

    @abstractmethod
    def frame_generator(self):
        '''
        A function which should return an iterable over video frames.
        '''
        raise NotImplementedError('Not yet implemented')


class FileReader(Source):
    """
    Read frames from a video file.

    :param filename: The name of the video file.
    """

    def __init__(self, filename):
        self.filename = filename

    def frame_generator(self):
        '''
        Returns a generator of video frames
        '''
        video = cv2.VideoCapture(self.filename)
        if not video.isOpened():
            raise Exception('Unable to open %s' % self.filename)
        while True:
            success, image = video.read()
            if not success:
                LOG.info('Unable to read frame from %s. Might have reached '
                         'end of file!', self.filename)
                return
            yield image


class USBCam(Source):
    '''
    Creates an instance which is capable of reading video frames from an USB
    Camera.

    :param index: The index passed to ``OpenCV.VideoCapture``. Using ``-1`` will
        search for the first available cam, while ``0`` represents the system
        default.
    '''

    def __init__(self, index=-1):
        self.index = index

    def frame_generator(self):
        '''
        Returns a generator for video frames.
        '''
        video = cv2.VideoCapture(self.index)
        if not video.isOpened():
            raise Exception('Unable to open camera')
        while True:
            _, image = video.read()
            yield image
        video.release()


class PiCamera(Source):
    '''
    Creates an instance which is capable of reading video frames from the
    Raspberry Pi Camera module.
    '''

    def frame_generator(self):
        '''
        Returns a generator for video frames.
        '''
        import picamera.array
        with picamera.PiCamera() as camera:
            with picamera.array.PiRGBArray(camera) as output:
                camera.resolution = (640, 480)
                camera.framerate = 32
                while True:
                    camera.capture(output, 'rgb', use_video_port=True)
                    yield output.array
                    output.truncate(0)
