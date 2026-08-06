import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose
from cv_bridge import CvBridge

import cv2
import numpy as np

from ugv_vision.hailo_infer import HailoDetector


def letterbox(image, target_h, target_w):
    """Resize keeping aspect ratio, pad with gray to (target_h, target_w).

    Returns the padded image plus the scale and offsets needed to map
    detection coordinates back into the original image.
    """
    h, w = image.shape[:2]
    scale = min(target_w / w, target_h / h)
    new_w, new_h = round(w * scale), round(h * scale)
    resized = cv2.resize(image, (new_w, new_h))

    pad_x = (target_w - new_w) // 2
    pad_y = (target_h - new_h) // 2

    padded = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
    padded[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
    return padded, scale, pad_x, pad_y


class HailoDetect(Node):
    def __init__(self):
        super().__init__('hailo_detect')

        self.declare_parameter('hef_path', '/home/ws/HailoAi/models/yolov8s.hef',
                                ParameterDescriptor(description='Path to the compiled .hef model'))
        self.declare_parameter('labels_path', '', ParameterDescriptor(
            description='Path to a newline-separated class labels file; defaults to the '
                        'coco_labels.txt shipped with this package'))
        self.declare_parameter('venv_site_packages', '/home/ws/HailoAi/venv/lib/python3.12/site-packages',
                                ParameterDescriptor(description='site-packages dir providing hailo_platform'))
        self.declare_parameter('image_topic', '/image_raw',
                                ParameterDescriptor(description='Input sensor_msgs/Image topic'))
        self.declare_parameter('score_threshold', 0.5,
                                ParameterDescriptor(description='Minimum detection confidence to publish'))

        hef_path = self.get_parameter('hef_path').value
        labels_path = self.get_parameter('labels_path').value
        venv_site_packages = self.get_parameter('venv_site_packages').value
        image_topic = self.get_parameter('image_topic').value
        self.score_threshold = self.get_parameter('score_threshold').value

        if not labels_path:
            from ament_index_python.packages import get_package_share_directory
            import os
            labels_path = os.path.join(get_package_share_directory('ugv_vision'),
                                        'config', 'coco_labels.txt')

        with open(labels_path) as f:
            self.labels = [line.strip() for line in f if line.strip()]

        self.get_logger().info(f'Loading {hef_path} ...')
        self.detector = HailoDetector(hef_path, venv_site_packages)
        self.get_logger().info(
            f'Hailo model ready, input {self.detector.input_width}x{self.detector.input_height}')

        self.bridge = CvBridge()
        self.image_subscription = self.create_subscription(
            Image, image_topic, self.image_callback, 10)
        self.detections_publisher = self.create_publisher(
            Detection2DArray, '/hailo_detect/detections', 10)
        self.result_publisher = self.create_publisher(
            Image, '/hailo_detect/result', 10)

    def image_callback(self, msg):
        frame_bgr = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        padded, scale, pad_x, pad_y = letterbox(
            frame_rgb, self.detector.input_height, self.detector.input_width)

        per_class_detections = self.detector.infer(padded)

        detection_array = Detection2DArray()
        detection_array.header = msg.header

        for class_id, class_detections in enumerate(per_class_detections):
            label = self.labels[class_id] if class_id < len(self.labels) else str(class_id)
            for x1, y1, x2, y2, score in class_detections:
                if score < self.score_threshold:
                    continue

                # Undo letterbox padding/scaling to get pixel coords in the original frame.
                x1 = (x1 * self.detector.input_width - pad_x) / scale
                x2 = (x2 * self.detector.input_width - pad_x) / scale
                y1 = (y1 * self.detector.input_height - pad_y) / scale
                y2 = (y2 * self.detector.input_height - pad_y) / scale

                detection = Detection2D()
                detection.header = msg.header
                detection.bbox.center.position.x = (x1 + x2) / 2.0
                detection.bbox.center.position.y = (y1 + y2) / 2.0
                detection.bbox.size_x = x2 - x1
                detection.bbox.size_y = y2 - y1

                hypothesis = ObjectHypothesisWithPose()
                hypothesis.hypothesis.class_id = label
                hypothesis.hypothesis.score = float(score)
                detection.results.append(hypothesis)

                detection_array.detections.append(detection)

                cv2.rectangle(frame_bgr, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(frame_bgr, f'{label} {score:.2f}', (int(x1), max(int(y1) - 5, 0)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        self.detections_publisher.publish(detection_array)
        self.result_publisher.publish(self.bridge.cv2_to_imgmsg(frame_bgr, encoding='bgr8'))

    def destroy_node(self):
        self.detector.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = HailoDetect()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
