"""
This module contains the main "DetectionPipeline" class which is the workhorse
of this application. It represents a series of operations which are applied to
each video frame.

For more details, see :py:class:`~.DetectionPipeline`
"""

import logging
from collections import namedtuple

import cv2

import numpy as np
from raspicam.operations import tile

LOG = logging.getLogger(__name__)
MutatorOutput = namedtuple(
    'MutatorOutput', 'intermediate_frames motion_regions')


def tiler(**kwargs):
    '''
    Creates a new pipeline operation to tile images.

    The created operation creates a new frame which tiles each intermediate
    frame.

    :param kwargs: keyword arguments which are delegated to
        :py:func:`raspicam.operations.tile`
    '''
    def fun(frames, motion_regions):
        # pylint: disable=missing-docstring
        output = tile(frames, **kwargs)
        return MutatorOutput([output], motion_regions)
    return fun


def resizer(dimension):
    '''
    Creates a new pipeline operation which resizes a frame to *dimension*.

    :param dimension: The target dimension of the frame
    '''
    def fun(frames, motion_regions):
        # pylint: disable=missing-docstring
        return MutatorOutput([cv2.resize(frames[-1], dimension)],
                             motion_regions)
    return fun


def togray(frames, motion_regions):
    '''
    Converts a frame to grayscale
    '''
    return MutatorOutput([cv2.cvtColor(frames[-1], cv2.COLOR_BGR2GRAY)],
                         motion_regions)


def blur(pixels):
    '''
    Creates a new pipeline operation which blurs the frame by *pixels*.

    .. note::
        OpenCV does not accept each value. From my educated guess, even values
        will not work!

    :param dimension: The target dimension of the frame.
    '''
    def fun(frames, motion_regions):
        # pylint: disable=missing-docstring
        return MutatorOutput(
            [cv2.GaussianBlur(frames[-1], (pixels, pixels), 0)],
            motion_regions)
    return fun


def masker(mask_filename):
    '''
    Creates a new pipeline operation which applies a mask taken from
    *mask_filename* to the image. The image should be black/white only. Black
    pixels will be converted to black in the resulting frame, white pixels will
    let the original frame data "shine through".

    This is a simple binary operation. Either the pixel is masked or not. Alpha
    levels are not supported!

    This mutator will generate one additional intermediate frame, containing the
    mask.

    .. note::

        For performance reason, the mask should have the same dimension as the
        frame it is applied to. If this is not the case, the mask will be
        automatically resized, but a warning message will be logged, informing
        you about the expected dimension.

    :param mask_filename: The filename of the image to be used as mask.
    '''

    LOG.debug('Setting mask to %s', mask_filename)
    if not mask_filename:
        return lambda frames, motion_regions: MutatorOutput([frames[-1]],
                                                            motion_regions)

    mask = cv2.imread(mask_filename, 0)

    def fun(frames, motion_regions):
        # pylint: disable=missing-docstring
        frame = frames[-1]

        if len(frame.shape) == 3:
            LOG.warning('Unable to apply the mask to a color image. '
                        'Convert to B/W first!')
            return MutatorOutput([frame], motion_regions)

        if frame.shape != mask.shape:
            LOG.warning('Mask has differend dimensions than the processed '
                        'image. It should be %s but is %s',
                        frame.shape, mask.shape)
            resized_mask = cv2.resize(mask, (frame.shape[1], frame.shape[0]))
        else:
            resized_mask = mask
        bitmask = cv2.inRange(resized_mask, 0, 0) != 0
        output = np.ma.masked_array(frame, mask=bitmask, fill_value=0).filled()
        return MutatorOutput([resized_mask, output], motion_regions)
    return fun


class MotionDetector:
    '''
    Creates a new pipeline operation which highlights pixels in which motions
    are detected.

    This will generate two frames (one intermediary, and one output frame)
    containing the frame *with* shadows, and one with shadows *removed*. In both
    frames, pixels with motion have the value 255, shadows use 127, and no
    motion is represented by the value 0.

    In addition, this operator will also generate motion regions in the output.
    These regions are standard OpenCV contours.
    '''

    def __init__(self):
        self.fgbg = cv2.createBackgroundSubtractorMOG2()

    def __call__(self, frames, motion_regions):
        fgmask = self.fgbg.apply(frames[-1])
        shadows = cv2.inRange(fgmask, 127, 127) == 255
        without_shadows = np.ma.masked_array(
            fgmask, mask=shadows, fill_value=0).filled()
        _, contours, _ = cv2.findContours(
            without_shadows,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
        contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 30]
        return MutatorOutput([fgmask, without_shadows], contours)


def file_extractor(filename):
    '''
    Creates a new pipeline operation which simply writes the current frame out
    to the specified *filename*. No modification is done.

    If the file already exists, it will be overwritten.
    '''
    def extract(frames, motion_regions):
        # pylint: disable=missing-docstring
        cv2.imwrite(filename, frames[-1])
        return MutatorOutput(frames, motion_regions)
    return extract


def box_drawer(target_frame_index, source_frame_index=None):
    '''
    Creates a new pipeline operation which draws bounding boxes around the
    motion regions fed into the operation. The boxes are drawn on top of the
    frame which is at index *target_frame_index* in the pipeline operations. The
    debug mode can be useful to determine the index.

    In case the regions were created from a frame with *different* dimensions as
    the target frame, the boxes need to be projected onto the target frame. In
    such a case, simply define the frame index of the frame which was used to
    generate the regions using *source_frame_index* and the boxes will
    automatically be projected.

    :param target_frame_index: The index of the frame on which the boxes should
        be drawn to.
    :param source_frame_index: The index of the frame which generated the motion
        regions.
    '''
    def draw_bounding_boxes(frames, motion_regions):
        # pylint: disable=missing-docstring
        if source_frame_index:
            src_shape = frames[source_frame_index].shape
            dst_shape = frames[target_frame_index].shape
            width_ratio = 1 / (src_shape[1] / dst_shape[1])
            height_ratio = 1 / (src_shape[0] / dst_shape[0])

        modified = frames[target_frame_index].copy()
        for contour in motion_regions:
            x, y, w, h = cv2.boundingRect(contour)
            if source_frame_index:
                x = int(x * width_ratio)
                w = int(w * width_ratio)
                y = int(y * height_ratio)
                h = int(h * height_ratio)
            cv2.rectangle(modified, (x, y), (x+w, y+h), (0, 255, 0), 1)
        return MutatorOutput([modified], motion_regions)
    return draw_bounding_boxes


class DetectionPipeline:
    '''
    The main pipeline container.

    Instances of this object can be fed frames. Each frame fed into the pipeline
    will have all *operations* applied to in order. Each operation output (and
    optional intermediate frames) are stored in *intermediate_frames*. The first
    frame will always be the original input frame, the last frame will always
    represent the pipeline output.

    The output is also directly accessible via the *output* property.

    Additionally, in case of detected motion, each function on
    *motion_callbacks* will be called in order, receiving an array of OpenCV
    contour objects which contained motion.

    Example::

        >>> pipe = DetectionPipeline([
        ...     resizer(Dimension(320, 240))
        ...     togray,
        ... ])
        >>> pipe.motion_callbacks.append(lambda contours: print(len(contours)))
        >>> for frame in my_frames:
        ...     pipe.feed(frame)
        ...     print(pipe.output.shape)
    '''

    def __init__(self, operations):
        self.operations = operations
        self.intermediate_frames = []
        self.motion_callbacks = []

    @property
    def output(self):
        '''
        Delegate to the output frame of the pipeline.
        '''
        return self.intermediate_frames[-1]

    def feed(self, frame):
        '''
        Inject a new frame into the pipeline. Each pipeline operation will be
        applied to this frame, and each intermediate frame will be stored in
        *intermediate_frames*.

        :return: The final resulting frame
        '''
        del self.intermediate_frames[:]
        self.intermediate_frames.append(frame)
        motion_regions = []
        for i, func in enumerate(self.operations):
            try:
                output = func(self.intermediate_frames, motion_regions)
            except Exception:
                LOG.critical('Exception raise at pipeline position %d in '
                             'function %s', i, func)
                raise

            if not output.intermediate_frames:
                # If the operation did not generate new frames, we don't process
                # it any further
                continue

            frame = output.intermediate_frames[-1]
            motion_regions = output.motion_regions
            self.intermediate_frames.extend(output.intermediate_frames)
            if output.motion_regions:
                for callback in self.motion_callbacks:
                    callback(output.motion_regions)
        return frame
