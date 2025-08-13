#!/usr/bin/env python3
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GObject

# Initialize GStreamer
Gst.init(None)


class CustomData:
    def __init__(self):
        self.pipeline = None
        self.source = None
        self.audio_convert = None
        self.audio_resample = None
        self.audio_sink = None
        self.video_convert = None
        self.video_sink = None


def pad_added_handler(src, new_pad, data):
    audio_sink_pad = data.audio_convert.get_static_pad("sink")
    video_sink_pad = data.video_convert.get_static_pad("sink")
    print(f"Received new pad '{new_pad.get_name()}' from '{src.get_name()}':")

    # If already linked, do nothing
    if audio_sink_pad.is_linked() and video_sink_pad.is_linked():
        print("We are already linked. Ignoring.")
        return

    # Check new pad's type
    new_pad_caps = new_pad.get_current_caps()
    new_pad_struct = new_pad_caps.get_structure(0)
    new_pad_type = new_pad_struct.get_name()

    if new_pad_type.startswith("audio/x-raw"):
        # print(f"It has type '{new_pad_type}' which is not raw audio. Ignoring.")

        # Attempt to link
        ret = new_pad.link(audio_sink_pad)
        if ret != Gst.PadLinkReturn.OK:
            print(f"Type is '{new_pad_type}' but link failed.")
        else:
            print(f"Link succeeded (type '{new_pad_type}').")

    elif new_pad_type.startswith("video/x-raw"):
        ret = new_pad.link(video_sink_pad)
        if ret != Gst.PadLinkReturn.OK:
            print(f"Type is '{new_pad_type}' but link failed.")
        else:
            print(f"Link succeeded (type '{new_pad_type}').")


def main():
    data = CustomData()

    # Create the elements
    data.source = Gst.ElementFactory.make("uridecodebin", "source")
    data.audio_convert = Gst.ElementFactory.make("audioconvert", "audio_convert")
    data.audio_resample = Gst.ElementFactory.make("audioresample", "audio_resample")
    data.audio_sink = Gst.ElementFactory.make("autoaudiosink", "audio_sink")
    data.video_convert = Gst.ElementFactory.make("videoconvert", "video_convert")
    data.video_sink = Gst.ElementFactory.make("autovideosink", "video_sink")

    if not all(
        [
            data.source,
            data.audio_convert,
            data.audio_resample,
            data.audio_sink,
            data.video_convert,
            data.video_sink,
        ]
    ):
        print("Not all elements could be created.")
        return

    # Create the pipeline
    data.pipeline = Gst.Pipeline.new("test-pipeline")

    # Add elements to pipeline
    data.pipeline.add(
        data.source,
        data.audio_convert,
        data.audio_resample,
        data.audio_sink,
        data.video_convert,
        data.video_sink,
    )
    # data.pipeline.add(data.audio_convert)
    # data.pipeline.add(data.audio_resample)
    # data.pipeline.add(data.sink)

    # Link static elements
    if not (
        (data.audio_convert.link(data.audio_resample))
        and (data.audio_resample.link(data.audio_sink))
        and (data.video_convert.link(data.video_sink))
    ):
        print("Elements could not be linked.")
        return

    # Set the URI
    data.source.props.uri = (
        "https://gstreamer.freedesktop.org/data/media/sintel_trailer-480p.webm"
    )
    # data.source.set_property(
    #     "uri", "https://gstreamer.freedesktop.org/data/media/sintel_trailer-480p.webm"
    # )

    # Connect pad-added signal
    data.source.connect("pad-added", pad_added_handler, data)

    # Start playing
    ret = data.pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("Unable to set the pipeline to the playing state.")
        return

    # Listen to the bus
    bus = data.pipeline.get_bus()
    terminate = False
    while not terminate:
        msg = bus.timed_pop_filtered(
            Gst.CLOCK_TIME_NONE,
            Gst.MessageType.STATE_CHANGED | Gst.MessageType.ERROR | Gst.MessageType.EOS,
        )

        if msg:
            t = msg.type
            if t == Gst.MessageType.ERROR:
                err, debug_info = msg.parse_error()
                print(
                    f"Error received from element {msg.src.get_name()}: {err.message}"
                )
                print(f"Debugging information: {debug_info if debug_info else 'none'}")
                terminate = True
            elif t == Gst.MessageType.EOS:
                print("End-Of-Stream reached.")
                terminate = True
            elif t == Gst.MessageType.STATE_CHANGED:
                if msg.src == data.pipeline:
                    old_state, new_state, pending_state = msg.parse_state_changed()
                    print(
                        f"Pipeline state changed from {Gst.Element.state_get_name(old_state)} "
                        f"to {Gst.Element.state_get_name(new_state)}"
                    )

    # Clean up
    data.pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    main()
