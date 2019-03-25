#!/usr/bin/python3

import logging
import argparse
import os
import inspect
import pprint
import eospy.cleos
import datetime as dt
import pytz
import requests
import time
import datetime

pp = pprint.PrettyPrinter(indent=4)

SCRIPT_PATH = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))

parser = argparse.ArgumentParser()
parser.add_argument("-v", '--verbose', action="store_true",
                    dest="verbose", help='Print logged info to screen')
parser.add_argument("-d", '--debug', action="store_true",
                    dest="debug", help='Print debug info')
parser.add_argument('-l', '--log_file', default='{}.log'.format(
    os.path.basename(__file__).split('.')[0]), help='Log file')
parser.add_argument('-u', '--uri', required=True, help='RPC endpoint')
parser.add_argument('-bp', '--bp-account', required=True,
                    help='BP account')
parser.add_argument('-p', '--permission', required=True,
                    help='Permission used for the claim')
parser.add_argument('-k', '--key', required=True,
                    help='Private key')
parser.add_argument('-s', '--symbol', required=False,
                    help='Symbol', default='EOS')
args = parser.parse_args()

VERBOSE = args.verbose
DEBUG = args.debug
LOG_FILE = args.log_file
URI = args.uri
PERMISSION = args.permission
BP_ACCOUNT = args.bp_account
KEY = args.key
SYMBOL = args.symbol

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
if DEBUG:
    logger.setLevel(logging.DEBUG)
if VERBOSE:
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

fh = logging.FileHandler(LOG_FILE)
logger.addHandler(fh)
fh.setFormatter(formatter)

SCRIPT_PATH = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))


def get_system_token_supply():
    cleos = eospy.cleos.Cleos(url=URI)
    data = cleos.get_table(
        code='eosio.token', scope=SYMBOL, table='stat', limit=1)
    amount = data['rows'][0]['supply'].split(' ')[0]
    return float(amount) * 10000


def get_global_state():
    cleos = eospy.cleos.Cleos(url=URI)
    data = cleos.get_table(
        code='eosio', scope='eosio', table='global', limit=1)
    return data['rows'][0]


def get_producer():
    cleos = eospy.cleos.Cleos(url=URI)
    data = cleos.get_table(
        code='eosio', scope='eosio', table='producers', lower_bound=BP_ACCOUNT, limit=1)
    return data['rows'][0]


def calculate_reward():

    token_supply = get_system_token_supply()
    global_state = get_global_state()
    producer = get_producer()

    continuous_rate = 0.04879  # 5 % annual rate
    useconds_per_year = 52 * 7 * 24 * 3600 * 1000000

    last_block_time = int(round((time.time() - 500) * 1000000))
    last_pervote_bucket_fill = datetime.datetime.strptime(
        global_state['last_pervote_bucket_fill'], '%Y-%m-%dT%H:%M:%S.%f').timestamp()*1000000
    usecs_since_last_fill = last_block_time - last_pervote_bucket_fill

    pervote_bucket = int(global_state['pervote_bucket'])

    new_tokens = (continuous_rate * token_supply *
                  usecs_since_last_fill) / useconds_per_year
    to_producers = new_tokens / 5
    to_per_block_pay = to_producers / 4
    to_per_vote_pay = to_producers - to_per_block_pay

    pervote_bucket += to_per_vote_pay
    reward = pervote_bucket * \
        float(producer['total_votes']) / \
        float(global_state['total_producer_vote_weight'])
    reward /= 10000

    return reward


def main():
    if SYMBOL == 'EOS':
        reward = calculate_reward()
        logger.info('Current reward: {}'.format(reward))
        if reward < 100:
            logger.info('Rewards < 100. Exit')
            quit()

    cleos = eospy.cleos.Cleos(url=URI)
    arguments = {
        "owner": BP_ACCOUNT
    }
    payload = {
        "account": "eosio",
        "name": "claimrewards",
        "authorization": [{
                "actor": BP_ACCOUNT,
                "permission": PERMISSION,
        }],
    }

    data = cleos.abi_json_to_bin(
        payload['account'], payload['name'], arguments)
    payload['data'] = data['binargs']

    trx = {"actions": [payload]}
    trx['expiration'] = str(
        (dt.datetime.utcnow() + dt.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))

    try:
        resp = cleos.push_transaction(trx, KEY, broadcast=True)
        logger.info(resp)

    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    main()
