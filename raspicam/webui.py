"""
Flask application which serves a motion-JPEG stream.
"""

from flask import Flask, render_template, Response
from raspicam.blueprint.root import ROOT

def make_app(frame_generator, config):
    app = Flask(__name__)
    app.frame_generator = frame_generator
    app.register_blueprint(ROOT)
    return app
