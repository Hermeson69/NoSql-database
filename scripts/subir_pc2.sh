#!/usr/bin/env bash
# ==============================================================================
# scripts/subir_pc2.sh
# Automacao para inicializar a Maquina 2 (Secundaria) no LINUX
# ==============================================================================

SEED_IP="${1:-26.96.137.160}"
MY_IP="${2:-26.42.12.45}"

echo "=========================================================="
echo "   INICIALIZANDO CLUSTER CASSANDRA - MAQUINA 2 (LINUX)    "
echo "=========================================================="
echo "IP do Seed (PC 1): $SEED_IP"
echo "IP desta Maquina (PC 2): $MY_IP"

# 1. Limpar container anterior se existir
echo -e "\n[1/3] Limpando container antigo..."
docker rm -f cassandra-node2 2>/dev/null || true
echo "Container limpo com sucesso."

# 2. Subir container da Maquina 2
echo -e "\n[2/3] Subindo container cassandra-node2..."
docker run -d --name cassandra-node2 \
  -p 7000:7000 -p 9042:9042 \
  -e CASSANDRA_CLUSTER_NAME="NoSQLCluster" \
  -e CASSANDRA_DC="dc1" \
  -e CASSANDRA_RACK="rack1" \
  -e CASSANDRA_ENDPOINT_SNITCH="GossipingPropertyFileSnitch" \
  -e CASSANDRA_BROADCAST_ADDRESS="$MY_IP" \
  -e CASSANDRA_BROADCAST_RPC_ADDRESS="$MY_IP" \
  -e CASSANDRA_SEEDS="$SEED_IP" \
  -e MAX_HEAP_SIZE="768M" -e HEAP_NEWSIZE="192M" \
  cassandra:5.0

# 3. Aguardar o Cassandra se juntar ao cluster
echo -e "\n[3/3] Aguardando o Cassandra se juntar ao anel (~35-50s)..."
tentativas=0
pronto=false

while [ "$pronto" = false ] && [ $tentativas -lt 30 ]; do
    sleep 4
    tentativas=$((tentativas+1))
    if docker exec cassandra-node2 cqlsh localhost 9042 -e "SELECT cluster_name FROM system.local" 2>&1 | grep -q "NoSQLCluster"; then
        pronto=true
    else
        echo "  -> Aguardando sincronizacao do anel... ($tentativas)"
    fi
done

if [ "$pronto" = false ]; then
    echo -e "\n[ERRO] O Cassandra demorou demais para inicializar. Verifique os logs com 'docker logs cassandra-node2'."
    exit 1
fi

echo -e "\n=========================================================="
echo "                  STATUS ATUAL DO CLUSTER                 "
echo "=========================================================="
docker exec -it cassandra-node2 nodetool status

echo -e "\nTUDO PRONTO NO PC 2! Para consultar a tabela replicada:"
echo "docker exec -it cassandra-node2 cqlsh localhost 9042 -e 'USE telemetria; SELECT * FROM sensores_iot LIMIT 5;'"

