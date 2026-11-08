#!/usr/bin/env python3
"""
==============================================================================
scripts/cluster.py
Gerenciador Unificado do Cluster Apache Cassandra (Windows & Linux)
Executa todas as etapas com IDENTIFICAÇÃO AUTOMÁTICA DE IP:
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
import socket
import subprocess
import platform
import argparse
from pathlib import Path

# Habilita cores ANSI no terminal do Windows se suportado
if platform.system() == "Windows":
    os.system("")

# Estilos e Cores ANSI
C_CYAN, C_GREEN, C_YELLOW, C_RED, C_GRAY, C_RESET = (
    "\033[36m", "\033[32m", "\033[33m", "\033[31m", "\033[90m", "\033[0m"
)
BG_GREEN, BG_YELLOW, C_BOLD = "\033[42;30m", "\033[43;30m", "\033[1m"

ROOT = Path(__file__).resolve().parent.parent
DADOS_DIR, INIT_DIR = ROOT / "dados", ROOT / "init"
DEFAULT_SEED_IP = "26.96.137.160"


def banner(txt: str):
    print(f"\n{C_CYAN}{'='*58}\n   {C_BOLD}{txt}{C_RESET}\n{C_CYAN}{'='*58}{C_RESET}")


def run_cmd(cmd: str, capture: bool = True):
    res = subprocess.run(cmd, shell=True, text=True, capture_output=capture)
    return res.returncode, res.stdout or "", res.stderr or ""


def check_docker() -> bool:
    if run_cmd("docker info")[0] != 0:
        print(f"\n{C_RED}[ERRO CRÍTICO] O Docker Desktop não está em execução! Inicie-o antes de continuar.{C_RESET}\n")
        return False
    return True


def detectar_ips():
    ips = []
    try:
        ips.extend([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith(("127.", "169.254."))])
    except Exception:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
    except Exception:
        pass
    if platform.system() == "Linux":
        code, out, _ = run_cmd("hostname -I")
        if code == 0:
            ips.extend(out.split())

    # Ignora redes virtuais WSL/Docker (172.17.x até 172.21.x) e duplicatas
    validos, seen = [], set()
    for ip in ips:
        if ip in seen or any(ip.startswith(f"172.{v}.") for v in range(17, 22)) or ip.startswith(("127.", "169.254.")):
            continue
        seen.add(ip)
        tag = "Radmin VPN" if ip.startswith("26.") else "Hamachi" if ip.startswith("25.") else "Wi-Fi / Ethernet"
        validos.append((ip, tag))

    return sorted(validos, key=lambda x: 0 if x[0].startswith(("26.", "25.")) else 1)


def obter_ip(fornecido=None, label="desta máquina"):
    if fornecido:
        return fornecido
    ips = detectar_ips()
    if not ips:
        return input(f"Informe o IP {label} [{DEFAULT_SEED_IP}]: ").strip() or DEFAULT_SEED_IP
    if len(ips) == 1:
        print(f"{C_GREEN}[] IP detectado: {C_BOLD}{ips[0][0]}{C_RESET} ({ips[0][1]})")
        return ips[0][0]

    print(f"\n{C_CYAN}[] IPs detectados {label}:{C_RESET}")
    for i, (ip, tag) in enumerate(ips, 1):
        rec = f" {C_GREEN}[Recomendado]{C_RESET}" if i == 1 else ""
        print(f"  [{i}] {ip} ({tag}){rec}")
    opt = input(f"{C_YELLOW}Escolha o IP [Enter = {ips[0][0]}]: {C_RESET}").strip()
    return ips[int(opt) - 1][0] if opt.isdigit() and 1 <= int(opt) <= len(ips) else opt if "." in opt else ips[0][0]


def container_ativo():
    names = run_cmd('docker ps --format "{{.Names}}"')[1].split()
    return next((c for c in ["cassandra-node1", "cassandra-node2"] if c in names), None)


def wait_cassandra(container: str, timeout: int = 3600) -> bool:
    print(f"\n{C_YELLOW}[] Aguardando JVM do Cassandra inicializar (~35-60s)...{C_RESET}")
    start = time.time()
    try:
        while time.time() - start < timeout:
            time.sleep(4)
            if run_cmd(f'docker exec {container} cqlsh localhost 9042 -e "SELECT cluster_name FROM system.local"')[0] == 0:
                print(f"{C_GREEN}[[OK]] Cassandra ONLINE e pronto ({int(time.time() - start)}s)!{C_RESET}")
                return True
            print(f"{C_GRAY}  -> Verificando porta 9042...{C_RESET}")
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[!] Espera cancelada pelo usuário.{C_RESET}")
    return False


def carregar_banco(container: str = "cassandra-node1"):
    banner("CARREGANDO O BANCO DE DADOS (ESQUEMAS E 50K REGISTROS)")
    for idx, (arq, desc) in enumerate([("01_schema.cql", "Esquema NoSQL"), ("02_seed.cql", "Registros Iniciais")], 1):
        cql_path = INIT_DIR / arq
        if not cql_path.exists():
            continue
        print(f"{C_YELLOW}[{idx}/3] Aplicando {arq} ({desc})...{C_RESET}")
        res = subprocess.run(
            f"docker exec -i {container} cqlsh localhost 9042",
            input=cql_path.read_text(encoding="utf-8"),
            text=True,
            shell=True,
            capture_output=True
        )
        print(f"{C_GREEN}[[OK]] {desc} aplicado com sucesso!{C_RESET}" if res.returncode == 0 else f"{C_RED}[ERRO] Falha no CQL: {res.stderr or res.stdout}{C_RESET}")

    csv_file = DADOS_DIR / "dados_sensores.csv"
    if not csv_file.exists():
        print(f"{C_YELLOW}[!] Gerando 50.000 registros de telemetria...{C_RESET}")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "gerar_dados_massa.py")], check=True)

    print(f"{C_YELLOW}[3/3] Importando 50.000 registros via cqlsh COPY...{C_RESET}")
    t0 = time.time()
    copy_cmd = "COPY telemetria.sensores_iot (sensor_id, data_leitura, timestamp, temperatura, umidade, tensao_bateria, status) FROM '/dados/dados_sensores.csv' WITH HEADER = TRUE;"
    code, _, err = run_cmd(f'docker exec -i {container} cqlsh localhost 9042 -e "{copy_cmd}"')
    print(f"{C_GREEN}[[OK]] 50.000 registros importados em {round(time.time() - t0, 2)}s!{C_RESET}" if code == 0 else f"{C_YELLOW}[AVISO] COPY: {err}{C_RESET}")


def verificar_conexao(container: str = None, silent: bool = False):
    container = container or container_ativo()
    if not container:
        if not silent:
            print(f"{C_RED}[ERRO] Nenhum container Cassandra em execução nesta máquina.{C_RESET}")
        return False, 0

    code, out, _ = run_cmd(f"docker exec {container} nodetool status")
    if code != 0:
        return False, 0

    lines = out.strip().splitlines()
    nos_un = [l for l in lines if l.startswith("UN ")]

    if not silent:
        banner(f"STATUS DO CLUSTER ({container})")
        for l in lines:
            color = C_GREEN if l.startswith("UN ") else C_YELLOW if any(l.startswith(p) for p in ["DN ", "UJ ", "UL "]) else ""
            print(f"  {color}{l}{C_RESET}")

        print(f"\n{C_CYAN}{'-'*58}{C_RESET}")
        if len(nos_un) >= 2:
            print(f"{BG_GREEN} [OK] SUCESSO TOTAL! AS 2 MÁQUINAS ESTÃO 100% CONECTADAS! {C_RESET}")
            print(f"{C_GREEN} -> Máquinas ativas no anel: {len(nos_un)} | Replicação RF=2 ativa!{C_RESET}")
        elif len(nos_un) == 1:
            print(f"{BG_YELLOW} [AGUARDANDO] Apenas 1 máquina ativa no anel por enquanto. {C_RESET}")
        print(f"{C_CYAN}{'-'*58}{C_RESET}")

    return (len(nos_un) >= 2), len(nos_un)


def start_node(name: str, my_ip: str, seed_ip: str, mount: bool = False) -> bool:
    run_cmd(f"docker rm -f {name}")
    v = f'-v "{DADOS_DIR.as_posix()}:/dados"' if mount else ""
    # Se nao for o proprio seed, instrui o Cassandra a substituir qualquer sessao antiga com o mesmo IP
    jvm_replace = f'-e JVM_OPTS="-Dcassandra.replace_address_first_boot={my_ip}"' if my_ip != seed_ip else ""
    cmd = (
        f'docker run -d --name {name} -p 7000:7000 -p 9042:9042 '
        f'-e CASSANDRA_CLUSTER_NAME="NoSQLCluster" -e CASSANDRA_DC="dc1" -e CASSANDRA_RACK="rack1" '
        f'-e CASSANDRA_ENDPOINT_SNITCH="GossipingPropertyFileSnitch" -e CASSANDRA_BROADCAST_ADDRESS="{my_ip}" '
        f'-e CASSANDRA_BROADCAST_RPC_ADDRESS="{my_ip}" -e CASSANDRA_SEEDS="{seed_ip}" {jvm_replace} '
        f'-e MAX_HEAP_SIZE="768M" -e HEAP_NEWSIZE="192M" {v} cassandra:5.0'
    )
    return run_cmd(cmd)[0] == 0


def subir_pc1(my_ip=None, wait_pc2: bool = True):
    if not check_docker():
        return
    my_ip = obter_ip(my_ip, "da Máquina 1 (Seed)")
    banner(f"MÁQUINA 1 (SEED) - IP: {my_ip}")
    if not start_node("cassandra-node1", my_ip, my_ip, mount=True) or not wait_cassandra("cassandra-node1"):
        return
    carregar_banco("cassandra-node1")

    if wait_pc2:
        print(f"\n{C_YELLOW}[] Aguardando o PC 2 se juntar ao anel (Ctrl+C para pular)...{C_RESET}")
        start = time.time()
        try:
            while time.time() - start < 90:
                time.sleep(4)
                ok, count = verificar_conexao("cassandra-node1", silent=True)
                if ok:
                    break
                print(f"{C_GRAY}  -> Monitorando anel... Nós UN ativos: {count}{C_RESET}")
        except KeyboardInterrupt:
            pass
    verificar_conexao("cassandra-node1")
    print(f"\n{C_YELLOW}Consulta de Teste:{C_RESET}\ndocker exec -it cassandra-node1 cqlsh localhost 9042 -e \"USE telemetria; SELECT * FROM sensores_iot LIMIT 5;\"\n")


def subir_pc2(seed_ip=None, my_ip=None):
    if not check_docker():
        return
    my_ip = obter_ip(my_ip, "desta Máquina 2")
    seed_ip = seed_ip or input(f"Informe o IP do Seed (PC 1) [{DEFAULT_SEED_IP}]: ").strip() or DEFAULT_SEED_IP
    banner(f"MÁQUINA 2 - IP: {my_ip} (SEED: {seed_ip})")
    if start_node("cassandra-node2", my_ip, seed_ip) and wait_cassandra("cassandra-node2"):
        verificar_conexao("cassandra-node2")
        print(f"\n{C_YELLOW}Consulta de Teste no PC 2:{C_RESET}\ndocker exec -it cassandra-node2 cqlsh localhost 9042 -e \"USE telemetria; SELECT * FROM sensores_iot LIMIT 5;\"\n")


def subir_local():
    if not check_docker():
        return
    banner("CLUSTER LOCAL (2 NÓS VIA DOCKER COMPOSE)")
    if run_cmd("docker compose up -d")[0] == 0 and wait_cassandra("cassandra-node1"):
        carregar_banco("cassandra-node1")
        verificar_conexao("cassandra-node1")


def limpar():
    print(f"{C_YELLOW}Removendo containers...{C_RESET}")
    run_cmd("docker rm -f cassandra-node1 cassandra-node2; docker compose down -v")
    print(f"{C_GREEN}[[OK]] Limpeza concluída com sucesso!{C_RESET}")


def menu():
    acoes = {
        "1": lambda: subir_pc1(),
        "2": lambda: subir_pc2(),
        "3": lambda: subir_local(),
        "4": lambda: carregar_banco(container_ativo() or "cassandra-node1"),
        "5": lambda: verificar_conexao(),
        "6": limpar,
    }
    nomes = [
        "Subir Máquina 1 (Seed - Banco + 50k dados + Esperar PC 2)",
        "Subir Máquina 2 (Secundária - Conectar ao PC 1)",
        "Subir Cluster Local (2 nós na mesma máquina via Compose)",
        "Apenas Carregar o Banco (Schemas + 50.000 dados)",
        "Apenas Verificar Conexão (Status do Cluster)",
        "Parar e Limpar Containers do Cluster",
    ]
    while True:
        banner("GERENCIADOR UNIFICADO DO CASSANDRA")
        for i, nome in enumerate(nomes, 1):
            print(f"  {C_BOLD}[{i}]{C_RESET} {nome}")
        print(f"  {C_BOLD}[0]{C_RESET} Sair")
        try:
            op = input(f"\n{C_CYAN}Escolha uma opção (0-6): {C_RESET}").strip()
            if op == "0":
                break
            if op in acoes:
                acoes[op]()
                if op != "5":
                    break
        except (KeyboardInterrupt, EOFError):
            break


def main():
    p = argparse.ArgumentParser(description="Gerenciador Unificado do Cassandra (Windows & Linux)")
    p.add_argument("--pc1", action="store_true", help="Sobe a Máquina 1 (Seed Node)")
    p.add_argument("--pc2", action="store_true", help="Sobe a Máquina 2 (Secundária)")
    p.add_argument("--local", action="store_true", help="Sobe cluster local com 2 nós")
    p.add_argument("--carregar", action="store_true", help="Carrega schemas e 50k dados")
    p.add_argument("--status", action="store_true", help="Verifica a conexão do cluster")
    p.add_argument("--limpar", action="store_true", help="Remove containers")
    p.add_argument("--my-ip", default=None, help="IP desta máquina")
    p.add_argument("--seed-ip", default=None, help="IP do Seed Node")
    args = p.parse_args()

    if not any([args.pc1, args.pc2, args.local, args.carregar, args.status, args.limpar]):
        menu()
    elif args.limpar:
        limpar()
    elif args.status:
        verificar_conexao()
    elif args.carregar:
        carregar_banco(container_ativo() or "cassandra-node1")
    elif args.local:
        subir_local()
    elif args.pc1:
        subir_pc1(my_ip=args.my_ip)
    elif args.pc2:
        subir_pc2(seed_ip=args.seed_ip, my_ip=args.my_ip)


if __name__ == "__main__":
    main()
