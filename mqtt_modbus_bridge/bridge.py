import json
import threading

import paho.mqtt.client as mqtt

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.server import StartTcpServer


MQTT_BROKER = 'localhost'
MQTT_PORT = 1883
MQTT_TOPIC = 'turtlesim/velocity'

MODBUS_HOST = '0.0.0.0'
MODBUS_PORT = 5020  # diferente da 502 usada pelo servidor interno do OpenPLC

# Registrador 0: cmd_linear_vel  (x100, inteiro)
# Registrador 1: cmd_angular_vel (x100, inteiro)
# Registrador 2: pose_linear_vel (x100, inteiro)
# Registrador 3: pose_angular_vel (x100, inteiro)
# Registrador 4: heartbeat (contador incremental, para watchdog no CLP)

heartbeat_counter = 0

store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, [0] * 10)
)
context = ModbusServerContext(slaves=store, single=True)


def scale(value, factor=100):
    scaled = int(value * factor)
    return scaled & 0xFFFF  # garante 16 bits, tratando negativos como complemento de 2


def on_message(client, userdata, msg):
    global heartbeat_counter
    try:
        payload = json.loads(msg.payload.decode())
        heartbeat_counter = (heartbeat_counter + 1) % 65536

        context[0].setValues(3, 0, [
            scale(payload.get('cmd_linear', 0.0)),
            scale(payload.get('cmd_angular', 0.0)),
            scale(payload.get('pose_linear', 0.0)),
            scale(payload.get('pose_angular', 0.0)),
            heartbeat_counter,
        ])
    except Exception as e:
        print(f'Erro ao processar mensagem MQTT: {e}')


def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message

    def on_connect(client, userdata, flags, reason_code, properties=None):
        print(f'[MQTT] Conectado ao broker ({MQTT_BROKER}:{MQTT_PORT})')
        client.subscribe(MQTT_TOPIC)

    client.on_connect = on_connect
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=10)
    client.loop_forever()


if __name__ == '__main__':
    mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
    mqtt_thread.start()

    print(f'[Modbus] Servidor TCP escravo iniciado em {MODBUS_HOST}:{MODBUS_PORT}')
    print('Registradores: 0=cmd_linear 1=cmd_angular 2=pose_linear 3=pose_angular 4=heartbeat')
    StartTcpServer(context=context, address=(MODBUS_HOST, MODBUS_PORT))
