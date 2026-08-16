import time
import threading

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.server import StartTcpServer


HOST = '0.0.0.0'
PORT = 5030

# Registrador 0: MotorSpeedPercent (0-100)
# Registrador 1: MotorEnable (0/1)
# Registrador 2: MotorDirectionFwd (0/1)

store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0] * 10))
context = ModbusServerContext(slaves=store, single=True)


def monitor():
    last = None
    while True:
        values = store.getValues(3, 0, count=3)
        if values != last:
            speed, enable, direction = values
            direction_str = 'FRENTE' if direction == 1 else 'RÉ'
            status = 'LIGADO' if enable == 1 else 'DESLIGADO'
            print(f'[Motor Simulado] Velocidade: {speed}% | Status: {status} | Sentido: {direction_str}')
            last = values
        time.sleep(0.1)


if __name__ == '__main__':
    threading.Thread(target=monitor, daemon=True).start()
    print(f'[Driver do Motor] Escutando como escravo Modbus em {HOST}:{PORT}')
    print('Registradores: 0=velocidade(%) 1=enable(0/1) 2=direcao(0=re,1=frente)')
    StartTcpServer(context=context, address=(HOST, PORT))
