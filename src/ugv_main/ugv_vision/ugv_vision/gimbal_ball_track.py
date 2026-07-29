import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from sensor_msgs.msg import Image, JointState

# Joint limits from ugv_description/urdf/rasp_rover.urdf
PAN_JOINT = 'pt_base_link_to_pt_link1'
TILT_JOINT = 'pt_link1_to_pt_link2'
PAN_LIMITS = (-3.14, 3.14)
TILT_LIMITS = (-0.5233333, 1.5707963)


class GimbalBallTrack(Node):
    """Keeps a color-tracked ball centered in frame by driving the pan/tilt gimbal.

    Proportional tracker ported from ugv_rpi/cv_ctrl.py's gimbal_track(): the
    pixel offset between the blob centroid and the frame center is scaled by a
    gain and accumulated into the current pan/tilt angle every frame, rather
    than commanding an absolute angle. Publishes to ugv/joint_states, which
    ugv_bringup.py already forwards to the gimbal over UART.
    """

    def __init__(self):
        super().__init__('gimbal_ball_track')

        self.declare_parameter('image_topic', '/image_raw',
                                ParameterDescriptor(description='Camera topic to track the ball in'))
        self.declare_parameter('lower_hue', 0, ParameterDescriptor(description='Lower Hue'))
        self.declare_parameter('lower_saturation', 115, ParameterDescriptor(description='Lower Saturation'))
        self.declare_parameter('lower_value', 70, ParameterDescriptor(description='Lower Value'))
        self.declare_parameter('upper_hue', 5, ParameterDescriptor(description='Upper Hue'))
        self.declare_parameter('upper_saturation', 255, ParameterDescriptor(description='Upper Saturation'))
        self.declare_parameter('upper_value', 255, ParameterDescriptor(description='Upper Value'))
        self.declare_parameter('min_blob_area', 200.0,
                                ParameterDescriptor(description='Minimum contour area (px^2) to count as the ball'))
        self.declare_parameter('pan_gain', 0.003,
                                ParameterDescriptor(description='Radians of pan per pixel of horizontal offset'))
        self.declare_parameter('tilt_gain', 0.003,
                                ParameterDescriptor(description='Radians of tilt per pixel of vertical offset'))

        self.bridge = CvBridge()
        self.pan = 0.0
        self.tilt = 0.0

        image_topic = self.get_parameter('image_topic').value
        self.image_sub = self.create_subscription(Image, image_topic, self.image_callback, 10)
        self.joint_state_pub = self.create_publisher(JointState, 'ugv/joint_states', 10)
        self.result_pub = self.create_publisher(Image, 'gimbal_ball_track/result', 10)

        self.get_logger().info(f'gimbal_ball_track tracking ball on {image_topic}')

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        height, width = frame.shape[:2]
        center_x, center_y = width // 2, height // 2

        lower = np.array([
            self.get_parameter('lower_hue').value,
            self.get_parameter('lower_saturation').value,
            self.get_parameter('lower_value').value,
        ])
        upper = np.array([
            self.get_parameter('upper_hue').value,
            self.get_parameter('upper_saturation').value,
            self.get_parameter('upper_value').value,
        ])

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            ball = max(contours, key=cv2.contourArea)
            if cv2.contourArea(ball) >= self.get_parameter('min_blob_area').value:
                x, y, w, h = cv2.boundingRect(ball)
                cx, cy = x + w // 2, y + h // 2
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)
                self.track(center_x, center_y, cx, cy)

        result_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        result_msg.header = msg.header
        self.result_pub.publish(result_msg)

    def track(self, fx, fy, gx, gy):
        pan_gain = self.get_parameter('pan_gain').value
        tilt_gain = self.get_parameter('tilt_gain').value

        self.pan = clamp(self.pan + (gx - fx) * pan_gain, *PAN_LIMITS)
        self.tilt = clamp(self.tilt + (fy - gy) * tilt_gain, *TILT_LIMITS)

        joint_state = JointState()
        joint_state.header.stamp = self.get_clock().now().to_msg()
        joint_state.name = [PAN_JOINT, TILT_JOINT]
        joint_state.position = [self.pan, self.tilt]
        self.joint_state_pub.publish(joint_state)


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def main(args=None):
    rclpy.init(args=args)
    node = GimbalBallTrack()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
