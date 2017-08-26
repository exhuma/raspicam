from datetime import datetime
from glob import glob
from time import sleep
from flask import Blueprint, render_template, current_app, Response

from raspicam.processing import detect, as_jpeg

ROOT = Blueprint('root', __name__)


def multipart_stream(frame_generator):
    """
    Wrap each item from a generator with HTTP Multipart metadata. This is required for Motion-JPEG.

    Example::

        >>> frames = my_generator()
        >>> wrapped_generator = multipart_stream(frames)
        >>> for frame in wrapped_generator:
        ...     print(frame[:20])

    :param frame_generator: A generater which generates image frames as *bytes* objects
    :return: A new, wrapped stream of bytes
    """
    for output in frame_generator:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'\r\n' + as_jpeg(output) + b'\r\n'
                                  b'\r\n')


def filereader():
    while True:
        now = datetime.now()
        dirname = now.strftime('%Y-%m-%d')
        fname = sorted(glob('%s/*.jpg' % dirname))[-1]
        with open(fname, 'rb') as fp:
            yield fp.read()
            sleep(0.5)


@ROOT.route('/')
def index():
    return render_template('index.html')


@ROOT.route('/file_feed')
def file_feed():
    return Response(multipart_stream(filereader()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@ROOT.route('/live_feed')
def video_feed():
    return Response(multipart_stream(detect(current_app.camera)),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
