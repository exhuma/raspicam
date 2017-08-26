"""
Flask application which serves a motion-JPEG stream.
"""

from flask import Flask, render_template, Response
from raspicam.blueprint.root import ROOT

def make_app(camera, config):
    app = Flask(__name__)
    app.camera = camera
    app.register_blueprint(ROOT)
    return app
