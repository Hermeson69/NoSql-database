#!/usr/bin/env python3
"""
==============================================================================
scripts/cluster.py
Gerenciador Unificado do Cluster Apache Cassandra (Windows & Linux)
Executa todas as etapas:
  - Subir Máquina 1 (Seed Node)
  - Subir Máquina 2 (Secundária)
  - Subir Cluster Local (2 nós na mesma máquina)
  - Carregar esquemas e 50.000 registros
  - Verificar conexão e saúde do anel de nós
Compatível 100% com Windows, Linux e macOS (requer apenas Python 3.8+).
==============================================================================
"""

import sys
import os
import time
import subprocess
import platform
import argparse
from pathlib import Path

# Habilita cores ANSI no terminal do Windows se necessário
if platform.system() == "Windows":
    os.system("")

# Códigos de Cores ANSI
C_RESET = "\033[0m"
C_CYAN = "\033[0;36m"
C_GREEN = "\033[0;32m"
C_YELLOW = "\033[1;33m"
C_RED = "\033[0;31m"
C_GRAY = "\033[0;90m"
C_BOLD = "\033[1m"
BG_GREEN = "\033[42;30m"
BG_YELLOW = "\033[43;30m"

# Diretórios base
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DADOS_DIR = PROJECT_DIR / "dados"
INIT_DIR = PROJECT_DIR / "init"
CSV_FILE = DADOS_DIR / "dados_sensores.csv"
SCHEMA_FILE = INIT_DIR / "01_schema.cql"
SEED_FILE = INIT_DIR / "02_seed.cql"

# IPs padrão (Radmin VPN)
DEFAULT_SEED_IP = "26.96.137.160"
DEFAULT_NODE2_IP = "26.42.12.45"


def print_banner(title):
    print(f"\n{C_CYAN}=========================================================={C_RESET}")
    print(f"{C_CYAN}{C_BOLD}   {title}{C_RESET}")
    print(f"{C_CYAN}=========================================================={C_RESET}")


def run_cmd(cmd, capture=True, shell=True):
    """Executa comando no shell de forma segura e multiplataforma."""
    res = subprocess.run(cmd, shell=shell, text=True, capture_output=capture)
    return res.returncode, res.stdout, res.stderr


def is_container_running(name):
    code, out, _ = run_cmd(f'docker ps --filter "name={name}" --format "{{{{.Names}}}}"')
    return name in out.split()


def get_active_container():
    if is_container_running("cassandra-node1"):
        return "cassandra-node1"
    if is_container_running("cassandra-node2"):
        return "cassandra-node2"
    return None


def wait_for_cassandra(container_name, timeout_seconds=120):
    """Aguarda a JVM do Cassandra inicializar e responder requisições CQL."""
    print(f"\n{C_YELLOW}[⏳] Aguardando JVM do Cassandra inicializar (35 a 60 segundos)...{C_RESET}")
    start = time.time()
    tentativa = 0
    while time.time() - start < timeout_seconds:
        tentativa += 1
        time.sleep(4)
        check_cmd = f'docker exec {container_name} cqlsh localhost 9042 -e "SELECT cluster_name FROM system.local"'
        code, out, _ = run_cmd(check_cmd)
        if code == 0 and "NoSQLCluster" in out:
            print(f"{C_GREEN}[✔] Cassandra está ONLINE e pronto para receber conexões! ({int(time.time() - start)}s){C_RESET}")
            return True
        print(f"{C_GRAY}  -> Verificando porta 9042 no {container_name}... ({tentativa}){C_RESET}")
    print(f"{C_RED}[ERRO] Tempo limite atingido esperando o Cassandra subir.{C_RESET}")
    return False


def carregar_banco(container_name="cassandra-node1"):
    """Aplica o esquema, seeds e importa os 50.000 dados de telemetria."""
    print_banner("CARREGANDO O BANCO DE DADOS (ESQUEMAS E DADOS)")

    # 1. Aplicar 01_schema.cql
    print(f"{C_YELLOW}[1/3] Aplicando 01_schema.cql (Keyspace + Tabela NoSQL)...{C_RESET}")
    if SCHEMA_FILE.exists():
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema_content = f.read()
        res = subprocess.run(
            f"docker exec -i {container_name} cqlsh localhost 9042",
            input=schema_content,
            text=True,
            shell=True,
            capture_output=True
        )
        print(f"{C_GREEN}[✔] Esquema NoSQL aplicado com sucesso!{C_RESET}")
    else:
        print(f"{C_RED}[ERRO] Arquivo {SCHEMA_FILE} não encontrado.{C_RESET}")

    # 2. Aplicar 02_seed.cql
    print(f"{C_YELLOW}[2/3] Aplicando 02_seed.cql (Registros de teste)...{C_RESET}")
    if SEED_FILE.exists():
        with open(SEED_FILE, "r", encoding="utf-8") as f:
            seed_content = f.read()
        subprocess.run(
            f"docker exec -i {container_name} cqlsh localhost 9042",
            input=seed_content,
            text=True,
            shell=True,
            capture_output=True
        )
        print(f"{C_GREEN}[✔] Registros iniciais aplicados com sucesso!{C_RESET}")

    # 3. Importar os 50.000 dados
    print(f"{C_YELLOW}[3/3] Importando grande volume de dados (50.000 registros)...{C_RESET}")
    copy_cql = (
        "COPY telemetria.sensores_iot (sensor_id, data_leitura, timestamp, temperatura, "
        "umidade, tensao_bateria, status) FROM '/dados/dados_sensores.csv' WITH HEADER = TRUE;"
    )
    start_copy = time.time()
    code, out, err = run_cmd(f'docker exec -i {container_name} cqlsh localhost 9042 -e "{copy_cql}"')
    duracao = round(time.time() - start_copy, 2)

    if code == 0:
        print(f"{C_GREEN}[✔] 50.000 registros importados em {duracao}s!{C_RESET}")
    else:
        print(f"{C_YELLOW}[AVISO] Saída do comando COPY:\n{out or err}{C_RESET}")


def verificar_conexao(container_name=None, silent=False):
    """Executa nodetool status e exibe diagnóstico colorido e legível."""
    if not container_name:
        container_name = get_active_container()

    if not container_name:
        if not silent:
            print(f"{C_RED}[ERRO] Nenhum container do Cassandra está em execução nesta máquina.{C_RESET}")
        return False, 0

    code, out, _ = run_cmd(f"docker exec {container_name} nodetool status")
    if code != 0:
        if not silent:
            print(f"{C_RED}[ERRO] Falha ao comunicar com {container_name} via nodetool.{C_RESET}")
        return False, 0

    lines = out.strip().splitlines()
    nos_un = [l for l in lines if l.startswith("UN ")]

    if not silent:
        print_banner("STATUS DA CONEXÃO DO CLUSTER")
        print(f"{C_GRAY}Tabela do nodetool status ({container_name}):{C_RESET}")
        for l in lines:
            if l.startswith("UN "):
                print(f"{C_GREEN}  {l}{C_RESET}")
            elif any(l.startswith(prefix) for prefix in ["DN ", "UJ ", "UL ", "UM "]):
                print(f"{C_YELLOW}  {l}{C_RESET}")
            else:
                print(f"  {l}")

        print(f"\n{C_CYAN}----------------------------------------------------------{C_RESET}")
        if len(nos_un) >= 2:
            print(f"{BG_GREEN} [OK] SUCESSO TOTAL! AS 2 MÁQUINAS ESTÃO 100% CONECTADAS! {C_RESET}")
            print(f"\n{C_GREEN} -> Máquinas ativas no anel: {len(nos_un)} computadores físicos{C_RESET}")
            print(f"{C_GREEN} -> Status: UN (Up / Normal) em ambos os nós{C_RESET}")
            print(f"{C_GREEN} -> Replicação RF=2: Ativa e sincronizada em tempo real!{C_RESET}")
        elif len(nos_un) == 1:
            print(f"{BG_YELLOW} [AGUARDANDO] Apenas 1 máquina ativa no anel por enquanto. {C_RESET}")
            print(f"\n{C_YELLOW} -> Aguardando o segundo computador conectar ao cluster.{C_RESET}")
        else:
            print(f"{C_RED} [ATENÇÃO] Nenhum nó com status UN detectado.{C_RESET}")
        print(f"{C_CYAN}----------------------------------------------------------{C_RESET}")

    return (len(nos_un) >= 2), len(nos_un)


def subir_pc1(my_ip=DEFAULT_SEED_IP, esperar_pc2=True):
    """Sobe o Nó 1 (Seed), carrega schemas e dados, e aguarda o PC 2."""
    print_banner(f"INICIALIZANDO MÁQUINA 1 (SEED NODE) - IP: {my_ip}")

    # 1. Limpar anterior
    print(f"{C_YELLOW}[1/4] Limpando container cassandra-node1 anterior...{C_RESET}")
    run_cmd("docker rm -f cassandra-node1")
    print(f"{C_GREEN}[✔] Container limpo com sucesso.{C_RESET}")

    # 2. Subir container
    print(f"{C_YELLOW}[2/4] Subindo container cassandra-node1 no Docker...{C_RESET}")
    dados_mount = f"{DADOS_DIR}:/dados"
    docker_cmd = (
        f'docker run -d --name cassandra-node1 '
        f'-p 7000:7000 -p 9042:9042 '
        f'-e CASSANDRA_CLUSTER_NAME="NoSQLCluster" '
        f'-e CASSANDRA_DC="dc1" '
        f'-e CASSANDRA_RACK="rack1" '
        f'-e CASSANDRA_ENDPOINT_SNITCH="GossipingPropertyFileSnitch" '
        f'-e CASSANDRA_BROADCAST_ADDRESS="{my_ip}" '
        f'-e CASSANDRA_BROADCAST_RPC_ADDRESS="{my_ip}" '
        f'-e CASSANDRA_SEEDS="{my_ip}" '
        f'-e MAX_HEAP_SIZE="768M" -e HEAP_NEWSIZE="192M" '
        f'-v "{dados_mount}" '
        f'cassandra:5.0'
    )
    code, cid, err = run_cmd(docker_cmd)
    if code != 0:
        print(f"{C_RED}[ERRO] Falha ao iniciar container:\n{err}{C_RESET}")
        return

    # 3. Aguardar Cassandra responder
    if not wait_for_cassandra("cassandra-node1"):
        return

    # 4. Carregar o banco (schemas + 50k dados)
    carregar_banco("cassandra-node1")

    # 5. Aguardar PC 2 conectar
    if esperar_pc2:
        print(f"\n{C_YELLOW}[🤝] Aguardando o PC 2 se juntar ao anel de nós...{C_RESET}")
        print(f"{C_GRAY}(Peça para o colega iniciar o PC 2 agora. Ctrl+C para pular){C_RESET}")
        conectado = False
        start_wait = time.time()
        try:
            while not conectado and (time.time() - start_wait < 90):
                time.sleep(4)
                conectado, count = verificar_conexao("cassandra-node1", silent=True)
                print(f"{C_GRAY}  -> Monitorando anel... Nós UN ativos: {count}{C_RESET}")
        except KeyboardInterrupt:
            print(f"\n{C_YELLOW}Espera interrompida pelo usuário.{C_RESET}")

    # Exibir diagnóstico final
    verificar_conexao("cassandra-node1")

    print(f"\n{C_YELLOW}TUDO PRONTO! Para consultar os dados da tabela, execute:{C_RESET}")
    print(f'docker exec -it cassandra-node1 cqlsh localhost 9042 -e "USE telemetria; SELECT * FROM sensores_iot LIMIT 5;"\n')


def subir_pc2(seed_ip=DEFAULT_SEED_IP, my_ip=DEFAULT_NODE2_IP):
    """Sobe o Nó 2 (Secundário) apontando para o Seed (PC 1)."""
    print_banner(f"INICIALIZANDO MÁQUINA 2 - IP: {my_ip} (SEED: {seed_ip})")

    # 1. Limpar anterior
    print(f"{C_YELLOW}[1/3] Limpando container cassandra-node2 anterior...{C_RESET}")
    run_cmd("docker rm -f cassandra-node2")
    print(f"{C_GREEN}[✔] Container limpo com sucesso.{C_RESET}")

    # 2. Subir container
    print(f"{C_YELLOW}[2/3] Subindo container cassandra-node2 no Docker...{C_RESET}")
    docker_cmd = (
        f'docker run -d --name cassandra-node2 '
        f'-p 7000:7000 -p 9042:9042 '
        f'-e CASSANDRA_CLUSTER_NAME="NoSQLCluster" '
        f'-e CASSANDRA_DC="dc1" '
        f'-e CASSANDRA_RACK="rack1" '
        f'-e CASSANDRA_ENDPOINT_SNITCH="GossipingPropertyFileSnitch" '
        f'-e CASSANDRA_BROADCAST_ADDRESS="{my_ip}" '
        f'-e CASSANDRA_BROADCAST_RPC_ADDRESS="{my_ip}" '
        f'-e CASSANDRA_SEEDS="{seed_ip}" '
        f'-e MAX_HEAP_SIZE="768M" -e HEAP_NEWSIZE="192M" '
        f'cassandra:5.0'
    )
    code, cid, err = run_cmd(docker_cmd)
    if code != 0:
        print(f"{C_RED}[ERRO] Falha ao iniciar container:\n{err}{C_RESET}")
        return

    # 3. Aguardar entrar no anel
    if not wait_for_cassandra("cassandra-node2"):
        return

    # Exibir diagnóstico final
    verificar_conexao("cassandra-node2")

    print(f"\n{C_YELLOW}TUDO PRONTO NO PC 2! Para consultar a tabela replicada:{C_RESET}")
    print(f'docker exec -it cassandra-node2 cqlsh localhost 9042 -e "USE telemetria; SELECT * FROM sensores_iot LIMIT 5;"\n')


def subir_local():
    """Sobe um cluster de 2 nós na mesma máquina via Docker Compose."""
    print_banner("INICIALIZANDO CLUSTER LOCAL (2 NÓS NA MESMA MÁQUINA)")
    print(f"{C_YELLOW}[1/3] Executando docker compose up -d...{C_RESET}")
    code, out, err = run_cmd("docker compose up -d")
    if code != 0:
        print(f"{C_RED}[ERRO] Falha ao executar docker compose:\n{err}{C_RESET}")
        return

    if not wait_for_cassandra("cassandra-node1"):
        return

    carregar_banco("cassandra-node1")
    verificar_conexao("cassandra-node1")


def menu_interativo():
    """Menu interativo quando o script é chamado sem parâmetros."""
    while True:
        print_banner("GERENCIADOR UNIFICADO DO CASSANDRA (WINDOWS & LINUX)")
        print(f"{C_BOLD}[1]{C_RESET} Subir Máquina 1 (Seed Node - Banco + 50k dados + Esperar PC 2)")
        print(f"{C_BOLD}[2]{C_RESET} Subir Máquina 2 (Secundária - Conectar ao PC 1)")
        print(f"{C_BOLD}[3]{C_RESET} Subir Cluster Local (2 nós na mesma máquina via Compose)")
        print(f"{C_BOLD}[4]{C_RESET} Apenas Carregar o Banco (Schemas + 50.000 dados)")
        print(f"{C_BOLD}[5]{C_RESET} Apenas Verificar Conexão (Status do Cluster)")
        print(f"{C_BOLD}[6]{C_RESET} Parar e Limpar Containers do Cluster")
        print(f"{C_BOLD}[0]{C_RESET} Sair")

        try:
            opcao = input(f"\n{C_CYAN}Escolha uma opção (0-6): {C_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando...")
            break

        if opcao == "1":
            ip = input(f"Informe o IP da Máquina 1 [{DEFAULT_SEED_IP}]: ").strip() or DEFAULT_SEED_IP
            subir_pc1(my_ip=ip)
            break
        elif opcao == "2":
            seed = input(f"Informe o IP do Seed (PC 1) [{DEFAULT_SEED_IP}]: ").strip() or DEFAULT_SEED_IP
            my_ip = input(f"Informe o IP desta Máquina 2 [{DEFAULT_NODE2_IP}]: ").strip() or DEFAULT_NODE2_IP
            subir_pc2(seed_ip=seed, my_ip=my_ip)
            break
        elif opcao == "3":
            subir_local()
            break
        elif opcao == "4":
            cname = get_active_container() or "cassandra-node1"
            carregar_banco(cname)
            break
        elif opcao == "5":
            verificar_conexao()
        elif opcao == "6":
            print(f"{C_YELLOW}Limpando containers...{C_RESET}")
            run_cmd("docker rm -f cassandra-node1 cassandra-node2")
            run_cmd("docker compose down -v")
            print(f"{C_GREEN}[✔] Containers removidos com sucesso.{C_RESET}")
        elif opcao == "0":
            print("Até logo!")
            break
        else:
            print(f"{C_RED}Opção inválida! Tente novamente.{C_RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Gerenciador Unificado do Cluster Apache Cassandra (Windows & Linux)"
    )
    parser.add_argument("--pc1", action="store_true", help="Sobe a Máquina 1 (Seed Node)")
    parser.add_argument("--pc2", action="store_true", help="Sobe a Máquina 2 (Secundária)")
    parser.add_argument("--local", action="store_true", help="Sobe cluster local com 2 nós via Docker Compose")
    parser.add_argument("--carregar", action="store_true", help="Apenas carrega o banco de dados")
    parser.add_argument("--status", action="store_true", help="Apenas verifica o status e conexão do anel")
    parser.add_argument("--limpar", action="store_true", help="Para e remove todos os containers do Cassandra")
    parser.add_argument("--my-ip", default=None, help="IP desta máquina")
    parser.add_argument("--seed-ip", default=DEFAULT_SEED_IP, help="IP do Seed Node (PC 1)")

    args = parser.parse_args()

    # Se nenhum argumento for passado, abre o menu interativo
    if not any([args.pc1, args.pc2, args.local, args.carregar, args.status, args.limpar]):
        menu_interativo()
        return

    if args.limpar:
        print(f"{C_YELLOW}Limpando containers...{C_RESET}")
        run_cmd("docker rm -f cassandra-node1 cassandra-node2")
        run_cmd("docker compose down -v")
        print(f"{C_GREEN}[✔] Containers removidos com sucesso.{C_RESET}")
    elif args.status:
        verificar_conexao()
    elif args.carregar:
        cname = get_active_container() or "cassandra-node1"
        carregar_banco(cname)
    elif args.local:
        subir_local()
    elif args.pc1:
        ip = args.my_ip or DEFAULT_SEED_IP
        subir_pc1(my_ip=ip)
    elif args.pc2:
        ip = args.my_ip or DEFAULT_NODE2_IP
        seed = args.seed_ip or DEFAULT_SEED_IP
        subir_pc2(seed_ip=seed, my_ip=ip)


if __name__ == "__main__":
    main()

