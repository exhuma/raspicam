"""
This module contains callables which cann be used in an image processing
pipeline.
"""
from datetime import datetime


class ImageWriter:

    def __init__(self, interval, storage):
        self.last_snap_taken = datetime.now()
        self.interval = interval
        self.storage = storage

    def __call__(self, current_time, frame, resized, motion_rects):
        time_since_snap = current_time - self.last_snap_taken
        if time_since_snap > self.interval:
            self.storage.write_snapshot(current_time, frame)
            self.last_snap_taken = current_time
        return current_time, frame, resized, motion_rects


class VideoWriter:

    def __init__(self, storage):
        self.storage = storage
        self.video_output_needed = False

    def __call__(self, current_time, frame, resized, motion_rects):
        video_storage_finished = self.storage.write_video(
            frame, self.video_output_needed)
        self.video_output_needed = not video_storage_finished
        return current_time, frame, resized, motion_rects


class ReportPipeline:

    @staticmethod
    def make_default(interval, storage):
        return ReportPipeline([
            ImageWriter(interval, storage),
            VideoWriter(storage),
        ])

    def __init__(self, operations):
        self.operations = operations
        self.intermediate_frames = []

    def feed(self, current_time, frame, resized, motion_rects):
        pipeline_args = current_time, frame, resized, motion_rects
        for func in self.operations:
            pipeline_args = func(*pipeline_args)
            self.intermediate_frames.append(pipeline_args[0])
        return pipeline_args[0]


