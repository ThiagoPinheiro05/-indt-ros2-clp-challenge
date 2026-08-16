import json
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose

import paho.mqtt.client as mqtt


MQTT_BROKER = 'localhost'
MQTT_PORT = 1883
MQTT_TOPIC = 'turtlesim/velocity'
PUBLISH_RATE_HZ = 10.0


class TurtleListener(Node):
    def __init__(self):
        super().__init__('turtle_listener')

        self.linear_vel = 0.0
        self.angular_vel = 0.0
        self.pose_linear_vel = 0.0
        self.pose_angular_vel = 0.0

        self.cmd_vel_sub = self.create_subscription(
            Twist, '/turtle1/cmd_vel', self.cmd_vel_callback, 10
        )
        self.pose_sub = self.create_subscription(
            Pose, '/turtle1/pose', self.pose_callback, 10
        )

        # --- Configuração do cliente MQTT ---
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_connected = False
        self.connect_mqtt()

        # Publica periodicamente (10 Hz, conforme sugerido no desafio)
        self.timer = self.create_timer(1.0 / PUBLISH_RATE_HZ, self.publish_mqtt)

        self.get_logger().info('turtle_listener iniciado. Aguardando dados...')

    def connect_mqtt(self):
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=10)
            self.mqtt_client.loop_start()
        except Exception as e:
            self.get_logger().warn(f'Falha ao conectar no broker MQTT: {e}')

    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties=None):
        self.mqtt_connected = True
        self.get_logger().info(f'Conectado ao broker MQTT ({MQTT_BROKER}:{MQTT_PORT})')

    def on_mqtt_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.mqtt_connected = False
        self.get_logger().warn('Desconectado do broker MQTT. Tentando reconectar...')

    def cmd_vel_callback(self, msg: Twist):
        self.linear_vel = msg.linear.x
        self.angular_vel = msg.angular.z

    def pose_callback(self, msg: Pose):
        self.pose_linear_vel = msg.linear_velocity
        self.pose_angular_vel = msg.angular_velocity

    def publish_mqtt(self):
        payload = {
            'timestamp': time.time(),
            'cmd_linear': self.linear_vel,
            'cmd_angular': self.angular_vel,
            'pose_linear': self.pose_linear_vel,
            'pose_angular': self.pose_angular_vel,
        }
        if self.mqtt_connected:
            self.mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=0)
        else:
            self.get_logger().warn('MQTT desconectado, payload não enviado.')

    def destroy_node(self):
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = TurtleListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
