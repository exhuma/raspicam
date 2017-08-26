"""
Flask application which serves a motion-JPEG stream.
"""
from datetime import datetime
from glob import glob
from os.path import join
from time import sleep

from flask import Flask, render_template, Response
from gouge.colourcli import Simple

from processing import detect
from camera import USBCam


app = Flask(__name__)

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
               b'\r\n' + output + b'\r\n'
               b'\r\n')


def filereader():
    while True:
        now = datetime.now()
        dirname = now.strftime('%Y-%m-%d')
        fname = sorted(glob('%s/*.jpg' % dirname))[-1]
        with open(fname, 'rb') as fp:
            yield fp.read()
            sleep(0.5)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/file_feed')
def file_feed():
    return Response(multipart_stream(filereader()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/live_feed')
def video_feed():
    camera = USBCam()
    return Response(multipart_stream(detect(camera)),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    Simple.basicConfig(level=0)
    app.run(host='0.0.0.0', debug=True)
