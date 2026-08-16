import json
import time
import statistics

import paho.mqtt.client as mqtt

MQTT_BROKER = 'localhost'
MQTT_PORT = 1883
MQTT_TOPIC = 'turtlesim/velocity'

latencies = []


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        sent_time = payload.get('timestamp')
        if sent_time is not None:
            latency_ms = (time.time() - sent_time) * 1000
            latencies.append(latency_ms)
            print(f'Latência ROS2 -> MQTT recebido: {latency_ms:.2f} ms')
    except Exception as e:
        print(f'Erro: {e}')


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f'Conectado ao broker. Coletando amostras por 10 segundos...')
    client.subscribe(MQTT_TOPIC)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, keepalive=10)
client.loop_start()

time.sleep(10)
client.loop_stop()

if latencies:
    print('\n--- Resultado ---')
    print(f'Amostras coletadas: {len(latencies)}')
    print(f'Latência média: {statistics.mean(latencies):.2f} ms')
    print(f'Latência mínima: {min(latencies):.2f} ms')
    print(f'Latência máxima: {max(latencies):.2f} ms')
else:
    print('Nenhuma amostra coletada. Confirme que turtle_listener.py está publicando.')
