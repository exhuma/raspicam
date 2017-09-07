import logging

import cv2

LOG = logging.getLogger(__name__)


class FileReader:

    def __init__(self, filename):
        self.filename = filename

    def frame_generator(self):
        video = cv2.VideoCapture(self.filename)
        if not video.isOpened():
            raise Exception('Unable to open %s' % self.filename)
        while True:
            success, image = video.read()
            if not success:
                LOG.info('Unable to read frame from %s. Might have reached '
                         'end of file!' % self.filename)
                return None
            yield image
