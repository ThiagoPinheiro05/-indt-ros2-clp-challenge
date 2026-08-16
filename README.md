# Desafio de Engenharia INDT — Integração ROS 2 ↔ Automação Industrial

Ponte entre robótica ROS 2 (turtlesim) e um CLP (OpenPLC), controlando um driver de motor via Modbus, com a velocidade do motor refletindo proporcionalmente a velocidade da tartaruga na simulação.

## Arquitetura

turtlesim (ROS 2 Jazzy)
| /turtle1/cmd_vel, /turtle1/pose
v
turtle_listener (nó ROS 2 / rclpy)
| MQTT (JSON, 10 Hz) — tópico "turtlesim/velocity"
v
bridge.py (ponte MQTT -> Modbus TCP)
| Modbus TCP (servidor escravo, porta 5020)
v
OpenPLC Runtime (mestre Modbus)
| lógica em Structured Text (escalonamento, zona morta,
| rampa de aceleração, watchdog de segurança)
| Modbus TCP (mestre, porta 5030)
v
driver.py (simulador do driver de motor / escravo Modbus)

## Por que MQTT em vez de OPC UA

O OpenPLC (versão utilizada neste projeto) não possui suporte nativo a MQTT nem a OPC UA — apenas a Modbus (TCP/RTU) e DNP3. Por isso, foi adotado MQTT para o transporte ROS 2 → gateway (mais simples de implementar e testar localmente com o broker Mosquitto), seguido de uma ponte própria em Python que traduz as mensagens MQTT para registradores Modbus, os quais o OpenPLC consulta como mestre através da funcionalidade "Slave Devices" do seu painel web.

A latência observada em ambiente local (mesma máquina, WSL2) foi da ordem de dezenas de milissegundos entre o comando na tartaruga e a reação do driver simulado, bem dentro do requisito de 500 ms do desafio.

## Componentes

| Pasta | Descrição |
|---|---|
| `ros2_gateway/turtle_gateway/` | Pacote ROS 2 (Python/rclpy). Assina `/turtle1/cmd_vel` e `/turtle1/pose`, publica em MQTT a 10 Hz. |
| `mqtt_modbus_bridge/bridge.py` | Assina o tópico MQTT e expõe os dados como servidor Modbus TCP (escravo). |
| `motor_driver_sim/driver.py` | Simula um driver de motor: servidor Modbus TCP que recebe comandos do OpenPLC e imprime o status no terminal. |
| `clp_program/turtle_motor_control.st` | Programa em Structured Text (IEC 61131-3) rodando no OpenPLC. |

## Mapa de registradores Modbus

### bridge.py — porta 5020 (lido pelo OpenPLC como Slave Device, endereços `%IW100`–`%IW104`)

| Registrador | Endereço IEC no CLP | Conteúdo |
|---|---|---|
| 0 | `%IW100` | Velocidade linear comandada (m/s × 100) |
| 1 | `%IW101` | Velocidade angular comandada (rad/s × 100) |
| 2 | `%IW102` | Velocidade linear medida (m/s × 100) |
| 3 | `%IW103` | Velocidade angular medida (rad/s × 100) |
| 4 | `%IW104` | Heartbeat (contador incremental, para watchdog) |

### Memória interna do CLP (Structured Text)

| Endereço IEC | Variável | Conteúdo |
|---|---|---|
| `%MW10` | MotorSpeedPercent | Velocidade final do motor, 0–100% |
| `%MW11` | MotorEnable | 0 = desligado, 1 = ligado |
| `%MW12` | MotorDirectionFwd | 0 = ré, 1 = frente |
| `%MW13` | WatchdogFault | 0 = comunicação ok, 1 = falha (sem dados há mais de 1s) |

### driver.py — porta 5030 (escrito pelo OpenPLC como Slave Device, endereços `%QW100`–`%QW102`)

| Registrador | Endereço IEC no CLP | Conteúdo |
|---|---|---|ros2 run turtlesim turtlesim_node
| 0 | `%QW100` | Velocidade do motor, 0–100% |
| 1 | `%QW101` | Enable (0/1) |
| 2 | `%QW102` | Sentido (0=ré, 1=frente) |

## Lógica implementada (Etapa 3)

- **Escalonamento**: 0–2 m/s (tartaruga) → 0–100% (motor)
- **Zona morta**: comandos abaixo de 0.05 m/s são tratados como zero
- **Limite de segurança**: saída nunca ultrapassa 100%
- **Rampa de aceleração**: subida gradual (3% por ciclo de scan de 20ms); desaceleração/parada são sempre imediatas, por segurança
- **Sentido de rotação**: reflete o sinal da velocidade linear comandada
- **Watchdog**: se o heartbeat não mudar por mais de 1 segundo, a velocidade é zerada automaticamente

## Como rodar (Ubuntu 24.04 / WSL2)

Pré-requisitos: ROS 2 Jazzy, Mosquitto, Python 3 com `paho-mqtt` e `pymodbus==3.7.4`, OpenPLC Runtime v3.

1. **turtlesim**

ros2 run turtlesim turtlesim_node
ros2 run turtlesim turtle_teleop_key

2. **Nó gateway ROS 2** (dentro do workspace colcon, após `colcon build` e `source install/setup.bash`)

ros2 run turtle_gateway turtle_listener

3. **Ponte MQTT → Modbus**

cd mqtt_modbus_bridge
python3 bridge.py

4. **Simulador do driver de motor**

cd motor_driver_sim
python3 driver.py

5. **OpenPLC**: enviar `clp_program/turtle_motor_control.st` pela página "Programs" do painel web (`localhost:8080`), configurar os dois Slave Devices (`bridge_turtlesim` na porta 5020, leitura; `motor_driver_sim` na porta 5030, escrita) e clicar em "Start PLC".

## Problemas encontrados e soluções

- **Permissão de arquivos no OpenPLC**: a instalação via `sudo ./install.sh` deixou o arquivo `glueVars.cpp` (que conecta as variáveis do programa à memória do runtime) de propriedade do usuário `root`, impedindo recompilações como usuário comum de terem efeito. Resolvido com `sudo chown -R $USER:$USER ~/OpenPLC_v3`.
- **Variáveis booleanas com endereço `%MX`**: não refletiam valor real no runtime testado, mesmo compiladas sem erro. Contornado representando os sinais booleanos como inteiros (0/1) em registradores `%MW`/`%QW`.
- **Blocos `VAR` mistos**: o compilador do OpenPLC exige que variáveis com endereço fixo (`AT %...`) fiquem em um bloco `VAR` separado de variáveis internas comuns.

## Requisitos funcionais atendidos

- [x] Latência ponta a ponta abaixo de 500 ms
- [x] Motor para quando a tartaruga para (comando de velocidade linear zero)
- [x] Sentido de rotação reflete o sinal da velocidade linear
- [x] Watchdog de 1s zera a velocidade em caso de perda de comunicação

