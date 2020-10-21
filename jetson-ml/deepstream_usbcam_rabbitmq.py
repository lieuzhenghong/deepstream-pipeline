#!/usr/bin/env python3

from optparse import OptionParser
import pyds
from common.utils import long_to_int
from common.bus_call import bus_call
from common.is_aarch_64 import is_aarch64
from gi.repository import GObject, Gst
import gi
import sys
sys.path.append('../')
gi.require_version('Gst', '1.0')


# Global variables
MAX_TIME_STAMP_LEN = 32
PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3
SCHEMA_TYPE = 0

NO_DISPLAY = False
CAM_PATH = None

MSGBROKER_CONFIG_FILE = None
MSGCONV_CONFIG_FILE = None
PGIE_CONFIG_FILE = None
PROTO_LIB = None

# Callback function for deep-copying an NvDsEventMsgMeta struct


def meta_copy_func(data, user_data):
    # Cast data to pyds.NvDsUserMeta
    user_meta = pyds.NvDsUserMeta.cast(data)
    src_meta_data = user_meta.user_meta_data
    # Cast src_meta_data to pyds.NvDsEventMsgMeta
    srcmeta = pyds.NvDsEventMsgMeta.cast(src_meta_data)
    # Duplicate the memory contents of srcmeta to dstmeta
    # First use pyds.get_ptr() to get the C address of srcmeta, then
    # use pyds.memdup() to allocate dstmeta and copy srcmeta into it.
    # pyds.memdup returns C address of the allocated duplicate.
    dstmeta_ptr = pyds.memdup(pyds.get_ptr(
        srcmeta), sys.getsizeof(pyds.NvDsEventMsgMeta))
    # Cast the duplicated memory to pyds.NvDsEventMsgMeta
    dstmeta = pyds.NvDsEventMsgMeta.cast(dstmeta_ptr)

    # Duplicate contents of ts field. Note that reading srcmeat.ts
    # returns its C address. This allows to memory operations to be
    # performed on it.
    dstmeta.ts = pyds.memdup(srcmeta.ts, MAX_TIME_STAMP_LEN+1)

    # Copy the sensorStr. This field is a string property.
    # The getter (read) returns its C address. The setter (write)
    # takes string as input, allocates a string buffer and copies
    # the input string into it.
    # pyds.get_string() takes C address of a string and returns
    # the reference to a string object and the assignment inside the binder copies content.
    # dstmeta.sensorStr=pyds.get_string(srcmeta.sensorStr)

    if(srcmeta.objSignature.size > 0):
        dstmeta.objSignature.signature = pyds.memdup(
            srcmeta.objSignature.signature, srcMeta.objSignature.size)
        dstmeta.objSignature.size = srcmeta.objSignature.size

    if(srcmeta.extMsgSize > 0):
        if(srcmeta.objType == pyds.NvDsObjectType.NVDS_OBJECT_TYPE_VEHICLE):
            srcobj = pyds.NvDsVehicleObject.cast(srcmeta.extMsg)
            obj = pyds.alloc_nvds_vehicle_object()
            obj.type = pyds.get_string(srcobj.type)
            obj.make = pyds.get_string(srcobj.make)
            obj.model = pyds.get_string(srcobj.model)
            obj.color = pyds.get_string(srcobj.color)
            obj.license = pyds.get_string(srcobj.license)
            obj.region = pyds.get_string(srcobj.region)
            dstmeta.extMsg = obj
            dstmeta.extMsgSize = sys.getsizeof(pyds.NvDsVehicleObject)
        if(srcmeta.objType == pyds.NvDsObjectType.NVDS_OBJECT_TYPE_PERSON):
            srcobj = pyds.NvDsPersonObject.cast(srcmeta.extMsg)
            obj = pyds.alloc_nvds_person_object()
            obj.age = srcobj.age
            obj.gender = pyds.get_string(srcobj.gender)
            obj.cap = pyds.get_string(srcobj.cap)
            obj.hair = pyds.get_string(srcobj.hair)
            obj.apparel = pyds.get_string(srcobj.apparel)
            dstmeta.extMsg = obj
            dstmeta.extMsgSize = sys.getsizeof(pyds.NvDsVehicleObject)

    return dstmeta

# Callback function for freeing an NvDsEventMsgMeta instance


def meta_free_func(data, user_data):
    user_meta = pyds.NvDsUserMeta.cast(data)
    srcmeta = pyds.NvDsEventMsgMeta.cast(user_meta.user_meta_data)

    # pyds.free_buffer takes C address of a buffer and frees the memory
    # It's a NOP if the address is NULL
    pyds.free_buffer(srcmeta.ts)
    pyds.free_buffer(srcmeta.sensorStr)

    if(srcmeta.objSignature.size > 0):
        pyds.free_buffer(srcmeta.objSignature.signature)
        srcmeta.objSignature.size = 0

    '''
    if(srcmeta.extMsgSize > 0):
        if(srcmeta.objType == pyds.NvDsObjectType.NVDS_OBJECT_TYPE_VEHICLE):
            obj =pyds.NvDsVehicleObject.cast(srcmeta.extMsg)
            pyds.free_buffer(obj.type);
            pyds.free_buffer(obj.color);
            pyds.free_buffer(obj.make);
            pyds.free_buffer(obj.model);
            pyds.free_buffer(obj.license);
            pyds.free_buffer(obj.region);
        if(srcmeta.objType == pyds.NvDsObjectType.NVDS_OBJECT_TYPE_PERSON):
            obj = pyds.NvDsPersonObject.cast(srcmeta.extMsg);
            pyds.free_buffer(obj.gender);
            pyds.free_buffer(obj.cap);
            pyds.free_buffer(obj.hair);
            pyds.free_buffer(obj.apparel);
        pyds.free_gbuffer(srcmeta.extMsg);
        srcmeta.extMsgSize = 0;
    '''


def generate_event_msg_meta(data, class_id):
    '''
    Some MetaData instances are stored in GList form. 
    To access the data in a GList node, 
    the data field needs to be cast to the appropriate structure. 
    This casting is done via cast() member function for the target type:
    '''
    meta = pyds.NvDsEventMsgMeta.cast(data)
    # Check the following link for struct fields
    # https://docs.nvidia.com/metropolis/deepstream/5.0/dev-guide/DeepStream_Development_Guide/baggage/structNvDsEventMsgMeta.html#af94e900971860386108ddcdf82983490
    meta.ts = pyds.alloc_buffer(MAX_TIME_STAMP_LEN + 1)
    pyds.generate_ts_rfc3339(meta.ts, MAX_TIME_STAMP_LEN)

    '''
    if (class_id == PGIE_CLASS_ID_PERSON):
        meta.type = pyds.NvDsEventType.NVDS_EVENT_ENTRY
        meta.objType = pyds.NvDsObjectType.NVDS_OBJECT_TYPE_PERSON # This affects the meta fields
        meta.objClassId = PGIE_CLASS_ID_PERSON
        # We need to allocate memory in order to persist the object 
        # See the following link:
        # https://docs.nvidia.com/metropolis/deepstream/dev-guide/index.html#page/DeepStream_Development_Guide/deepstream_Python_sample_apps.html#wwpID0E0WC0HA
        # obj = pyds.alloc_nvds_person_object() 
        # obj = generate_person_meta(obj)
        # meta.extMsg = obj
        # meta.extMsgSize = sys.getsizeof(pyds.NvDsPersonObject)
    '''

    meta.type = pyds.NvDsEventType.NVDS_EVENT_ENTRY
    meta.objType = pyds.NvDsObjectType.NVDS_OBJECT_TYPE_CUSTOM
    # TODO we need to allocate memory and generate custom metadata
    # See above for how to do it
    meta.objClassId = class_id

    return meta


def osd_sink_pad_buffer_probe(pad, info, u_data):
    frame_number = 0
    obj_counter = {
        PGIE_CLASS_ID_VEHICLE: 0,
        PGIE_CLASS_ID_PERSON: 0,
        PGIE_CLASS_ID_BICYCLE: 0,
        PGIE_CLASS_ID_ROADSIGN: 0
    }
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GSTBuffer")
        return

    # Retrieve batch metadata from the GST Buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects
    # the C address of gst_buffer as input,
    # which is obtained with hash(gst_buffer)

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    if not batch_meta:
        return Gst.PadProbeReturn.OK
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
            # The casting is done by pyds.NvDSFrameMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collection
            # will leave it alone
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            continue

        frame_number = frame_meta.frame_num
        l_obj = frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                continue

            obj_counter[obj_meta.class_id] += 1

            if ((frame_number % 30) == 0):
                # Allocating an NvDsEventMsgMeta instance and getting reference
                # to it. The underlying memory is not managed by Python so that
                # downstream plugins can access it. Otherwise the garbage collector
                # will free it when this probe exits.
                # See the "MetaData Access" section at this link:
                # https://docs.nvidia.com/metropolis/deepstream/dev-guide/index.html#page/DeepStream_Development_Guide/deepstream_Python_sample_apps.html

                # See also the struct fields here (C++ API reference):
                # https://docs.nvidia.com/metropolis/deepstream/5.0/dev-guide/DeepStream_Development_Guide/baggage/structNvDsEventMsgMeta.html
                msg_meta = pyds.alloc_nvds_event_msg_meta()
                msg_meta.bbox.top = obj_meta.rect_params.top
                msg_meta.bbox.left = obj_meta.rect_params.left
                msg_meta.bbox.width = obj_meta.rect_params.width
                msg_meta.bbox.height = obj_meta.rect_params.height
                msg_meta.frameId = frame_number
                msg_meta.trackingId = long_to_int(obj_meta.object_id)
                msg_meta.confidence = obj_meta.confidence
                # What is this msg_meta thing even for? Can we get rid of this bit?
                # https://docs.nvidia.com/metropolis/deepstream/python-api/NvDsMeta_Schema/NvDsEventMsgMeta.html
                # No we can't this is the thing that actually sends it out
                # TODO I need to understand what this is
                msg_meta = generate_event_msg_meta(msg_meta, obj_meta.class_id)
                user_event_meta = pyds.nvds_acquire_user_meta_from_pool(
                    batch_meta)
                if (user_event_meta):
                    user_event_meta.user_meta_data = msg_meta
                    user_event_meta.base_meta.meta_type = pyds.NvDsMetaType.NVDS_EVENT_MSG_META
                    # Custom MetaData added to NvDsUserMeta require
                    # custom copy and release functions.
                    # The MetaData library relies on these custom functions to perform deep-copy of the custom structure,
                    # and free allocated resources.
                    # These functions are registered as callback function pointers in the NvDsUserMeta structure.

                    # Setting callbacks in the event msg meta. The bindings layer
                    # will wrap these callables in C functions. Currently only one
                    # set of callbacks is supported.
                    # pyds.set_user_copyfunc(user_event_meta, meta_copy_func)
                    # pyds.set_user_releasefunc(user_event_meta, meta_free_func)
                    pyds.nvds_add_user_meta_to_frame(
                        frame_meta, user_event_meta)
                else:
                    print("Error in attaching event meta to buffer\n")
            try:
                l_obj = l_obj.next
            except StopIteration:
                break
        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    print(
        f"Frame Number = {frame_number}, Person Count = {obj_counter[PGIE_CLASS_ID_PERSON]}")
    return Gst.PadProbeReturn.OK


def main(args):
    GObject.threads_init()
    Gst.init(None)
    pipeline = Gst.Pipeline()
    source = Gst.ElementFactory.make("v4l2src", "usb-cam-source")
    caps_v4l2src = Gst.ElementFactory.make("capsfilter", "v4l2src_caps")
    # videoconvert to make sure a superset of raw formats are supported
    vidconvsrc = Gst.ElementFactory.make("videoconvert", "convertor_src1")
    # nvvideoconvert to convert incoming raw buffers for NVMM Mem (NvBufSurface API)
    nvvidconvsrc = Gst.ElementFactory.make("nvvideoconvert", "convertor_src2")
    caps_vidconvsrc = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
    # create nvstreammux instance to form batches from one or more sources
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    # Use nvinfer to run inferencing on camera's output,
    # behaviour of inferencing is set through config file
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    # use convertor to convert from NV12 to RGBA as required by nvosd
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    # Create OSD to draw on the converted RGBA buffer
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    # NVMsgConv converts a buffer to a NVDs Payload in JSON format
    # https://docs.nvidia.com/metropolis/deepstream/dev-guide/index.html#page/DeepStream%20Plugins%20Development%20Guide/deepstream_plugin_details.html#wwpID0E0LP0HA
    msgconv = Gst.ElementFactory.make("nvmsgconv", "nvmsg-converter")
    # NVMsgBroker takes the NVDs payload and sends it out or something
    msgbroker = Gst.ElementFactory.make("nvmsgbroker", "nvmsg-broker")
    # What is tee?
    tee = Gst.ElementFactory.make("tee", "nvsink-tee")
    # What is queue1 and queue2?
    queue1 = Gst.ElementFactory.make("queue", "nvtee-que1")
    queue2 = Gst.ElementFactory.make("queue", "nvtee-que2")

    if NO_DISPLAY:
        print("Creating FakeSink")
        sink = Gst.ElementFactory.make("fakesink", "fakesink")
    else:
        if is_aarch64():
            transform = Gst.ElementFactory.make(
                "nvegltransform", "nvegl-transform")

        print("Creating EGLSink")
        sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")

    print(f"Playing cam {CAM_PATH}")
    caps_v4l2src.set_property(
        'caps', Gst.Caps.from_string("video/x-raw, framerate=30/1"))
    caps_vidconvsrc.set_property(
        'caps', Gst.Caps.from_string("video/x-raw(memory:NVMM)"))
    source.set_property('device', CAM_PATH)
    streammux.set_property('width', 1280)
    streammux.set_property('height', 720)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)
    # Set sync = false to avoid late frame drops at the display-sink
    pgie.set_property('config-file-path', PGIE_CONFIG_FILE)

    # TODO can i remove the msgconv config
    msgconv.set_property('config', MSGCONV_CONFIG_FILE)
    msgconv.set_property('payload-type', SCHEMA_TYPE)

    # Set msgbroker config
    msgbroker.set_property('proto-lib', PROTO_LIB)
    msgbroker.set_property('config', MSGBROKER_CONFIG_FILE)
    msgbroker.set_property('sync', False)

    # Add sync = false to avoid late frame drops at the display
    sink.set_property('sync', False)

    # =======================================
    # Add elements to pipeline
    # =======================================
    print("Adding elements to the pipeline")
    pipeline.add(source)
    pipeline.add(caps_v4l2src)
    pipeline.add(vidconvsrc)
    pipeline.add(nvvidconvsrc)
    pipeline.add(caps_vidconvsrc)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(tee)
    pipeline.add(queue1)
    pipeline.add(queue2)
    pipeline.add(msgconv)
    pipeline.add(msgbroker)
    pipeline.add(sink)
    if is_aarch64() and not NO_DISPLAY:
        pipeline.add(transform)

    # =======================================
    # Link elements in pipeline
    # =======================================

    print(f"Linking elements in the pipeline...")
    source.link(caps_v4l2src)
    caps_v4l2src.link(vidconvsrc)
    vidconvsrc.link(nvvidconvsrc)
    nvvidconvsrc.link(caps_vidconvsrc)

    # what does this do?
    sinkpad = streammux.get_request_pad("sink_0")
    srcpad = caps_vidconvsrc.get_static_pad("src")

    srcpad.link(sinkpad)
    streammux.link(pgie)
    pgie.link(nvvidconv)
    nvvidconv.link(nvosd)
    nvosd.link(tee)
    queue1.link(msgconv)
    msgconv.link(msgbroker)

    if is_aarch64() and not NO_DISPLAY:
        queue2.link(transform)
        transform.link(sink)
    else:
        queue2.link(sink)

    # This links the two queues to the tee element
    # See this GStreamer link:
    # https://gstreamer.freedesktop.org/documentation/tutorials/basic/multithreading-and-pad-availability.html?gi-language=c
    sink_pad = queue1.get_static_pad("sink")
    tee_msg_pad = tee.get_request_pad('src_%u')
    tee_render_pad = tee.get_request_pad('src_%u')
    if not tee_msg_pad or not tee_render_pad:
        sys.stderr.write("Unable to get request pads")
    tee_msg_pad.link(sink_pad)
    sink_pad = queue2.get_static_pad("sink")
    tee_render_pad.link(sink_pad)

    # Create an event loop and feed GStreamer bus messages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # TODO again no idea what this means
    # Add a probe to be informed of the generated metadata.
    # We add a probe to the sink pad of the OSD element,
    # since by that time the buffer will have gotten all the metadata.

    osdsinkpad = nvosd.get_static_pad("sink")
    if not osdsinkpad:
        sys.stderr.write("Unable to get sink pad of nvosd")

    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER,
                         osd_sink_pad_buffer_probe,
                         0)

    # =============================================
    # Start playback and listen to events
    # =============================================

    print("Starting pipeline...")
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    # cleanup
    pyds.unset_callback_funcs()
    pipeline.set_state(Gst.State.NULL)


def parse_args():
    # TODO copy this from deepstream test 4
    # parser = OptionParser()
    global CAM_PATH
    global MSGBROKER_CONFIG_FILE
    global PGIE_CONFIG_FILE
    global MSGCONV_CONFIG_FILE
    global PROTO_LIB

    CAM_PATH = "/dev/video0"
    MSGBROKER_CONFIG_FILE = "cfg_amqp.txt"
    PGIE_CONFIG_FILE = 'dstest4_pgie_config.txt'
    MSGCONV_CONFIG_FILE = 'dstest4_msgconv_config.txt'
    PROTO_LIB = '/opt/nvidia/deepstream/deepstream/lib/libnvds_amqp_proto.so'
    return 0


if __name__ == "__main__":
    ret = parse_args()
    # If argument parsing has failed, return failure (nonzero exit code)
    if ret == 1:
        sys.exit(1)
    sys.exit(main(sys.argv))
