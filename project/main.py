# main.py

from flask import Flask, render_template, Response
from camera import USBCam, PiCamera

import cv2

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


t adddef myconverter():
    """
    Convert frames to something usable by flask
    :return: 
    """
    cam = PiCamera()
    generator = cam.frame_generator()
    for frame in generator:
        ret, jpeg = cv2.imencode('.jpg', frame)
        frame = jpeg.tostring()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')



@app.route('/video_feed')
def video_feed():
    return Response(myconverter(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
