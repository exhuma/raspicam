"""
Flask application which serves a motion-JPEG stream.
"""
from flask import Flask, render_template, Response

from processing import detect


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

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(multipart_stream(detect()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
