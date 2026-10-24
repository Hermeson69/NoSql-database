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

SENSORES = [
    "SENSOR-SP-001", "SENSOR-SP-002", "SENSOR-RJ-001", "SENSOR-RJ-002",
    "SENSOR-MG-001", "SENSOR-PR-001", "SENSOR-RS-001", "SENSOR-BA-001",
    "SENSOR-SC-001", "SENSOR-PE-001"
]

STATUS_OPCOES = ["NORMAL", "NORMAL", "NORMAL", "NORMAL", "ALERTA", "CRITICO"]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Gerando {NUM_REGISTROS:,} registros de telemetria IoT...")
    
    data_base = datetime(2026, 10, 24, 0, 0, 0)
    
    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sensor_id", "data_leitura", "timestamp", "temperatura", "umidade", "tensao_bateria", "status"])
        
        for i in range(NUM_REGISTROS):
            sensor = random.choice(SENSORES)
            delta_segundos = random.randint(0, 86400 * 3) # Variação de 3 dias
            dt = data_base + timedelta(seconds=delta_segundos)
            
            data_leitura = dt.strftime("%Y-%m-%d")
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S+0000")
            temperatura = round(random.uniform(18.0, 38.5), 2)
            umidade = round(random.uniform(40.0, 95.0), 2)
            tensao = round(random.uniform(3.5, 4.2), 2)
            status = random.choice(STATUS_OPCOES)
            
            writer.writerow([sensor, data_leitura, timestamp_str, temperatura, umidade, tensao, status])
            
            if (i + 1) % 10000 == 0:
                print(f"  -> {i + 1:,} registros gerados...")

    tamanho_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\n[SUCESSO] Arquivo gerado: {OUTPUT_FILE}")
    print(f"Tamanho total: {tamanho_mb:.2f} MB")
    print("\nPara importar no Cassandra com velocidade máxima via cqlsh:")
    print("docker compose exec -T cassandra-node1 cqlsh -u cassandra -p cassandra -e \"COPY telemetria.sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status) FROM '/dados/dados_sensores.csv' WITH HEADER = TRUE;\"")

if __name__ == "__main__":
    main()
