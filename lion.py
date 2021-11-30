import requests
from json import loads
from json.decoder import JSONDecodeError
from time import sleep
from rich.live import Live
from requests.exceptions import ConnectionError
from prometheus_client.parser import text_string_to_metric_families
from template import *
from os import path
from sys import exit
from config import config

REST = config['REST']
RPC = config['RPC']
NODE_EXPORTER = config['NODE_EXPORTER_URL']
TELEGRAM_TOKEN = config['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = config['TELEGRAM_CHAT_ID']
VALIDATOR_ADDR = config['VALIDATOR_ADDR']
DELEGATOR = config['DELEGATOR']
VALOPER = config['VALOPER']
ETH_ADDRESS = config['ETH_ADDRESS']
MONIKER = ""
PUB_KEY = ""
UPTIME = []
COMMITS = [0, 0, 0]  # missed, signed, propossed

# if REST == '' or not RPC == '':
#     print('Unconfigured. Check config.py Exit')
#     exit(1)


def tg_message(data):
    tgURL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"\
        f"/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text="
    return handle_request(tgURL, data, True)


def handle_request(api: str, pattern: str, raw=False) -> dict:
    """return json from the rpc/rest/NODE_EXPORTER"""
    try:
        if not raw:
            response = loads(requests.get(f"{api}/{pattern}").text)
            return response['result']
        response = requests.get(f"{api}/{pattern}").text
        return response if response is not None else "[ERR]"
    except Exception as err:
        return f"[ERR] {err}"


def peggy_module_state():
    pattern = f'/peggy/v1/module_state'
    result = handle_request(REST, pattern, True)
    try:
        return loads(result)['state']
    except JSONDecodeError:
        return '[ERR]'


def get_moniker(pub_key):
    global MONIKER
    if not MONIKER:
        validators = handle_request(REST, "staking/validators")
        for val in validators:
            if val['consensus_pubkey']['value'] == pub_key:
                MONIKER = val['description']['moniker']
                return val['operator_address']
        return MONIKER
    return MONIKER


def handle_system_info(data):
    if '[ERR]' not in data:
        used_mem = f"{data['node_memory_MemTotal_bytes']/ (2**30) - data['node_memory_MemAvailable_bytes'] / (2**30):.3f}"
        load_avg = f"{data['node_load1'], data['node_load5'], data['node_load15']}"
        memory = f"{data['node_memory_MemTotal_bytes']/ (2**30) :.3f} GB"
        disk_usage = f"{data['node_filesystem_avail_bytes'] / (2**30):.1f} / {data['node_filesystem_size_bytes']/ (2**30):.1f} GB"
    else:
        used_mem = load_avg = memory = disk_usage = f'[red]node_exporter err'
    return used_mem, load_avg, memory, disk_usage


def system_info():
    metrics = handle_request(NODE_EXPORTER, "/metrics", True)
    if '[ERR]' in metrics:
        return metrics
    data = {}
    for family in text_string_to_metric_families(metrics):
        for sample in family.samples:
            if sample[0] == 'node_filesystem_avail_bytes' and sample[1]['mountpoint'] == '/':
                data[f"{sample[0]}"] = sample[2]
            if sample[0] == 'node_filesystem_size_bytes' and sample[1]['mountpoint'] == '/':
                data[f"{sample[0]}"] = sample[2]
            elif sample[0] == 'node_uname_info':
                # get node name ex: vmi718121.contaboserver.net
                data[sample[0]] = sample[1]['nodename']
            else:
                if sample[0] not in data:
                    data[f"{sample[0]}"] = sample[2]

    return handle_system_info(data)


def get_inflation():
    result = handle_request(REST, 'cosmos/mint/v1beta1/inflation', True)
    return loads(result)['inflation']


def peers():
    net_info = handle_request(RPC, "net_info")
    peers = int(net_info['n_peers'])
    return f"[red]{peers}" if peers < 5 else f"[green]{peers}"


def get_comission():
    """get current reward/comission"""
    url = f"cosmos/distribution/v1beta1/validators/"\
          f"{VALOPER}/commission"
    try:
        data = loads(handle_request(REST, url, True))
        return data['commission']['commission'][0]['amount']
    except IndexError:
        # means there are no comission at the moment, return 0
        return [0, 0]


def get_rewards():
    """get current reward/comission"""
    url = f"cosmos/distribution/v1beta1/delegators/"\
          f"{DELEGATOR}/"\
          f"rewards/{VALOPER}"
    try:
        data = handle_request(REST, url, True)
        data = loads(data)
        comission = round(float(get_comission()))
        rewards = round(float(data['rewards'][0]['amount']))
        return rewards, comission
    except IndexError:
        # means there are no rewards at the moment, return 0
        return (0, 0)


def count_uptime(response, block):
    """Check wether val signed, propossed or missed block"""
    # block, response = get_uptime()
    # count = response.count(VALIDATOR_ADDR)
    # COMMITS = (0, 0, 0) # missed, signed, propossed
    # status = '[magenta]✗ ', '[green]✓ ', '[cyan]:rocket: '
    status = '[magenta]✗ ', '[green]✓ ', '[cyan]✓ '
    count = response.count(VALIDATOR_ADDR)
    if f"{status[count]}{block}" not in UPTIME:
        UPTIME.append(f"{status[count]}{block}")
        COMMITS[count] += 1
        COMMITS[1] += 1 if count == 2 else 0
        if count < 1:
            tg_message(f'Missed {block}')


def get_uptime(last_block=None):
    last_block = int(last_block)
    if len(UPTIME) > 0:
        last_tracked_block = int(UPTIME[-1].split()[-1])
        while last_tracked_block < last_block:
            last_tracked_block += 1
            # UPTIME[-1] = '[green]✓ 123456'
            # int(UPTIME[-1].split()[-1]) -> 123456
            response = handle_request(
                REST, f"blocks/{last_tracked_block}", True)
            count_uptime(response, last_tracked_block)
    else:
        response = handle_request(REST, "blocks/latest", True)
        block = loads(response)['block']['header']['height']
        return count_uptime(response, block)


def find_pub(VALIDATOR_ADDR, block=None, page=1):
    global PUB_KEY
    if not PUB_KEY:
        # last block
        block = handle_request(RPC, "status")[
            "sync_info"]["latest_block_height"]
        # 100 active validators per page
        response = handle_request(RPC,
                                  f"validators?&height={block}"
                                  f"&per_page=100&page={page}")
        for val in response['validators']:
            if VALIDATOR_ADDR == val['address']:
                PUB_KEY = val['pub_key']['value']
                return PUB_KEY

        if page == 2:
            return f"Can't find pub_key! Val can be jailed!"

        if int(response['total']) > 100 and page == 1:
            return find_pub(VALIDATOR_ADDR, block, 2)

        return f"Can't find pub_key! Val can be jailed!"

    return PUB_KEY


def get_eth_addr(orchestrator_addresses):
    global ETH_ADDRESS
    if ETH_ADDRESS == "":
        for item in orchestrator_addresses:
            if item['sender'] == DELEGATOR:
                ETH_ADDRESS = item['eth_address']
                return ETH_ADDRESS
    return ETH_ADDRESS


def get_vp(VALIDATOR_ADDR, block=None, page=1):
    # last block
    block = handle_request(RPC, "status")["sync_info"]["latest_block_height"]
    response = handle_request(RPC,
                              f"validators?&height={block}"
                              f"&per_page=100&page={page}")
    for val in response['validators']:
        if VALIDATOR_ADDR == val['address']:
            return f"[green]{val['voting_power']}"

    if int(response['total']) > 100 and page == 1:
        return get_vp(VALIDATOR_ADDR, block, 2)

    if page == 2:
        return f"[bold red][blink]0 Check VAL!"

    return f"[bold red][blink]0 Check VAL!"


def main():
    data = {}
    status = handle_request(RPC, "/status", True)
    status = loads(status)['result']
    unconfirmed_txs = handle_request(RPC, "/unconfirmed_txs")
    pub_key = find_pub(VALIDATOR_ADDR)
    moniker = get_moniker(pub_key)
    rewards = get_rewards()
    total_vals = handle_request(RPC, "validators")['total']
    used_mem, load_avg, memory, disk_usage = system_info()
    power = get_vp(VALIDATOR_ADDR)

    inflation = float(get_inflation()) * 100

    get_uptime(status['sync_info']['latest_block_height'])
    total_uptime = len(UPTIME)

    data = {
        "layout_info": {
            f"Moniker": moniker,
            f"NETWORK": f"{status['node_info']['network']}",
            # f"Node ID": f"{status['node_info']['id']}",
            f"val_address": VALIDATOR_ADDR,
            f"val_pub_key": pub_key,
            f"valoper": VALOPER,
            f"Delegator": DELEGATOR,
            f"Server IP": f"{status['node_info']['listen_addr']}",
            f"Telegram": f"[green]Enabled" if TELEGRAM_TOKEN else f"[red]Disabled",
            # f"Twilio Call": f"[green]TODO",
            f"Load avg": load_avg,
            f"Disk": disk_usage,
            f"Memory": f"{used_mem} / {memory}",
            f"Jailed": f"[green]False" if 'green' in f"{power}" else f"[bold red][blink]True",
            f"Inflation": f"{inflation:.2f}%",
            f"Mempool": f"{float(unconfirmed_txs['total_bytes'])/1000:.2f}Kb",
            f"unconfirmed_txs": unconfirmed_txs['n_txs'],
            f"Proposed": f"{COMMITS[2]}/{total_uptime}",
            f"Signed": f"{COMMITS[1]}/{total_uptime}",
            f"Missed": f"{COMMITS[0]}/{total_uptime}"
        },

        "footer_layout": {
            f"VP": power,
            f"Catching_up": f"[green]{status['sync_info']['catching_up']}",
            f"Active_vals": f"{total_vals}",
            f"height": f"{status['sync_info']['latest_block_height']} ",
            f"Peers": f"{peers()}",
            f"rewards": f"{sum(rewards)/10**6:.3f} UMEE"
        }}
    return data


def peggy_main():
    data = {}
    peggy_state = peggy_module_state()
    if '[ERR]' in peggy_state or 'Not Implemented' in peggy_state:
        data['[red]api error'] = '[red]Could not parse data'
        return data
    data['Ethereum address'] = get_eth_addr(
        peggy_state['orchestrator_addresses'])
    data['bridge_eth_addr'] = peggy_state['params']['bridge_ethereum_address']
    data['unbatched_transfers'] = len(peggy_state['unbatched_transfers'])
    data['last_obsrvd_eth_height'] = peggy_state['last_observed_ethereum_height']
    data['last_out_batch_id'] = peggy_state['last_outgoing_batch_id']
    data['last_out_pool_id'] = peggy_state['last_outgoing_pool_id']
    data['last_obsrvd_nonce'] = peggy_state['last_observed_nonce']
    data['bridge_chain_id'] = peggy_state['params']['bridge_chain_id']
    return data


if __name__ == '__main__':
    if config['REST'] == '' and config['RPC'] == '':
        print('Unconfigured. Check config.py Exit')
        exit(1)
    with Live(layout, screen=True, redirect_stderr=False, refresh_per_second=1) as live:
        try:
            while True:
                data = main()
                peggy_data = peggy_main()
                layout["INFO"].update(layout_info(data))
                layout["colored_blocks"].update(layout_body(UPTIME))
                layout["HEIGHT"].update(footer(
                    f"[b][red]{data['footer_layout']['height']}", 'HEIGHT'))
                layout["Voting_Power"].update(footer(
                    f"[b][red]{data['footer_layout']['VP']}", 'Voting Power'))
                layout["Catching_up"].update(footer(
                    f"[b][red]{data['footer_layout']['Catching_up']}", 'Catching_up'))
                layout["Peers"].update(footer(
                    f"[b][red]{data['footer_layout']['Peers']}", 'Peers'))
                layout["Active_vals"].update(
                    footer(f"[b][red]{data['footer_layout']['Active_vals']}", 'Active Validators'))
                layout["Rewards"].update(
                    footer(f"[b][magenta]{data['footer_layout']['rewards']}", 'Rewards'))
                layout['peggy'].update(layout_peggy(peggy_data))
                sleep(4)
        except KeyboardInterrupt:
            pass
