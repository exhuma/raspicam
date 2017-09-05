import logging
from abc import ABCMeta, abstractmethod
from collections import deque
from datetime import datetime
from os import getcwd, makedirs
from os.path import exists, join

import cv2

from raspicam.localtypes import Dimension

LOG = logging.getLogger(__name__)


class Storage(metaclass=ABCMeta):

    def __init__(self):
        self.video_length = video_length = 200
        self.lookbehind = deque(maxlen=video_length)
        self.lookahead = deque(maxlen=video_length)
        self.dimension = Dimension(100, 100)
        self.format = 'h264'
        self.root = getcwd()

    @abstractmethod
    def write_video(self, frame, output_needed):
        raise NotImplementedError('Not yet implemented')

    def write_snapshot(self, timestamp, image, subdir=''):
        raise NotImplementedError('Not yet implemented')

    @staticmethod
    def from_config(config):
        root = config.get('storage', 'root', default='')
        if not root:
            LOG.warning('No option storage.root in config file. Storage disabled!')
            return NullStorage()

        instance = DiskStorage()
        instance.root = root
        video_length = int(
            config.get('storage', 'num_context_frames', default=200))
        instance.video_length = video_length
        instance.lookbehind = deque(maxlen=video_length)
        instance.lookahead = deque(maxlen=video_length)
        instance.root = config.get('storage', 'root')
        instance.format = config.get('video', 'format', default='h264')
        LOG.debug('Storage created: %r', instance)
        return instance

    @property
    def video_extension(self):
        if self.format == 'divx':
            return '.avi'
        elif self.format == 'h264':
            return '.mkv'
        else:
            raise ValueError('Unknown Video Format')

    @property
    def fourcc(self):
        if self.format == 'divx':
            return 'DIVX'
        elif self.format == 'h264':
            return 'H264'
        else:
            raise ValueError('Unknown Video Format')

    def __repr__(self):
        return '<%s root=%r context=%r>' % (
            self.__class__.__name__, self.root, self.video_length)


class DiskStorage(Storage):

    def write_video(self, frame, output_needed):
        self.dimension = Dimension(frame.shape[1], frame.shape[0])
        timestamp = datetime.now()
        day = timestamp.strftime('%Y-%m-%d')
        dirname = join(self.root, day, 'video')
        if not exists(dirname):
            makedirs(dirname)
        basename = timestamp.strftime('%Y-%m-%dT%H.%M.%S') + self.video_extension
        absname = join(dirname, basename)
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
                absname,
                cv2.VideoWriter_fourcc(*self.fourcc),
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
            LOG.info('Video written to %r (codec=%s)', absname, self.format)
            return True
        return False

    def write_snapshot(self, timestamp, image, subdir=''):
        dirname = join(self.root, timestamp.strftime('%Y-%m-%d'), 'images')
        if subdir:
            dirname = join(dirname, subdir)
        if not exists(dirname):
            makedirs(dirname)
        ts_text = timestamp.strftime('%Y-%m-%dT%H.%M')
        filename = join(
            dirname, ts_text + '.jpg')
        if exists(filename):
            LOG.debug('Skipping existing file %s', filename)
            return
        cv2.imwrite(filename, image)
        LOG.info('Snapshot written to %s', filename)



class NullStorage(Storage):

    def write_video(self, frame, output_needed):
        LOG.debug('Writing video frame to NullStorage')

    def write_snapshot(self, timestamp, image, subdir=''):
        LOG.debug('Writing image frame to NullStorage')
