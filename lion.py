import requests
from json import loads, dumps
from rich.live import Live
from prometheus_client.parser import text_string_to_metric_families
from template import *
from sys import exit
from config import config
from datetime import datetime
import timeago
from random import shuffle
import asyncio

ETH_RPC2 = 'https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161'
BRIDGE_CHAINS = {"1": "Ethereum Mainnet", "5": "Goerli Test Network"}
BRIDGE_ETHEREUM_ADDR = "0xb564ac229e9d6040a9f1298b7211b9e79ee05a2c"
ETHERSCAN_API_KEY = config['ETHERSCAN_API_KEY']
TELEGRAM_CHAT_ID = config['TELEGRAM_CHAT_ID']
NODE_EXPORTER = config['NODE_EXPORTER_URL']
TELEGRAM_TOKEN = config['TELEGRAM_TOKEN']
VALIDATOR_ADDR = config['VALIDATOR_ADDR']
DELEGATOR = config['DELEGATOR']
VALOPER = config['VALOPER']
VALCONS = config['VALCONS']
ETH_RPC = config['ETH_RPC']
ORCH_ETH_ADDRESS = ""
ORCH_UMEE_ADDR = ''
REST = config['REST']
RPC = config['RPC']
COMMITS = [0, 0, 0]  # missed, signed, propossed
MONIKER = ""
PUB_KEY = ""
UPTIME = []
DECIMALS = 10 ** 6
BRIDGE_CHAIN_ID = ""
ORCHESTRATORS = list()
VALIDATORS = list()
DATA = dict(layout_info={}, footer_layout={})


async def get_proposals():
    try:
        active_proposals = await handle_request(
            REST, f"/gov/proposals?status=voting_period")
        if len(active_proposals) < 1:
            return layout["Active_proposals"].update(footer(f"[b][green] No active proposals!", 'Active proposals'))
        active_proposals = await handle_request(
            REST, f"/gov/proposals?status=voting_period")
        voted_proposals = len(await handle_request(
            REST, f"/gov/proposals?status=voting_period&voter={DELEGATOR}"))

        active_proposals = len(active_proposals)

        if voted_proposals == active_proposals:
            return layout["Active_proposals"].update(footer(f"[b][green]Voted: {voted_proposals} / {active_proposals}", 'Active proposals'))

        if voted_proposals > 0 and voted_proposals < active_proposals:
            return layout["Active_proposals"].update(footer(f"[b][yellow]Voted: {voted_proposals} / {active_proposals}", 'Active proposals'))

        return layout["Active_proposals"].update(footer(f"[b][red]Voted: {voted_proposals} / {active_proposals}", 'Active proposals'))

    except Exception as err:
        return layout["Active_proposals"].update(footer(f"[ERR] voted proposals \n{err}", 'Active proposals'))


async def get_eth_txs():
    ETHERSCAN_URL = f"https://api.etherscan.io/api?module=account&action=txlist&"\
                    f"address={ORCH_ETH_ADDRESS}&startblock=14210004&"\
                    f"endblock=latest&page=1&offset=7&sort=desc&apikey={ETHERSCAN_API_KEY}"
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'}
    dt = datetime.utcnow()
    if not ETHERSCAN_API_KEY:
        result = f'[ERR] Etherscan apikey not specified'
        return layout['etherscan_txs'].update(footer(result, 'Orchestrator ETH txs'))
    if 'KEYS NOT SET' in ORCH_ETH_ADDRESS:
        result = f'[b][red][ERR] Ethereum addr not found'
        return layout['etherscan_txs'].update(footer(result, 'Orchestrator ETH txs'))
    try:
        response = requests.get(ETHERSCAN_URL, headers=headers).json()
        status = ['SUCCESS', 'FAIL']
        result = ""
        for tx in response['result']:

            tx_timestamp = datetime.utcfromtimestamp(int(tx['timeStamp']))
            delta = timeago.format(tx_timestamp, dt)
            tx_hash = f"{tx['hash'][:10]}..{tx['hash'][-10:]}"

            if int(tx['isError']):
                result = f"{result}[red]{status[int(tx['isError'])]: <7}[/] {tx['input'][:10]: <10} [u blue link=https://etherscan.io/tx/{tx['hash']}]{tx_hash}[/] {delta}\n"
            else:
                result = f"{result}[green]{status[int(tx['isError'])]: <7}[/] {tx['input'][:10]: <10} [u blue link=https://etherscan.io/tx/{tx['hash']}]{tx_hash}[/] {delta}\n"

        # return result
        return layout['etherscan_txs'].update(footer(result, 'Orchestrator ETH txs'))
    except Exception as err:
        result = f"[ERR] {err}"
        return layout['etherscan_txs'].update(footer(result, 'Orchestrator ETH txs'))


async def get_orch_txs():
    try:
        if 'KEYS NOT SET' in ORCH_UMEE_ADDR:
            result = f'[b][red][ERR] UMEE orch addr not found'
            return layout['umee_orch_txs'].update(footer(result, 'Orchestrator UMEE txs'))

        url = f"cosmos/tx/v1beta1/txs?events=tx.acc_seq=%27{ORCH_UMEE_ADDR}%27&pagination.limit=7&order_by=ORDER_BY_DESC"
        response = loads(await handle_request(REST, url, True))
        status = ['SUCCESS', 'FAIL']
        dt = datetime.utcnow()
        result = ""
        for tx in response['tx_responses']:
            tx_timestamp = datetime.strptime(tx['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
            delta = timeago.format(tx_timestamp, dt)
            tx_hash = tx['txhash']
            tx_hash_slice = f"{tx_hash[:7]}..{tx_hash[-7:]}"

            module = loads(tx['raw_log'])[0]['events'][0]['attributes'][0]['value']
            try:
                event_nonce = tx['tx']['body']['messages'][0]['event_nonce'] if module else ""
            except KeyError:
                event_nonce = tx['tx']['body']['messages'][0]['nonce'] if module else ""
            module = module.replace('/gravity.v1.Msg', '').replace('Claim', '')
            if module in "gravity.v1.MsgERC20DeployedClaim":
                event_nonce = tx['tx']['body']['messages'][0]['symbol']

            if tx['code'] == 0:
                if event_nonce:
                    module = f"{module}/{event_nonce}"
                    result = f"{result}[green]{status[0]: <7}[/] {module: ^19} [u blue link=https://www.mintscan.io/umee/txs/{tx_hash}]{tx_hash_slice}[/] {delta}\n"
                else:
                    result = f"{result}[green]{status[0]: <7}[/] {module: ^19} [u blue link=https://www.mintscan.io/umee/txs/{tx_hash}]{tx_hash_slice}[/] {delta}\n"

            else:
                result = f"{result}[red]{status[1]: <7}[/] {module: ^19} [u blue link=https://www.mintscan.io/umee/txs/{tx_hash}]{tx_hash_slice}[/] {delta}\n"
        # return result
        return layout['umee_orch_txs'].update(footer(result, 'Orchestrator UMEE txs'))
    except Exception as err:
        result = f"[ERR] parsing get_orch_txs check check REST API!\n{err}"
        return layout['umee_orch_txs'].update(footer(result, 'Orchestrator UMEE txs'))


async def get_delegator_txs():
    try:

        txs = dict()
        sent_txs = f"cosmos/tx/v1beta1/txs?events=tx.acc_seq=%27{DELEGATOR}%27&pagination.limit=7&order_by=ORDER_BY_DESC"
        received_txs = f"cosmos/tx/v1beta1/txs?events=transfer.recipient%3D%27{DELEGATOR}%27&order_by=ORDER_BY_DESC&pagination.limit=7"
        sent_txs = loads(await handle_request(REST, sent_txs, True))
        received_txs = loads(await handle_request(REST, received_txs, True))

        for sent_tx in sent_txs['tx_responses']:
            sent_tx_timestamp = datetime.strptime(sent_tx['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
            txs[sent_tx_timestamp] = sent_tx

        for received_tx in received_txs['tx_responses']:
            received_tx_timestamp = datetime.strptime(received_tx['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
            txs[received_tx_timestamp] = received_tx

        sorted_txs = list(reversed(sorted(txs.items())))
        # iterate over 7 txs
        sorted_txs = dict(sorted_txs[:7])
        dt = datetime.utcnow()
        status = ['SUCCESS', 'FAIL']
        result = ""

        for tx_timestamp, tx in sorted_txs.items():

            delta = timeago.format(tx_timestamp, dt)
            tx_hash = tx['txhash']
            tx_hash_slice = f"{tx_hash[:7]}..{tx_hash[-7:]}"

            message0 = tx['tx']['body']['messages'][0]
            module = message0['@type']

            module = module.split('.')[-1].replace('Msg', '').replace('Delegator', '')

            if module in '/cosmos.bank.v1beta1.MsgSend' and message0['from_address'] != DELEGATOR:
                module = module.replace('Send', 'Receive')
                denom = message0['amount'][0]['denom'][1:]  # uumee --> umee
                amount = round(int(message0['amount'][0]['amount']) / DECIMALS, 2)
                module = f"{module} +{amount} {denom}"

            if module in '/ibc.applications.transfer.v1.MsgTransfer' and message0['sender'] != DELEGATOR:
                module = module.replace('Transfer', 'IBC Receive')
                denom = message0['token']['denom'][1:]  # uumee --> umee
                amount = round(int(message0['token']['amount']) / DECIMALS, 2)
                module = f"{module} +{amount} {denom}"

            if module in '/cosmos.bank.v1beta1.MsgSend' and message0['from_address'] == DELEGATOR:
                denom = message0['amount'][0]['denom'][1:]  # uumee --> umee
                amount = round(int(message0['amount'][0]['amount']) / DECIMALS, 2)
                module = f"{module} -{amount} {denom}"

            if module in '/ibc.applications.transfer.v1.MsgTransfer' and message0['sender'] == DELEGATOR:
                module = module.replace('Transfer', 'IBC Send')
                denom = message0['token']['denom'][1:]  # uumee --> umee
                amount = round(int(message0['token']['amount']) / DECIMALS, 2)
                module = f"{module} -{amount} {denom}"

            if tx['code'] == 0:
                result = f"{result}[green]{status[0]: <7}[/] {module: ^23} [u blue link=https://www.mintscan.io/umee/txs/{tx_hash}]{tx_hash_slice}[/] {delta}\n"
            else:
                result = f"{result}[red]{status[1]: <7}[/] {module: ^23} [u blue link=https://www.mintscan.io/umee/txs/{tx_hash}]{tx_hash_slice}[/] {delta}\n"
        return layout['delegator_txs'].update(footer(result, 'Delegator txs'))
    except Exception as err:
        result = f"[ERR] parsing get_orch_txs check REST API!\n{err}"
        return layout['delegator_txs'].update(footer(result, 'Delegator txs'))


async def tg_allert_message(message):
    try:
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            tgURL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"\
                f"/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text="
            return await handle_request(tgURL, message, True)
    except Exception as err:
        response = f'[ERR] tg_allert_message {err}'
        return response


async def handle_request(api: str, pattern: str, raw=False) -> dict:
    """return json/text from the rpc/rest/NODE_EXPORTER"""
    try:
        if not raw:
            response = loads(requests.get(f"{api}/{pattern}").text)
            return response['result']
        response = requests.get(f"{api}/{pattern}").text
        return response if response is not None else "[ERR]"
    except Exception as err:
        return f"[ERR] {err}"


async def get_pubkey_vp_moniker():
    try:
        global MONIKER, PUB_KEY
        url = f"/cosmos/staking/v1beta1/validators/{VALOPER}"
        response = loads(await handle_request(REST, url, True))
        if not MONIKER:
            MONIKER = response['validator']['description']['moniker']
        if not PUB_KEY:
            PUB_KEY = response['validator']['consensus_pubkey']['key']

        jailed_status = response['validator']['jailed']
        jailed_status = f"[green]{jailed_status}" if 'False' in f"{jailed_status}" else f"[bold red][blink]{jailed_status}"

        bond_status = response['validator']['status']
        bond_status = f"[b][green]{bond_status}"

        if "BOND_STATUS_BONDED" not in bond_status or 'true' in jailed_status:
            await tg_allert_message(f"BOND_STATUS: {response['validator']['status']}\nJailed: {response['validator']['jailed']}")
            bond_status = bond_status.replace('[green]', '[red][blink]')

        power = int(int(response['validator']['tokens']) / DECIMALS)

        DATA["layout_info"]["Moniker"] = MONIKER
        DATA["layout_info"]["Jailed"] = jailed_status
        DATA["layout_info"]["val_pub_key"] = f"{PUB_KEY[:15]}..{PUB_KEY[-10:]}"
        layout["Voting_Power"].update(footer(f"[b][green]{power}", 'Voting Power'))
        layout["BOND_STATUS"].update(footer(bond_status, 'STATUS'))
        return DATA
    except Exception as err:
        result = f"[ERR] {err}"
        layout["Voting_Power"].update(footer(f"[b][red]{result}", 'Voting Power'))
        return (result, ) * 3


async def handle_system_info(data):
    if '[ERR]' not in data:
        available_space = data['node_filesystem_avail_bytes']
        used_mem = f"{data['node_memory_MemTotal_bytes'] / (2**30) - data['node_memory_MemAvailable_bytes'] / (2**30):.1f}"
        load_avg = f"{data['node_load1'], data['node_load5'], data['node_load15']}"
        memory = f"{data['node_memory_MemTotal_bytes'] / (2**30) :.1f} GB"
        disk_usage = f"{available_space / (2**30):.1f} GB / {data['node_filesystem_size_bytes'] / (2**30):.1f} GB"
        boot_time = data['node_boot_time_seconds']
        boot_time = datetime.fromtimestamp(boot_time)
        boot_time = datetime.now() - boot_time
        delta = timeago.format(boot_time, datetime.now())
        uptime = f"{delta[:~3]}"

        if available_space < (2 ** 30) * 10:
            await tg_allert_message(f"WARN low disk space : {available_space / (2 ** 30):.5f} GB")
    else:
        used_mem = load_avg = memory = disk_usage = uptime = data

    DATA["layout_info"]["Load avg"] = load_avg
    DATA["layout_info"]["Available disk"] = disk_usage
    DATA["layout_info"]["Memory"] = f"{used_mem} / {memory}"
    DATA["layout_info"]["Uptime"] = f"{uptime}"
    return DATA


async def system_info():
    metrics = await handle_request(NODE_EXPORTER, "/metrics", True)
    if '[ERR]' in metrics:
        # return (metrics,) * 5
        return await handle_system_info('[ERR] node_exporter')
        # return ('[ERR]',) * 5
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
    return await handle_system_info(data)


async def get_inflation():
    result = await handle_request(REST, 'cosmos/mint/v1beta1/inflation', True)
    return loads(result)['inflation']


async def peers():
    net_info = await handle_request(RPC, "net_info")
    if 'ERR' not in net_info:
        peers = int(net_info['n_peers'])
        peers = f"[b][red]{peers}" if peers < 10 else f"[b][green]{peers}"
        return layout["Peers"].update(footer(peers, 'Peers'))

    return layout["Peers"].update(footer(f"[bold red][ERR] peers", 'Peers'))


async def get_price(denom, amount):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={denom}&vs_currencies=usd"
        price = requests.get(url).json()[denom]['usd']
        price = round(amount * price, 2)
        return f"{amount} {denom.upper()} / {price}$"
    except Exception:
        return f'{amount} {denom.upper()} / [bold red][blink][ERR] get_price'


async def get_rewards():
    """get current reward/comission"""
    url = f"distribution/validators/{VALOPER}"
    rewards, comission = 0, 0
    DENOM = 'uumee'
    try:
        data = await handle_request(REST, url)
        for denom in data['self_bond_rewards']:
            if denom['denom'] == DENOM:
                rewards += int(round(float(denom['amount'])))
        for denom in data['val_commission']['commission']:
            if denom['denom'] == DENOM:
                comission += int(round(float(denom['amount'])))

        rewards = round((rewards + comission) / DECIMALS)
        result = await get_price('umee', rewards)
        return layout["Rewards"].update(footer(f"[b][magenta]{result}", 'Rewards'))
    except (IndexError, TypeError):
        result = 0
        return layout["Rewards"].update(footer(f"[b][magenta]{result}", 'Rewards'))


async def count_uptime(response, block):
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
            await tg_allert_message(f'Missed block: {block}')

    layout["blocks"].update(layout_body(UPTIME))


async def aiter(blocks):
    for block in range(blocks):
        yield block


async def get_uptime():
    response = await handle_request(REST, "blocks/latest", True)
    last_block = int(loads(response)['block']['header']['height'])
    if len(UPTIME) > 0:
        last_tracked_block = int(UPTIME[-1].split()[-1])
        # while last_tracked_block < last_block:
        # last_block += 1
        async for block in aiter(last_block - last_tracked_block):
            last_tracked_block += 1
            # UPTIME[-1] = '[green]✓ 123456'
            # int(UPTIME[-1].split()[-1]) -> 123456
            response = await handle_request(
                REST, f"blocks/{last_tracked_block}", True)
            await count_uptime(response, last_tracked_block)
    else:
        return await count_uptime(response, last_block)
    return layout["HEIGHT"].update(footer(f"[b][magenta]{last_block}", 'HEIGHT'))


async def get_eth_balance():
    data = {"jsonrpc": "2.0", "method": "eth_getBalance",
            "params": [f"{ORCH_ETH_ADDRESS}", "latest"], "id": 1}
    headers = {'Content-Type': 'application/json'}

    if ORCH_ETH_ADDRESS:
        try:
            response = requests.post(ETH_RPC, data=dumps(data),
                                     headers=headers).json()['result']
            balance = round(float(int(response, 16) / 10 ** 18), 2)
            if balance < 0.1:
                await tg_allert_message(f'WARN ETH balance: {balance} ETH ')
            eth_in_usd = await get_price('ethereum', balance)
            return f'{eth_in_usd}'
        except Exception as err:
            return f'[ERR] {err}'
    return f'[ERR] ORCH keys probably doesnt set! Cant find eth addr!'


async def get_current_valset():
    try:
        pattern = "/gravity/v1beta/valset/current"
        response = await handle_request(REST, pattern, True)
        orch_in_valset = "[green]True" if ORCH_ETH_ADDRESS.lower(
        ) in response.lower() else f"[bold red][blink]False"
        current_valset = loads(response)
        return orch_in_valset, current_valset

    except Exception as err:
        return (f"[ERR] get_current_valset {err}") * 2


async def get_slahing_info():
    pattern = f"/cosmos/slashing/v1beta1/signing_infos/{VALCONS}"
    response = await handle_request(REST, pattern, True)
    if VALCONS:
        try:
            response = loads(response)
            missed_block_counter = response['val_signing_info']['missed_blocks_counter']
            if missed_block_counter == '0':
                missed_block_counter = f"[b][green]{missed_block_counter}"
            elif missed_block_counter != '0':
                missed_block_counter = f"[b][red]{missed_block_counter}"

            return layout["Block_counter"].update(footer(f'{missed_block_counter}', 'Block Counter'))
        except Exception as err:
            return layout["Block_counter"].update(footer(f'[ERR] {err}', 'Block Counter'))
    return layout["Block_counter"].update(footer('[ERR] valcons not specified', 'Block Counter'))


async def eth_rpc_status():
    data = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(ETH_RPC, data=dumps(
            data), headers=headers).json()['result']
        response2 = requests.post(ETH_RPC2, data=dumps(
            data), headers=headers).json()['result']
        local_rpc_last_block, remote_rpc_last_block = int(
            response, 16), int(response2, 16)

        if local_rpc_last_block == remote_rpc_last_block:
            return f"[green]GOOD {local_rpc_last_block}"

        elif abs(local_rpc_last_block - remote_rpc_last_block) > 5:
            await tg_allert_message(f'WARN ETH RPC:\nlocal eth node:{local_rpc_last_block}\ninfura:{remote_rpc_last_block}')
            return f"[red]WARN local eth node:{local_rpc_last_block} infura:{remote_rpc_last_block}"

        return f"[yellow]WARN local:{local_rpc_last_block} infura:{remote_rpc_last_block}"
    except Exception as err:
        return f'[ERR] {err}'


async def get_peggo_params():
    global BRIDGE_CHAIN_ID
    global BRIDGE_ETHEREUM_ADDR
    if not BRIDGE_CHAIN_ID or not BRIDGE_ETHEREUM_ADDR:
        url = '/gravity/v1beta/params'
        try:
            response = await handle_request(REST, url, True)
            response = loads(response)
            # BRIDGE_ETHEREUM_ADDR = response['params']['bridge_ethereum_address']
            BRIDGE_CHAIN_ID = response['params']['bridge_chain_id']
            return (BRIDGE_ETHEREUM_ADDR, BRIDGE_CHAIN_ID)
        except Exception as err:
            return (f'[ERR] {err}',) * 2
    return


async def get_delegate_keys():
    url = f'/gravity/v1beta/query_delegate_keys_by_validator?validator_address={VALOPER}'
    global ORCH_ETH_ADDRESS
    global ORCH_UMEE_ADDR
    if not ORCH_ETH_ADDRESS or not ORCH_UMEE_ADDR:
        try:
            # response = loads(await handle_request(REST, url, True))
            response = await handle_request(REST, url, True)
            if 'no validator' in response.lower():
                # ORCH_ETH_ADDRESS, ORCH_UMEE_ADDR = ('[b][red][blink]KEYS NOT SET') * 2
                ORCH_ETH_ADDRESS = ORCH_UMEE_ADDR = '[b][red][blink]KEYS NOT SET'
                return
            response = loads(response)
            ORCH_ETH_ADDRESS = response['eth_address']
            ORCH_UMEE_ADDR = response['orchestrator_address']
            return ORCH_ETH_ADDRESS, ORCH_UMEE_ADDR
        except Exception as err:
            return (f'[ERR] {err}',) * 2
    return


async def get_last_event_nonce():
    orch_event_list = []
    nonce_url = f"gravity/v1beta/oracle/eventnonce/"
    try:
        if not ORCHESTRATORS or len(ORCHESTRATORS) < 99:
            url = f"/cosmos/staking/v1beta1/validators?status=BOND_STATUS_BONDED"
            response = loads(await handle_request(REST, url, True))
            async for val in aiter(len(response['validators'])):
                if response['validators'][val]['operator_address'] not in VALIDATORS:
                    # print('test')
                    orch_url = f"/gravity/v1beta/query_delegate_keys_by_validator?validator_address={response['validators'][val]['operator_address']}"
                    response2 = loads(await handle_request(REST, orch_url, True))
                    ORCHESTRATORS.append(response2['orchestrator_address'])
                    VALIDATORS.append(response['validators'][val]['operator_address'])
                    break

        # shuffle list every time and iterate over 5 orch at once
        shuffle(ORCHESTRATORS)
        for orch in ORCHESTRATORS[:5]:
            response = loads(await handle_request(REST, f"{nonce_url}{orch}", True))['event_nonce']
            orch_event_list.append(int(response))

        own_event_nonce = int(loads(await handle_request(REST, f"{nonce_url}{ORCH_UMEE_ADDR}", True))['event_nonce'])
        if abs(max(orch_event_list) - own_event_nonce) > 3:
            await tg_allert_message(f'Event_nonce allert:\nLast own_event_nonce: {own_event_nonce} \n 5 random events: {orch_event_list}')
            return f"{own_event_nonce} / {orch_event_list}"

        return f"{own_event_nonce} / {orch_event_list} / {len(ORCHESTRATORS)}"

    except Exception as err:
        return f"[ERR] get_last_event_nonce {err}"


async def get_validators_set():
    try:
        url = f"/cosmos/staking/v1beta1/validators?status=BOND_STATUS_BONDED"
        response = loads(await handle_request(REST, url, True))
        active_set = int(response['pagination']['total'])
        active_set = f"[b][green]{active_set}" if active_set > 99 else f"[b][red]{active_set}"
        return layout["Active_vals"].update(footer(active_set, 'Validators'))
    except Exception as err:
        response = f"[b][red]{err}"
        return layout["Active_vals"].update(footer(response, 'Validators'))


async def status():
    status = loads(await handle_request(RPC, "/status", True))['result']
    DATA["layout_info"]["NETWORK"] = f"{status['node_info']['network']}"
    DATA["layout_info"]["Server IP"] = f"{status['node_info']['listen_addr']}"

    layout["val_info"].update(layout_info(DATA))
    layout["Catching_up"].update(footer(f"[b][green]{status['sync_info']['catching_up']}", 'Catching_up'))
    return DATA


async def main():
    unconfirmed_txs = await handle_request(RPC, "/num_unconfirmed_txs")
    inflation = float(await get_inflation()) * 100
    total_uptime = len(UPTIME)
    DATA["layout_info"]["val_address"] = f"{VALIDATOR_ADDR[:15]}..{VALIDATOR_ADDR[-10:]}"
    DATA["layout_info"]["valoper"] = f"[u blue link=https://www.mintscan.io/umee/validators/{VALOPER}]{VALOPER[:26]}.."
    DATA["layout_info"]["Delegator"] = f"[u blue link=https://www.mintscan.io/umee/account/{DELEGATOR}]{DELEGATOR[:26]}.."
    DATA["layout_info"]["Telegram"] = f"[green]Enabled" if TELEGRAM_TOKEN else f"[red]Disabled"
    DATA["layout_info"]["Inflation"] = f"{inflation:.2f}%"
    DATA["layout_info"]["Mempool"] = f"{float(unconfirmed_txs['total_bytes'])/1000:.2f}Kb"
    DATA["layout_info"]["unconfirmed_txs"] = unconfirmed_txs['n_txs']
    DATA["layout_info"]["Proposed"] = f"{COMMITS[2]}/{total_uptime}"
    DATA["layout_info"]["Signed"] = f"{COMMITS[1]}/{total_uptime}"
    DATA["layout_info"]["Missed"] = f"{COMMITS[0]}/{total_uptime}"
    # DATA["layout_info"]["Tombstoned"] = f"[green]{tombstone}" if False == tombstone else f"[bold red]True"
    layout["val_info"].update(layout_info(DATA))
    return DATA


async def peggo_main():
    data = {}
    eth_rpc_stats = await eth_rpc_status()
    eth_balance = await get_eth_balance()
    orch_in_valset, current_valset = await get_current_valset()
    bridge_eth_addr_slice = f"{BRIDGE_ETHEREUM_ADDR[:11]}..{BRIDGE_ETHEREUM_ADDR[-11:]}"
    data['bridge_chain'] = BRIDGE_CHAINS[BRIDGE_CHAIN_ID]
    data['bridge_eth_addr'] = f"[u blue link=https://etherscan.io/address/{BRIDGE_ETHEREUM_ADDR}]{bridge_eth_addr_slice}"
    data['orch_eth_address'] = f"[u blue link=https://etherscan.io/address/{ORCH_ETH_ADDRESS}]{ORCH_ETH_ADDRESS}"
    data['orch_umee_addr'] = f"[u blue link=https://www.mintscan.io/umee/account/{ORCH_UMEE_ADDR}]{ORCH_UMEE_ADDR}"
    data['orch_eth_balance'] = f"[b][magenta]{eth_balance}" if 'ERR' not in eth_balance else f"[bold red]{eth_balance}"
    data['current_valset'] = len(current_valset['valset']['members'])
    data['orch_in_valset'] = orch_in_valset
    data['eth_rpc_status'] = eth_rpc_stats
    data['Last Event Nonce'] = await get_last_event_nonce()

    for member in current_valset['valset']['members']:
        if ORCH_ETH_ADDRESS.lower() == member['ethereum_address'].lower():
            data['power'] = f"[green]{member['power']}"
            break
        else:
            data['power'] = "[bold red]Can't find! Check peggo valset!"

    layout['peggo_state'].update(layout_info(data))

    return data


async def loop1() -> int:
    while True:
        await asyncio.create_task(get_pubkey_vp_moniker())
        await asyncio.sleep(0.1)
        await asyncio.create_task(main())
        await asyncio.sleep(0.1)
        await asyncio.create_task(get_slahing_info())
        await asyncio.sleep(0.1)
        await asyncio.create_task(status())
        await asyncio.sleep(0.1)
        await asyncio.create_task(get_delegator_txs())
        await asyncio.sleep(0.1)
        await asyncio.create_task(get_validators_set())
        await asyncio.sleep(0.1)
        await asyncio.create_task(get_rewards())
        await asyncio.sleep(0.1)
        await asyncio.create_task(get_delegate_keys())
        await asyncio.sleep(0.1)
        await asyncio.create_task(get_peggo_params())
        await asyncio.sleep(0.1)
        await asyncio.create_task(get_orch_txs())
        await asyncio.sleep(0.1)
        await asyncio.create_task(peggo_main())
        await asyncio.sleep(0.1)
        await asyncio.create_task(get_proposals())
        await asyncio.sleep(0.1)
        await asyncio.create_task(get_eth_txs())
        await asyncio.sleep(0.1)
        await asyncio.create_task(peers())


async def loop2():
    while True:
        await asyncio.create_task(get_uptime())
        await asyncio.sleep(0.1)
        await asyncio.create_task(system_info())


def amain() -> int:
    with Live(layout, screen=True, transient=True, refresh_per_second=2):
        loop = asyncio.get_event_loop()
        loop.create_task(loop1())
        loop.create_task(loop2())
        loop.run_forever()


if __name__ == "__main__":
    try:
        exit(amain())
    except KeyboardInterrupt:
        pass
