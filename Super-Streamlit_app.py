import os
import re
import shutil
import subprocess
import requests
import json
import time
import base64
import asyncio
import streamlit as st

FILE_PATH = os.environ.get('FILE_PATH', './.tmp')
XCONF_PATH = os.path.join(FILE_PATH, 'xconf')
INTERVAL_SECONDS = int(os.environ.get("TIME", 100))
OPENSERVER = os.environ.get('OPENSERVER', 'true').lower() == 'true'
KEEPALIVE = os.environ.get('KEEPALIVE', 'true').lower() == 'true'
CFIP = os.environ.get('CFIP', 'ip.sb')
PORT = int(os.environ.get('SERVER_PORT') or os.environ.get('PORT') or 3000)
V_PORT = int(os.environ.get('V_PORT', 8080))
CFPORT = int(os.environ.get('CFPORT', 443))
SUB_URL = os.environ.get('SUB_URL', 'https://myjyup.shiguangda.nom.za/upload-a4aa34be-4373-4fdb-bff7-0a9c23405dac')

VLPATH = os.environ.get('VLPATH', 'startvl')
XHPPATH = os.environ.get('XHPPATH', '')

UUID = os.environ.get('UUID', '2b77e1df-a473-4b2e-a738-47f541b222b2')
NEZHA_VERSION = os.environ.get('NEZHA_VERSION', 'V1')
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', 'nazha.tcguangda.eu.org')
NEZHA_KEY = os.environ.get('NEZHA_KEY', 'ilovehesufeng520')
NEZHA_PORT = os.environ.get('NEZHA_PORT', '443')
SUB_NAME = os.environ.get('SUB_NAME', 'streamlit')
MY_DOMAIN = os.environ.get('MY_DOMAIN', '')

ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', 'str.tcgd001.cf')
ARGO_AUTH = os.environ.get('ARGO_AUTH', 'eyJhIjoiNjFmNmJhODg2ODkxNmJmZmM1ZDljNzM2NzdiYmIwMDYiLCJ0IjoiNjQ0OWRjOWQtZWVkZC00ZDY5LWIyYmItY2ExNTQ4MzRkYzlhIiwicyI6Ik1UTTNPVFF4TXpJdE5tVTNOUzAwTldJekxXSTFNR1l0TkRrd016bGxNR1ExTm1ZMyJ9')

def createFolder(folderPath):
    if not os.path.exists(folderPath):
        os.makedirs(folderPath)
        print(f"{folderPath} is created")
    else:
        print(f"{folderPath} already exists")

pathsToDelete = ['config.yml', 'xconf', 'tunnel.json', 'tunnel.yml', 'boot.log', 'log.txt']
def cleanupOldFiles():
    for file in pathsToDelete:
        filePath = os.path.join(FILE_PATH, file)

        try:
            if os.path.exists(filePath):
                if os.path.isdir(filePath):
                    shutil.rmtree(filePath)
                    # print(f"{filePath} deleted")
                else:
                    os.remove(filePath)
                    # print(f"{filePath} deleted")
            else:
                # print(f"Skip Delete {filePath}")
                pass
        except Exception as err:
            # print(f"Failed to delete {filePath}: {err}")
            pass

# set page
def display_homepage():
    st.markdown("""
    <html>
    <head>
        <title>my home page</title>
    </head>
    <body>
        <h1>Welcome to my space!</h1>
        <p>Very happy to make friends with you all!</p>
    </body>
    </html>
    """, unsafe_allow_html=True)

async def exec_promise(command, options=None, wait_for_completion=False):
    if options is None:
        options = {}

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **options
        )

        if wait_for_completion:
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error = Exception(f"Command failed with exit code {proc.returncode}")
                error.code = proc.returncode
                error.stderr = stderr.decode().strip()
                raise error

            return stdout.decode().strip()
        else:
            # print(f"'{command}' is running")
            return proc

    except Exception as e:
        if not hasattr(e, 'code'):
            e.code = -1
        if not hasattr(e, 'stderr'):
            e.stderr = str(e)
        raise

async def detect_process(processname):
    methods = [
        {'cmd': f'pidof "{processname}"', 'name': 'pidof'},
        {'cmd': f'pgrep -x "{processname}"', 'name': 'pgrep'},
        {'cmd': f'ps -eo pid,comm | awk -v name="{processname}" \'$2 == name {{print $1}}\'', 'name': 'ps+awk'}
    ]

    for method in methods:
        try:
            stdout = await exec_promise(method['cmd'], wait_for_completion=True)
            if stdout:
                return re.sub(r'\n+', ' ', stdout)
        except Exception as e:
            if hasattr(e, 'code') and e.code not in (127, 1):
                print(f'[detect_process] {method["name"]} error:', str(e))
            continue

    return ''

async def kill_process(process_name):
    print(f"Attempting to kill process: {process_name}")

    try:
        pids = await detect_process(process_name)

        if not pids:
            print(f"Process '{process_name}' not found.")
            return

        result = await exec_promise(f"kill -9 {pids}")

        msg = f"Killed process (PIDs: {pids})"
        print(msg)
        return {'success': True, 'message': msg}

    except Exception as e:
        msg = f"Kill failed: {str(e)}"
        print(f"Error: {msg}")
        return {'success': False, 'message': msg}

def generate_config():
    vlpath = '/' + str(VLPATH)
    xhppath = '/' + str(XHPPATH)
    inbound = {
        "log": {
            "access": "/dev/null",
            "error": "/dev/null",
            "loglevel": "none"
        },
        "dns": {
            "servers": [
                "https+local://8.8.8.8/dns-query"
            ]
        }
    };
    with open(os.path.join(XCONF_PATH, 'inbound.json'), 'w', encoding='utf-8') as inbound_file:
        json.dump(inbound, inbound_file, ensure_ascii=False, indent=2)

    if VLPATH:
        inbound_v = {
            "inbounds": [
                {
                    "port": V_PORT,
                    "listen": "::",
                    "protocol": "vless",
                    "settings": {
                        "clients": [
                            {
                                "id": UUID,
                                "level": 0
                            }
                        ],
                        "decryption": "none"
                    },
                    "streamSettings": {
                        "network": "ws",
                        "security": "none",
                        "wsSettings": {
                            "path": vlpath
                        }
                    },
                    "sniffing": {
                        "enabled": True,
                        "destOverride": [
                            "http",
                            "tls",
                            "quic"
                        ],
                        "metadataOnly": False
                    }
                }
            ]
        };
        with open(os.path.join(XCONF_PATH, 'inbound_v.json'), 'w', encoding='utf-8') as inbound_v_file:
            json.dump(inbound_v, inbound_v_file, ensure_ascii=False, indent=2)
    elif XHPPATH:
        inbound_v = {
            "inbounds": [
                {
                    "port": V_PORT,
                    "listen": "::",
                    "protocol": "vless",
                    "settings": {
                        "clients": [
                            {
                                "id": UUID
                            }
                        ],
                        "decryption": "none"
                    },
                    "streamSettings": {
                        "network": "xhttp",
                        "security": "none",
                        "xhttpSettings": {
                            "mode": "packet-up",
                            "path": xhppath
                        }
                    },
                    "sniffing": {
                        "enabled": True,
                        "destOverride": [
                            "http",
                            "tls",
                            "quic"
                        ],
                        "metadataOnly": False
                    }
                }
            ]
        };
        with open(os.path.join(XCONF_PATH, 'inbound_v.json'), 'w', encoding='utf-8') as inbound_v_file:
            json.dump(inbound_v, inbound_v_file, ensure_ascii=False, indent=2)

    outbound = {
        "outbounds": [
            {
                "tag": "direct",
                "protocol": "freedom"
            },
            {
                "tag": "block",
                "protocol": "blackhole"
            }
        ]
    };
    with open(os.path.join(XCONF_PATH, 'outbound.json'), 'w', encoding='utf-8') as outbound_file:
        json.dump(outbound, outbound_file, ensure_ascii=False, indent=2)

def get_files_for_architecture():
    arch = os.uname().machine
    if arch in ['arm', 'arm64', 'aarch64']:
        base_files = [
            {'file_name': 'web', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/xray_arm'},
        ]
        if OPENSERVER:
            base_files.append({'file_name': 'bot', 'file_url': 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64'})
        if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
            if NEZHA_VERSION == 'V0':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/kahunama/myfile/releases/download/main/nezha-agent_arm'})
            elif NEZHA_VERSION == 'V1':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/nezha-agentv1_arm'})
    else:
        base_files = [
            {'file_name': 'web', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/xray'},
        ]
        if OPENSERVER:
            base_files.append({'file_name': 'bot', 'file_url': 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64'})
        if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
            if NEZHA_VERSION == 'V0':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/kahunama/myfile/releases/download/main/nezha-agent'})
            elif NEZHA_VERSION == 'V1':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/nezha-agentv1'})
    return base_files

def authorize_files(file_paths):
    new_permissions = 0o775

    for relative_file_path in file_paths:
        absolute_file_path = os.path.join(FILE_PATH, relative_file_path)
        try:
            os.chmod(absolute_file_path, new_permissions)
            print(f"Empowerment success for {absolute_file_path}: {oct(new_permissions)}")
        except Exception as e:
            print(f"Empowerment failed for {absolute_file_path}: {e}")

def download_function(file_name, file_url):
    file_path = os.path.join(FILE_PATH, file_name)
    already_existed = False
    if os.path.exists(file_path):
        print(f"{file_name} already exists, skip download")
        already_existed = True
        return True, already_existed
    try:
        with requests.get(file_url, stream=True) as response, open(file_path, 'wb') as file:
            shutil.copyfileobj(response.raw, file)
        return True, already_existed
    except Exception as e:
        print(f"Download {file_name} failed: {e}")
        return False, already_existed

def download_files():
    files_to_download = get_files_for_architecture()

    if not files_to_download:
        print("Can't find a file for the current architecture")
        return

    downloaded_files = []

    for file_info in files_to_download:
        file_name = file_info['file_name']
        file_url = file_info['file_url']
        download_result, already_existed = download_function(file_name, file_url)
        if download_result:
            if not already_existed:
                print(f"Downloaded {file_name} successfully")
            downloaded_files.append(file_name)

    files_to_authorize = downloaded_files
    authorize_files(files_to_authorize)

def argo_config():
    if not ARGO_AUTH or not ARGO_DOMAIN:
        print("ARGO_DOMAIN or ARGO_AUTH is empty, use quick Tunnels")
        return

    if 'TunnelSecret' in ARGO_AUTH:
        with open(os.path.join(FILE_PATH, 'tunnel.json'), 'w') as file:
            file.write(ARGO_AUTH)
        tunnel_yaml = f"""tunnel: {ARGO_AUTH.split('"')[11]}
credentials-file: {os.path.join(FILE_PATH, 'tunnel.json')}
protocol: http2

ingress:
  - hostname: {ARGO_DOMAIN}
    service: http://localhost:{V_PORT}
    originRequest:
      noTLSVerify: true
  - service: http_status:404
"""
        with open(os.path.join(FILE_PATH, 'tunnel.yml'), 'w') as file:
            file.write(tunnel_yaml)
    else:
        print("Use token connect to tunnel")

def get_cloud_flare_args():
    args = ""
    if re.match(r"^[A-Z0-9a-z=]{120,250}$", ARGO_AUTH):
        args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 run --token {ARGO_AUTH}"
    elif "TunnelSecret" in ARGO_AUTH:
        args = f"tunnel --edge-ip-version auto --config {FILE_PATH}/tunnel.yml run"
    else:
        args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{V_PORT}"
    return args

def nezconfig():
    NEZHA_TLS = ''
    valid_ports = ['443', '8443', '2096', '2087', '2083', '2053']
    if NEZHA_VERSION == 'V0':
        if NEZHA_PORT in valid_ports:
            NEZHA_TLS = '--tls'
        return NEZHA_TLS
    elif NEZHA_VERSION == 'V1':
        if NEZHA_PORT in valid_ports:
            NEZHA_TLS = 'true'
        else:
            NEZHA_TLS = 'false'
        try:
            nez_yml = f"""client_secret: {NEZHA_KEY}
debug: false
disable_auto_update: true
disable_command_execute: false
disable_force_update: true
disable_nat: false
disable_send_query: false
gpu: false
insecure_tls: false
ip_report_period: 1800
report_delay: 4
server: {NEZHA_SERVER}:{NEZHA_PORT}
skip_connection_count: false
skip_procs_count: false
temperature: false
tls: {NEZHA_TLS}
use_gitee_to_upgrade: false
use_ipv6_country_code: false
uuid: {UUID}
"""
            with open(os.path.join(FILE_PATH, 'config.yml'), 'w') as file:
                file.write(nez_yml)
            print("config.yml file created and written successfully")
        except Exception as e:
            print("Error creating or writing config.yml file: {e}")
    else:
        return None

async def runbot(args):
    bot_path = os.path.join(FILE_PATH, 'bot')
    if os.path.exists(bot_path):
        cmd = f'nohup {FILE_PATH}/bot {args} >/dev/null 2>&1 &'
        try:
            proc_bot = await exec_promise(cmd)
        except Exception as e:
            print(f"Error launching bot: {getattr(e, 'stderr', str(e))} (Code: {getattr(e, 'code', -1)})")
    else:
        print("bot file not found, skip running")

async def runweb():
    web_path = os.path.join(FILE_PATH, 'web')
    if os.path.exists(web_path):
        cmd = f'nohup {FILE_PATH}/web run -confdir {FILE_PATH}/xconf >/dev/null 2>&1 &'
        try:
            proc_web = await exec_promise(cmd)
        except Exception as e:
            print(f"Error launching web: {getattr(e, 'stderr', str(e))} (Code: {getattr(e, 'code', -1)})")
    else:
        print("web file not found, skip running")

async def runnpm(NEZHA_TLS):
    npm_path = os.path.join(FILE_PATH, 'npm')
    if os.path.exists(npm_path):
        if NEZHA_VERSION == 'V0':
            cmd = f'nohup {FILE_PATH}/npm -s {NEZHA_SERVER}:{NEZHA_PORT} -p {NEZHA_KEY} {NEZHA_TLS} --report-delay=4 --skip-conn --skip-procs --disable-auto-update >/dev/null 2>&1 &'
            try:
                proc_npm = await exec_promise(cmd)
            except Exception as e:
                print(f"Error launching {FILE_PATH}/npm: {getattr(e, 'stderr', str(e))} (Code: {getattr(e, 'code', -1)})")
        elif NEZHA_VERSION == 'V1':
            cmd = f'nohup {FILE_PATH}/npm -c {FILE_PATH}/config.yml >/dev/null 2>&1 &'
            try:
                proc_npm = await exec_promise(cmd)
            except Exception as e:
                print(f"Error launching npm: {getattr(e, 'stderr', str(e))} (Code: {getattr(e, 'code', -1)})")
    else:
        print("npm file not found, skip running")

async def runapp(args, NEZHA_TLS):
    if OPENSERVER:
        bot_pids = await detect_process("bot")
        if bot_pids:
            # print(f"bot is already running. PIDs: {bot_pids}")
            pass
        else:
            await runbot(args)
        await asyncio.sleep(5)
        print(f"bot is running")
    else:
        print("bot is not allowed, skip running")

    web_pids = await detect_process("web")
    if web_pids:
        # print(f"web is already running. PIDs: {web_pids}")
        pass
    else:
        await runweb()
    await asyncio.sleep(1)
    print(f"web is running")

    if NEZHA_VERSION and NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
        npm_pids = await detect_process("npm")
        if npm_pids:
            # print(f"npm is already running. PIDs: {npm_pids}")
            pass
        else:
            await runnpm(NEZHA_TLS)
        await asyncio.sleep(1)
        print(f"npm is running")
    else:
        print("npm variable is empty, skip running")

async def keep_alive(args, NEZHA_TLS):
    if OPENSERVER:
        bot_pids = await detect_process("bot")
        if bot_pids:
            # print(f"bot is already running. PIDs: {bot_pids}")
            pass
        else:
            print(f"bot runs again !")
            await runbot(args)

    await asyncio.sleep(5)

    web_pids = await detect_process("web")
    if web_pids:
        # print(f"web is already running. PIDs: {web_pids}")
        pass
    else:
        print(f"web runs again !")
        await runweb()

    await asyncio.sleep(5)

    if NEZHA_VERSION and NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
        npm_pids = await detect_process("npm")
        if npm_pids:
            # print(f"npm is already running. PIDs: {npm_pids}")
            pass
        else:
            print(f"npm runs again !")
            await runnpm(NEZHA_TLS)

def getArgoDomainFromLog():
    bootfile_path = os.path.join(FILE_PATH, 'boot.log')
    if os.path.exists(bootfile_path) and os.path.getsize(bootfile_path) > 0:
        with open(bootfile_path, 'r', encoding='utf-8') as f:
            file_content = f.read()

        regex = re.compile(r'info.*https:\/\/(.*trycloudflare\.com)')
        matches = regex.findall(file_content)
        last_match = matches[-1] if matches else None
        return last_match
    else:
        return None

def buildurl(argo_domain, ISP):
    Node_DATA = None
    if VLPATH:
        Node_DATA = f"vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=%2F{VLPATH}%3Fed%3D2560#{ISP}-{SUB_NAME}"
    elif XHPPATH:
        Node_DATA = f"vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&type=xhttp&host={argo_domain}&path=%2F{XHPPATH}%3Fed%3D2560&mode=packet-up#{ISP}-{SUB_NAME}"
    return Node_DATA

async def extract_domains(args, ISP):
    current_argo_domain = ''
    if OPENSERVER:
        if ARGO_AUTH and ARGO_DOMAIN:
            current_argo_domain = ARGO_DOMAIN
        else:
            try:
                await asyncio.sleep(3)
                current_argo_domain = getArgoDomainFromLog()
                if not current_argo_domain:
                    try:
                        print('boot.log not found, re-running bot')
                        bootfile_path = os.path.join(FILE_PATH, 'boot.log')
                        if os.path.exists(bootfile_path):
                            os.unlink(bootfile_path)
                            await asyncio.sleep(1)
                        await kill_process("bot")
                        await asyncio.sleep(1)
                        await runbot(args)
                        print(f"bot is running")
                        await asyncio.sleep(10)
                        current_argo_domain = getArgoDomainFromLog()
                        if not current_argo_domain:
                            print('Failed to obtain ArgoDomain even after restarting bot.')
                    except Exception as error:
                        print('Error in bot process management:', error)
                        return
            except Exception as error:
                # print(f"Failed to get current_argo_domain: {error}")
                pass

    if MY_DOMAIN:
        current_argo_domain = MY_DOMAIN
        # print('Overriding ArgoDomain with MY_DOMAIN:', current_argo_domain)

    argo_domain = current_argo_domain
    if not argo_domain:
        print('No domain could be determined. Cannot construct UPLOAD_DATA')
        UPLOAD_DATA = None
        return

    UPLOAD_DATA = buildurl(argo_domain, ISP)
    # print(UPLOAD_DATA)
    return argo_domain, UPLOAD_DATA

def get_cloudflare_meta():
    try:
        with requests.Session() as session:
            response = session.get('https://speed.cloudflare.com/meta')
            data = response.json()
            return data
    except Exception as error:
        print(f"Failed to get Cloudflare meta: {error}")
        return None

def get_isp_and_ip():
    data = get_cloudflare_meta()
    if data:
        # SERVERIP = data['clientIp']
        # print(SERVERIP)
        fields1 = data['country']
        fields2 = data['asOrganization']
        ISP = f"{fields1}-{fields2}".replace(' ', '_')
        # print(ISP)
        return ISP

def generate_links(UPLOAD_DATA):
    if UPLOAD_DATA:
        file_path = os.path.join(FILE_PATH, 'log.txt')
        with open(file_path, 'w') as f:
            encoded_data = base64.b64encode(UPLOAD_DATA.encode('utf-8')).decode('utf-8')
            f.write(encoded_data)
            # print(encoded_data)

async def cleanfiles():
    await asyncio.sleep(60)
    os.system('cls' if os.name == 'nt' else 'clear')
    print('App is running')

async def upload_subscription(sub_name, upload_data, sub_url):
    def _sync_upload():
        data = json.dumps({"URL_NAME": sub_name, "URL": upload_data})
        headers = {'Content-Type': 'application/json', 'Content-Length': str(len(data))}
        try:
            response = requests.post(sub_url, data=data, headers=headers, verify=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Upload failed: {str(e)}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_upload)

async def subupload(initial_argo_domain, initial_upload_data, args, ISP):
    previous_argo_domain = initial_argo_domain
    argo_domain = initial_argo_domain
    UPLOAD_DATA = initial_upload_data

    while True:
        if argo_domain != previous_argo_domain:
            response = await upload_subscription(SUB_NAME, UPLOAD_DATA, SUB_URL)
            generate_links(UPLOAD_DATA)
            previous_argo_domain = argo_domain
        else:
            # print(f"domain name has not been updated, no need to upload")
            pass

        await asyncio.sleep(INTERVAL_SECONDS)

        extracted = await extract_domains(args, ISP)
        if len(extracted) == 2:
            argo_domain, UPLOAD_DATA = extracted

async def keep_alive_run(args, NEZHA_TLS):
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        await keep_alive(args, NEZHA_TLS)

# main
async def main():
    await kill_process("web")
    await asyncio.sleep(1)
    await kill_process("bot")
    await asyncio.sleep(1)
    await kill_process("npm")
    await asyncio.sleep(1)
    display_homepage()
    createFolder(FILE_PATH)
    cleanupOldFiles()
    createFolder(XCONF_PATH)

    generate_config()
    download_files()
    ISP = get_isp_and_ip()
    if OPENSERVER:
        argo_config()
        args = get_cloud_flare_args()
    else:
        args = None
    if NEZHA_VERSION and NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
        NEZHA_TLS = nezconfig()
    else:
        NEZHA_TLS = None

    await runapp(args, NEZHA_TLS)
    argo_domain, UPLOAD_DATA = await extract_domains(args, ISP)
    generate_links(UPLOAD_DATA)

    tasks = [
        asyncio.create_task(cleanfiles())
    ]
    if SUB_URL:
        response = await upload_subscription(SUB_NAME, UPLOAD_DATA, SUB_URL)
        if KEEPALIVE and OPENSERVER and not ARGO_AUTH and not ARGO_DOMAIN:
            tasks.append(asyncio.create_task(subupload(argo_domain, UPLOAD_DATA, args, ISP)))
    if KEEPALIVE:
        await keep_alive(args, NEZHA_TLS)
        tasks.append(asyncio.create_task(keep_alive_run(args, NEZHA_TLS)))
    await asyncio.gather(*tasks)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
