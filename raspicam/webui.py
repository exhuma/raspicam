"""
Flask application which serves a motion-JPEG stream.
"""

from flask import Flask
from raspicam.blueprint.root import ROOT


def make_app(frame_generator, config):
    '''
    Creates a new web-app using  *frame_generator* as source for video-frames
    and *config* as global application config. Returns a WSGI compliant web
    application.
    '''
    app = Flask(__name__)
    app.localconf = config
    app.frame_generator = frame_generator
    app.register_blueprint(ROOT)
    return app
