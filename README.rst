raspicam
========

Playground for Raspberry Pi motion detection using Python.


How to setup
------------

This project is based on `Raspbian Jessie Lite
<https://downloads.raspberrypi.org/raspbian_lite/images/raspbian_lite-2017-07-05/>`_.
I have not tested it on the latest (stretch) image, but I'm certain that the
bootstrap script is not yet properly adapted to that.


1. Download the raspian image from the link above
2. Write the image to the SD-card of the Raspberry Pi
3. Boot the Raspberry Pi and update the packages::

        sudo aptitude update
        sudo aptitude upgrade

4. Clone the project into your home folder::

        sudo aptitude install git
        git clone https://github.com/exhuma/raspicam

5. Run the bootstrap script::

   .. note::

        This step will easily take over an hour to finish but *should* be
        automated!

    ::

        cd raspicam
        sudo bash bootstrap.bash

6. Run the application::

        cd ~/raspicam
        python3 project/main.py
