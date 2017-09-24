from datetime import datetime
from glob import glob
from os import listdir
from os.path import abspath, isdir, join
from time import sleep

from flask import Blueprint, Response, current_app, render_template, send_file, request
from raspicam.processing import as_jpeg

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
    current_frame_id = id(frame_generator.frame)
    while True:
        while current_frame_id == id(frame_generator.frame):
            # sleep as long as the frame has not changed in the thread
            sleep(0.01)
        output = frame_generator.frame
        current_frame_id = id(output)
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


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


@ROOT.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'


@ROOT.route('/')
@ROOT.route('/show_stream')
def show_stream():
    return render_template('show_stream.html')


@ROOT.route('/file/<path:fname>')
def file(fname):
    basedir = current_app.localconf.get('storage', 'root')
    filepath = join(basedir, fname)
    # TODO This is UNSAFE!
    return send_file(
        abspath(filepath),
        as_attachment=False,
        conditional=True
    )
    # with open(filepath, 'rb') as fp:
    #     return send_file(
    #         fp,
    #         attachment_filename=basename(filepath))
    # return send_from_directory(base, fname, as_attachment=False, conditional=True)


@ROOT.route('/player/<path:fname>')
def player(fname):
    return render_template('player.html', fname=fname)


@ROOT.route('/files')
@ROOT.route('/files/<path:path>')
def files(path=''):
    basedir = current_app.localconf.get('storage', 'root', default=None)
    if not basedir:
        return 'No storage defined in config!'
    sysdir = join(basedir, path)
    videos = []
    paths = []
    images = []
    for fname in listdir(sysdir):
        relname = join(path, fname)
        sysname = join(sysdir, fname)
        if fname.endswith('.avi') or fname.endswith('.mkv'):
            videos.append(relname)
        if fname.endswith('.jpg'):
            images.append(relname)
        elif isdir(sysname):
            paths.append(relname)
    entries = {
        'videos': sorted(videos),
        'images': sorted(images),
        'paths': sorted(paths)
    }
    return render_template('browser.html', entries=entries)


@ROOT.route('/file_feed')
def file_feed():
    return Response(multipart_stream(filereader()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@ROOT.route('/live_feed')
def video_feed():
    return Response(multipart_stream(current_app.frame_generator),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
