from gouge.colourcli import Simple

from processing import detect
from camera import USBCam

Simple.basicConfig(level=0)

cam = USBCam()

for frame in detect(cam):
    pass
