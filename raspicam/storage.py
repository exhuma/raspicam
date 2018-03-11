"""
Different implementations of persistent storage endpoints.

Each storage should be a subclass of :py:class:`~.Storage`. For more information
refer to that class.

Currently this is only aimed at disk-storage but other implementations would be
possible. But then some variable names and function signatures *might* need to
be revisited for clarity.

This module offers two implementations:

* :py:class:`~.DiskStorage` which stores files onto the harddisk.
* :py:class:`~.NullStorage` which does not store the file anywhere.
"""
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
    """
    A storage subclass is responsible to put files into permanent storage. This
    class should be subclassed for concrete storage implementations.
    """

    def __init__(self):
        self.video_length = video_length = 200
        self.lookbehind = deque(maxlen=video_length)
        self.lookahead = deque(maxlen=video_length)
        self.dimension = Dimension(100, 100)
        self.format = 'h264'
        self.root = getcwd()

    @abstractmethod
    def write_video(self, frame, has_motion):
        '''
        Add *frame* to a video file.

        :param frame: The frame to append to the video.
        :param has_motion: Wheter the video contains regions in which motion
            was detected or not.
        '''
        raise NotImplementedError('Not yet implemented')

    def write_snapshot(self, timestamp, image, subdir=''):
        '''
        Put the *image* (which was taken at *timestamp*) into storage.

        :param timestamp: The date & time at which the image was taken.
        :param image: The image to wite.
        :param subdir: An optional sub-directory name (relative to the storage
            root).
        '''
        raise NotImplementedError('Not yet implemented')

    @staticmethod
    def from_config(config):
        '''
        Generate a storage of the appropriate class from a config instance.

        The config should contain the section ``storage.root`` representing the
        root folder of the storage.
        '''
        root = config.get('storage', 'root', default='')
        if not root:
            LOG.warning('No option storage.root in config file. '
                        'Storage disabled!')
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
        '''
        Returns the video extension used for the selected video format.

        OpenCV seems to be quite picky about the codec & extension combination
        and is not able to offer an extension by itself. Using the wrong
        codec/extension combination results in empty video-frames. This property
        contains tested combinations and will return the appropriate extension
        given the video format.
        '''
        if self.format == 'divx':
            return '.avi'
        elif self.format == 'h264':
            return '.mkv'
        else:
            raise ValueError('Unknown Video Format')

    @property
    def fourcc(self):
        '''
        This property decouples the config-value of the video codec from the
        fourcc code.
        '''
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
    '''
    Writes files to disk
    '''

    def write_video(self, frame, has_motion):
        '''
        See :py:meth:`.Storage.write_video`
        '''
        self.dimension = Dimension(frame.shape[1], frame.shape[0])
        timestamp = datetime.now()
        day = timestamp.strftime('%Y-%m-%d')
        dirname = join(self.root, day, 'video')
        if not exists(dirname):
            makedirs(dirname)
        basename = timestamp.strftime(
            '%Y-%m-%dT%H.%M.%S') + self.video_extension
        absname = join(dirname, basename)
        if not has_motion:
            self.lookbehind.append(frame)
            return True
        else:
            LOG.debug('Video dump requested, %d frames in buffer, '
                      'filling up lookahead: %d/%d',
                      len(self.lookbehind),
                      len(self.lookahead),
                      self.video_length)
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
        '''
        See :py:meth:`.Storage.write_snapshot`
        '''
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
    '''
    Simply logs calls, but does not really store anything.

    This can be useful to disable storage alltogether and/or debugging.
    '''

    def write_video(self, frame, has_motion):
        '''
        See :py:meth:`.Storage.write_video`
        '''
        LOG.debug('Writing video frame to NullStorage')

    def write_snapshot(self, timestamp, image, subdir=''):
        '''
        See :py:meth:`.Storage.write_snapshot`
        '''
        LOG.debug('Writing image frame to NullStorage')
