import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image

from litevla_edge.action_schema import parse_model_output


class DummyVlaController(Node):
    def __init__(self) -> None:
        super().__init__("litevla_dummy_controller")
        self.declare_parameter("instruction", "Move toward the red cube")
        self.declare_parameter("dummy_action", "MOVE_FORWARD")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("image_topic", "/image_raw")
        self.declare_parameter("publish_hz", 6.6)
        self.declare_parameter("max_linear_x", 0.2)
        self.declare_parameter("max_angular_z", 0.6)
        self.declare_parameter("estop", False)

        cmd_vel_topic = self.get_parameter("cmd_vel_topic").value
        image_topic = self.get_parameter("image_topic").value
        publish_hz = float(self.get_parameter("publish_hz").value)

        self.publisher = self.create_publisher(Twist, cmd_vel_topic, 10)
        self.create_subscription(Image, image_topic, self.on_image, 10)
        self.latest_image_stamp = None
        self.frame_count = 0
        self.timer = self.create_timer(1.0 / publish_hz, self.on_timer)

        self.get_logger().info(
            f"Publishing safe dummy actions to {cmd_vel_topic} at {publish_hz:.2f} Hz"
        )
        self.get_logger().info(f"Listening for camera frames on {image_topic}")

    def on_image(self, msg: Image) -> None:
        self.latest_image_stamp = msg.header.stamp
        self.frame_count += 1

    def on_timer(self) -> None:
        start = time.perf_counter()
        instruction = self.get_parameter("instruction").value
        raw_action = self.get_parameter("dummy_action").value
        estop = bool(self.get_parameter("estop").value)

        if estop:
            command = parse_model_output("STOP")
        else:
            command = parse_model_output(
                raw_action,
                float(self.get_parameter("max_linear_x").value),
                float(self.get_parameter("max_angular_z").value),
            )

        twist = Twist()
        twist.linear.x = command.linear_x
        twist.angular.z = command.angular_z
        self.publisher.publish(twist)

        latency_ms = (time.perf_counter() - start) * 1000.0
        self.get_logger().info(
            "instruction=%r raw=%r parsed=%s valid=%s cmd=(%.3f, %.3f) "
            "frames=%d latency_ms=%.3f"
            % (
                instruction,
                raw_action,
                command.action,
                command.valid,
                twist.linear.x,
                twist.angular.z,
                self.frame_count,
                latency_ms,
            ),
            throttle_duration_sec=1.0,
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = DummyVlaController()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
