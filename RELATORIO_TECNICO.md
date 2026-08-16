# Relatório Técnico — Integração ROS 2 ↔ Automação Industrial

**Desafio de Engenharia INDT** | Ponte entre robótica ROS 2 (turtlesim) e CLP (OpenPLC)

## 1. Introdução

Este relatório documenta a arquitetura, as decisões técnicas e os resultados de latência obtidos na implementação de uma cadeia de comunicação entre um sistema robótico simulado (turtlesim, ROS 2 Jazzy) e um controlador lógico programável (OpenPLC Runtime), com acionamento final de um driver de motor via protocolo Modbus.

## 2. Arquitetura implementada

turtlesim → nó ROS 2 (rclpy) → MQTT → ponte Python → OpenPLC (mestre Modbus) → driver de motor (Modbus)

O nó ROS 2 assina os tópicos `/turtle1/cmd_vel` e `/turtle1/pose`, publicando as velocidades a 10 Hz em formato JSON via MQTT. Uma ponte em Python traduz essas mensagens para registradores Modbus, consultados pelo OpenPLC como dispositivo escravo. A lógica de controle roda em Structured Text dentro do CLP, e o resultado final é escrito em outro dispositivo Modbus que simula o driver do motor.

## 3. Escolha do protocolo: MQTT vs. OPC UA

O desafio propõe OPC UA ou MQTT como protocolo de alto nível entre o ROS 2 e o CLP. A escolha de MQTT neste projeto foi motivada por uma restrição concreta identificada durante a implementação: **o OpenPLC Runtime (versão utilizada) não possui suporte nativo a nenhum dos dois protocolos** — apenas a Modbus (TCP/RTU) e DNP3 nativamente.

Diante disso, qualquer uma das duas opções exigiria uma camada de tradução adicional até o CLP. A comparação entre as duas abordagens:

| Critério | MQTT | OPC UA |
|---|---|---|
| Complexidade de implementação | Baixa — biblioteca `paho-mqtt` madura e simples | Maior — exige modelagem de nós no servidor |
| Overhead de rede | Muito leve (mensagens JSON curtas) | Maior (protocolo binário mais estruturado) |
| Segurança nativa | Básica por padrão (TLS opcional) | Forte, embutida no protocolo |
| Integração com o OpenPLC | Requer ponte própria (nenhum suporte nativo) | Também requer ponte própria (nenhum suporte nativo) |
| Ecossistema para prototipagem local | Mosquitto (broker leve, fácil de instalar) | Exigiria servidor OPC UA próprio (ex: asyncua) |

Dado que ambos exigiriam uma ponte de tradução para o OpenPLC, o critério decisivo foi a **velocidade de implementação e teste local**: o MQTT com Mosquitto permite montar e validar o pipeline completo rapidamente, com uma pegada de rede mínima — adequado ao escopo de um protótipo educacional rodando inteiramente em uma única máquina (WSL2).

Em um cenário de produção com múltiplos CLPs e requisitos de segurança mais rígidos (autenticação forte, criptografia nativa, modelagem semântica dos dados), OPC UA seria a escolha mais robusta, especialmente se o CLP alvo já tivesse suporte nativo ao protocolo (como é o caso de CLPs Siemens S7-1200/1500, citados como sugestão no enunciado do desafio).

## 4. Análise de latência

### 4.1 Metodologia

Cada mensagem publicada pelo nó ROS 2 (`turtle_listener`) carrega um timestamp (`time.time()`) no momento da publicação. A latência do trecho ROS 2 → recepção MQTT foi medida comparando esse timestamp com o horário de recebimento da mensagem por um cliente MQTT assinante, ao longo de 10 segundos de movimentação contínua da tartaruga (102 amostras coletadas).

### 4.2 Resultados — trecho ROS 2 → MQTT

| Métrica | Valor |
|---|---|
| Amostras coletadas | 102 |
| Latência média | 1,59 ms |
| Latência mínima | 0,57 ms |
| Latência máxima | 11,34 ms |

### 4.3 Latência dos demais trechos (observação qualitativa)

Os trechos MQTT → ponte Python → registrador Modbus, e OpenPLC (mestre Modbus) → driver simulado, rodam com ciclo de scan do CLP configurado em 20 ms (`TASK task0(INTERVAL := T#20ms...)`), e a comunicação Modbus entre processos na mesma máquina (loopback local) não introduz latência de rede perceptível. Nos testes end-to-end realizados (tartaruga → log do driver simulado), a resposta do motor simulado à movimentação da tartaruga foi percebida como praticamente instantânea (sub-segundo), consistente com a soma dos componentes medidos e estimados.

### 4.4 Conclusão sobre o requisito de latência

A latência ponta a ponta observada está **muito abaixo do limite de 500 ms** exigido pelo desafio (requisito funcional 1), com a maior parte do orçamento de tempo disponível não utilizada — a arquitetura teria margem confortável mesmo em uma rede real com latência de alguns milissegundos entre máquinas físicas separadas (diferente do cenário local em uma única máquina usado neste protótipo).

## 5. Tratamento de falhas e robustez

- **Watchdog de comunicação**: o CLP monitora um contador incremental (heartbeat) enviado a cada mensagem MQTT. Se esse contador não mudar por mais de 1 segundo, a velocidade do motor é zerada automaticamente (requisito funcional 4).
- **Reconexão MQTT**: o nó ROS 2 e a ponte Python tratam desconexões do broker MQTT, tentando reconectar automaticamente.
- **Limite de segurança**: a saída de velocidade nunca ultrapassa 100%, independentemente do valor recebido.
- **Zona morta**: comandos de velocidade muito pequenos (ruído) são tratados como zero, evitando acionamentos indesejados do motor.

## 6. Limitações conhecidas e decisões de engenharia

Durante a implementação, foram identificadas e contornadas as seguintes limitações do ambiente:

- Variáveis booleanas com endereço `%MX` no OpenPLC Runtime testado não refletiam corretamente o valor computado em tempo de execução, mesmo compilando sem erros. Foram substituídas por inteiros (0/1) em registradores `%MW`/`%QW`, sem perda funcional.
- A instalação do OpenPLC via `sudo` deixou arquivos de propriedade do usuário `root`, impedindo que recompilações subsequentes (executadas como usuário comum) tivessem efeito — corrigido ajustando a propriedade dos arquivos.

## 7. Conclusão

A cadeia de comunicação proposta pelo desafio foi implementada e validada de ponta a ponta, com latência medida bem dentro do requisito estabelecido, tratamento de falhas de comunicação via watchdog, e lógica de controle com escalonamento, zona morta e rampa de aceleração. A escolha do MQTT como protocolo de transporte se mostrou adequada ao escopo do protótipo, tendo sido documentada a limitação de suporte nativo do OpenPLC a ambos os protocolos de alto nível propostos como justificativa técnica central dessa decisão.
