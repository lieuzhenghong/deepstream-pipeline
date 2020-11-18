# Remember to set
# export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python3.6/pyrealsense2
# otherwise you will not see pyrealsense2
# you will get ModuleNotFoundError

from io import BytesIO
import numpy as np

def send_image_to_server(img):
    '''
    Takes a numpy array 
    '''
    import socket 
    import sys

    HEADER_SIZE = 10

    server_address = ('localhost', 6000)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(server_address) 
        try:
            message = BytesIO()
            np.save(message, img)

            msg_len = message.getbuffer().nbytes
            b_msg_len = bytes(str(f"{msg_len:<{HEADER_SIZE}}"), 'utf-8')
            sock.sendall(b_msg_len)

            print("Sending message...")
            message.seek(0)
            sock.sendall(message.read())
            print("All sent!")

            # Now receive data
            full_data = BytesIO()
            while True:
                data = sock.recv(4096)
                print(len(data))
                if not data:
                    print("All data received!")
                    break
                full_data.write(data) 

        finally:
            print("Closing connection")
            sock.close()

    full_data.seek(0)
    assert(full_data.getbuffer().nbytes > 0)
    bboxes = np.load(full_data, allow_pickle=True)
    return bboxes


def main():
    import pyrealsense2 as rs

    # Configure depth and color streams
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    # Start streaming
    pipeline.start(config)

    try:
        frame_counter = 0
        while True:
            #for i in range(1):
            # Wait for a coherent pair of frames: depth and color
            frames = pipeline.wait_for_frames()
            frame_counter += 1
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            if not depth_frame or not color_frame:
                continue

            # Convert images to numpy arrays
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            print(f"Sending image {frame_counter}...")
            bboxes = send_image_to_server(color_image)
            print(np.shape(bboxes))
            print(f"Images received!")

            # Package to be sent eventually
            package = [bboxes, depth_image]
            print(len(bboxes))
            print(np.shape(bboxes), np.shape(depth_image))
            # print(package)

            # display_images(depth_image, color_image)

    finally:
        # Stop streaming
        pipeline.stop()


def display_images(depth_image, color_image):
    import cv2
    # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

    # Stack both images horizontally
    images = np.hstack((color_image, depth_colormap))

    # Show images
    cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
    cv2.imshow('RealSense', images)
    cv2.waitKey(1)

main()
