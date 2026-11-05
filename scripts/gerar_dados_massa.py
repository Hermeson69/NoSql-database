#!/usr/bin/env python3
"""
scripts/gerar_dados_massa.py
Gera 50.000 registros sintéticos de telemetria IoT em formato CSV
para demonstração de grande volume de dados no Apache Cassandra.
Não requer bibliotecas externas (usa apenas a biblioteca padrão do Python).
"""

import csv
import os
import random
from datetime import datetime, timedelta

NUM_REGISTROS = 50000
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "dados_sensores.csv")

# Lista diversificada de sensores por aplicação e ambiente
SENSORES = [
    # Compatibilidade com roteiros de apresentação e testes prévios
    "SENSOR-SP-001",
    "SENSOR-RJ-002",

    # Indústria & Fábricas
    "FORNO-IND-LINHA-A",
    "CALDEIRA-VAPOR-SETOR-3",
    "TURBINA-HIDRAULICA-02",
    "MOTOR-GERADOR-DIESEL-01",
    "PRENSA-HIDRAULICA-P08",
    "COMPRESSOR-AR-CENTRAL",

    # Câmaras Frias & Armazenamento Alimentício
    "CAMARA-FRIA-CARNES-01",
    "CAMARA-CONGELADOS-SETOR-B",
    "SILO-GRAOS-SOJA-NORTE",
    "ADEGA-CLIMATIZADA-04",

    # Tecnologia, Data Centers & Telecom
    "DATACENTER-RACK-TI-01",
    "DATACENTER-RACK-TI-12",
    "SALA-SERVIDORES-CORE",
    "TORRE-TELECOM-5G-SUL",

    # Cidades Inteligentes & Meio Ambiente
    "ESTACAO-METEO-CENTRO",
    "ESTACAO-METEO-SERRA-04",
    "QUALIDADE-AR-AV-PAULISTA",
    "BOIA-OCEANICA-COSTEIRA-07",
    "SENSOR-PLUVIOMETRICO-VALE",

    # Saúde, Farmacêutica & Laboratórios
    "LAB-CRIOGENIA-VACINAS-01",
    "BANCO-SANGUE-ULTRAFRIO-02",
    "CENTRO-CIRURGICO-SALA-4",
    "INCUBADORA-BIOLOGICA-B03",

    # Energia & Sustentabilidade
    "PAINEL-SOLAR-FAZENDA-L05",
    "BANCO-BATERIAS-NOBREAK-02",
    "SUBESTACAO-TRANSFORMADOR-09",
    "AEROGERADOR-EOLICO-P14",

    # Logística & Frota Móvel
    "CAMINHAO-FRIGORIFICO-FROTA-22",
    "CONTAINER-MARITIMO-REEFER-88",
    "DRONE-AGRO-MONITORAMENTO-03",

    # Agronegócio & Irrigação
    "ESTUFA-HIDROPONICA-ALFACE-01",
    "PIVO-IRRIGACAO-TALHAO-15",
    "SENSOR-UMIDADE-SOLO-GLEBA-B"
]

STATUS_OPCOES = ["NORMAL", "NORMAL", "NORMAL", "NORMAL", "NORMAL", "ALERTA", "CRITICO"]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Gerando {NUM_REGISTROS:,} registros de telemetria IoT com {len(SENSORES)} tipos de sensores distintos...")
    
    data_base = datetime(2026, 10, 24, 0, 0, 0)
    
    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sensor_id", "data_leitura", "timestamp", "temperatura", "umidade", "tensao_bateria", "status"])
        
        for i in range(NUM_REGISTROS):
            sensor = random.choice(SENSORES)
            delta_segundos = random.randint(0, 86400 * 3)  # Variação de 3 dias
            dt = data_base + timedelta(seconds=delta_segundos)
            
            data_leitura = dt.strftime("%Y-%m-%d")
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S+0000")
            
            # Faixas térmicas personalizadas para maior realismo de acordo com o tipo
            if "CAMARA" in sensor or "CRIOGENIA" in sensor or "ULTRAFRIO" in sensor:
                temperatura = round(random.uniform(-25.0, 4.0), 2)
                umidade = round(random.uniform(70.0, 98.0), 2)
            elif "FORNO" in sensor or "CALDEIRA" in sensor or "TURBINA" in sensor:
                temperatura = round(random.uniform(45.0, 120.0), 2)
                umidade = round(random.uniform(15.0, 40.0), 2)
            elif "DATACENTER" in sensor or "SALA-SERVIDORES" in sensor:
                temperatura = round(random.uniform(18.0, 24.5), 2)
                umidade = round(random.uniform(40.0, 55.0), 2)
            else:
                temperatura = round(random.uniform(15.0, 38.5), 2)
                umidade = round(random.uniform(30.0, 95.0), 2)

            tensao = round(random.uniform(3.4, 4.2), 2)
            status = random.choice(STATUS_OPCOES)
            
            writer.writerow([sensor, data_leitura, timestamp_str, temperatura, umidade, tensao, status])
            
            if (i + 1) % 10000 == 0:
                print(f"  -> {i + 1:,} registros gerados...")

    tamanho_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\n[SUCESSO] Arquivo gerado: {OUTPUT_FILE}")
    print(f"Tamanho total: {tamanho_mb:.2f} MB")
    print("\nPara importar no Cassandra com velocidade máxima via cqlsh:")
    print("docker exec -i cassandra-node1 cqlsh localhost 9042 -e \"COPY telemetria.sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status) FROM '/dados/dados_sensores.csv' WITH HEADER = TRUE;\"")

if __name__ == "__main__":
    main()
