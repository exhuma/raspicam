import logging
from collections import deque
from datetime import datetime

import cv2

from raspicam.types import Dimension

LOG = logging.getLogger(__name__)


class VideoStorage:

    def __init__(self):
        self.video_length = video_length = 200
        self.lookbehind = deque(maxlen=video_length)
        self.lookahead = deque(maxlen=video_length)
        self.dimension = Dimension(100, 100)

    def write(self, frame, output_needed):
        self.dimension = Dimension(frame.shape[1], frame.shape[0])
        timestamp = datetime.now()
        filename = timestamp.strftime('%Y-%m-%dT%H.%M.%S.mkv')
        if not output_needed:
            self.lookbehind.append(frame)
            return True
        else:
            LOG.debug('Video dump requested, %d frames in buffer, filling up lookahead: %d/%d',
                      len(self.lookbehind), len(self.lookahead), self.video_length)
            self.lookahead.append(frame)
        if len(self.lookahead) == self.lookahead.maxlen:
            LOG.info('Dumping video cache (%d lookbehind, %d lookahead)',
                     len(self.lookbehind), len(self.lookahead))
            writer = cv2.VideoWriter(
                filename,
                cv2.VideoWriter_fourcc(*'H264'),
                10.0,
                (self.dimension.width, self.dimension.height),
                True)
            # lookahead is full. Write result to disk
            for stored_frame in self.lookbehind:
                writer.write(stored_frame)
            for stored_frame in self.lookahead:
                writer.write(stored_frame)
            writer.release()
            self.lookbehind.clear()
            self.lookahead.clear()
            return True
        return False


