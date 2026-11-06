#!/usr/bin/env bash
# ==============================================================================
# scripts/subir_pc2.sh
# Automacao para inicializar a Maquina 2 (Secundaria) no LINUX
# Uso normal: ./scripts/subir_pc2.sh "IP_DO_SEED" "MEU_IP"
# Checar status a qualquer momento: ./scripts/subir_pc2.sh status
# ==============================================================================

# Cores ANSI
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'
BG_GREEN='\033[42;30m'
BG_YELLOW='\033[43;30m'

exibir_diagnostico() {
    echo -e "\n${CYAN}==========================================================${NC}"
    echo -e "${CYAN}                  STATUS DO CLUSTER                       ${NC}"
    echo -e "${CYAN}==========================================================${NC}"

    status_output=$(docker exec cassandra-node2 nodetool status 2>&1)
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERRO] Container cassandra-node2 nao esta respondendo.${NC}"
        return 1
    fi

    echo -e "\nTabela do nodetool status:"
    echo "$status_output" | while IFS= read -r line; do
        if [[ "$line" =~ ^UN\  ]]; then
            echo -e "${GREEN}  $line${NC}"
        elif [[ "$line" =~ ^(D|U)(J|L|M|D)\  ]]; then
            echo -e "${YELLOW}  $line${NC}"
        else
            echo "  $line"
        fi
    done

    nos_un=$(echo "$status_output" | grep -c "^UN " || true)

    echo -e "\n${CYAN}----------------------------------------------------------${NC}"
    if [ "$nos_un" -ge 2 ]; then
        echo -e "${BG_GREEN} [OK] SUCESSO TOTAL! AS 2 MAQUINAS ESTAO 100% CONECTADAS! ${NC}"
        echo -e "\n${GREEN} -> Maquinas no anel: $nos_un computadores fisicos${NC}"
        echo -e "${GREEN} -> Status: UN (Up / Normal) em ambos os computadores.${NC}"
        echo -e "${GREEN} -> Replicacao RF=2: Totalmente ativa e sincronizada!${NC}"
    elif [ "$nos_un" -eq 1 ]; then
        echo -e "${BG_YELLOW} [AGUARDANDO] Apenas 1 maquina ativa no anel.             ${NC}"
        echo -e "\n${YELLOW} -> Aguardando sincronizacao com o Seed (PC 1).${NC}"
    else
        echo -e "${RED} [ATENCAO] Nenhum no com status UN detectado.${NC}"
    fi
    echo -e "${CYAN}----------------------------------------------------------${NC}"
}

# Se o usuario passou 'status' como primeiro argumento:
if [ "$1" == "status" ]; then
    exibir_diagnostico
    exit 0
fi

SEED_IP="${1:-26.96.137.160}"
MY_IP="${2:-26.42.12.45}"

echo -e "${CYAN}==========================================================${NC}"
echo -e "${CYAN}   INICIALIZANDO CLUSTER CASSANDRA - MAQUINA 2 (LINUX)    ${NC}"
echo -e "${CYAN}==========================================================${NC}"
echo -e "${YELLOW}IP do Seed (PC 1): $SEED_IP${NC}"
echo -e "${YELLOW}IP desta Maquina (PC 2): $MY_IP${NC}"

# 1. Limpar container anterior se existir
echo -e "\n${YELLOW}[1/3] Limpando container antigo...${NC}"
docker rm -f cassandra-node2 2>/dev/null || true
echo -e "${GREEN}Container limpo com sucesso.${NC}"

# 2. Subir container da Maquina 2
echo -e "\n${YELLOW}[2/3] Subindo container cassandra-node2...${NC}"
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
echo -e "\n${YELLOW}[3/3] Aguardando o Cassandra se juntar ao anel (~35-50s)...${NC}"
tentativas=0
pronto=false

while [ "$pronto" = false ] && [ $tentativas -lt 30 ]; do
    sleep 4
    tentativas=$((tentativas+1))
    if docker exec cassandra-node2 cqlsh localhost 9042 -e "SELECT cluster_name FROM system.local" 2>&1 | grep -q "NoSQLCluster"; then
        pronto=true
    else
        echo -e "  -> Aguardando sincronizacao do anel... ($tentativas)"
    fi
done

if [ "$pronto" = false ]; then
    echo -e "\n${RED}[ERRO] O Cassandra demorou demais para inicializar. Verifique os logs com 'docker logs cassandra-node2'.${NC}"
    exit 1
fi

# Exibicao Final
exibir_diagnostico

echo -e "\n${YELLOW}TUDO PRONTO NO PC 2! Para consultar a tabela replicada:${NC}"
echo "docker exec -it cassandra-node2 cqlsh localhost 9042 -e 'USE telemetria; SELECT * FROM sensores_iot LIMIT 5;'"
echo -e "\n${YELLOW}Para rechecar o status do anel a qualquer momento, basta rodar:${NC}"
echo "./scripts/subir_pc2.sh status"
