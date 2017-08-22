from gouge.colourcli import Simple

from processing import detect

Simple.basicConfig(level=0)

for frame in detect():
    pass
