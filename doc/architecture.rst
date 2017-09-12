.. _architecture:

Architecture
============

The application builds on two main ideas:

* It processes a stream of image frames. Where the frames come from is
  adaptable.
  
  See :py:mod:`raspicam.source` for reference implementations.

* Each frame passes through a pipeline of operations. Each operation is
  responsible for either modifying the frame, finding regions with motion, or
  both.

  See :py:mod:`raspicam.pipeline` for reference implementations.


"Source" Streams
----------------

The existing implementations are all based on Python generators, which allows
for endless streams (like from a webcam). But technically, the way the code is
written, a finite collection of streams could be processed as well.


Pipelines
---------

A pipeline contains an ordered collection of "operations". A pipeline is
stateful. The state of the pipe depends on the last frame which was "fed" to
it. There are two ways of feeding a frame into the pipeline. Either by calling
:py:meth:`~raspicam.pipeline.DetectionPipeline.feed` or by simply *calling* the
pipeline. When calling the pipeline, it has the same behaviour as a normal
pipeline operation (see below). This means, that a pipeline can be used as a
normal operation as well, which lets you combine pipelines out of existing
pipelnes.


Operations
----------

Each operation receives a list of frames, and a list of regions (as OpenCV
contours) which contain motion in that frame as input. The frames represent
each modified frame of the pipeline in the order they were modified in (See
:ref:`intermediary_frames`. The return value of each operation must be an
instance of :py:class:`~raspicam.pipeline.MutatorOutput`.

Operations should follow these two rules:

* If no frame has been modified, the ``intermediate_frames`` value of
  ``MutatorOutput`` should be an empty list.
* If the operation does not do any motion detection, the operation should pass
  on the value that it received as input unmodified.


.. _intermediary_frames:

Intermediary Frames
~~~~~~~~~~~~~~~~~~~

In short: Each operation receives a list of frames and returns a list of frames
again. Typical operations operate on the *last frame in the list*, but are not
forced to. Generally, each frame in the list represents a modified state from
the pipeline.

Rationale
^^^^^^^^^

Originally, the pipeline operated on only one frame per operation. The output
of one operation was  directly passed on to the next operation as input. This
however has one limitation: If an operation does a destructive operation on an
image (edge detection, resizing, grayscaling, e.t.c.) there would be no
possibility to go back. These are operations which are needed for motion
detection. But you also want to display the original frame as output from the
pipeline (with maybe added metadata). Thus, a downstream operation might need
access to an upstream frame. This is *one* reason why "intermediate frames"
were introduced.

The *second* reason is debugging. One operation might do several modifications
on a frame in one go. But you may want to have a look at those frames while
debugging. For this reason, an operation is allowed to return more than one
frame. In that case, the last frame represents the "real" output, while the
others represent intermediate steps. These will be made visible when running
the application in debug mode.
