"""
Flask application which serves a motion-JPEG stream.
"""

from flask import Flask, Response, render_template
from raspicam.blueprint.root import ROOT


def make_app(frame_generator, config):
    app = Flask(__name__)
    app.localconf = config
    app.frame_generator = frame_generator
    app.register_blueprint(ROOT)
    return app
