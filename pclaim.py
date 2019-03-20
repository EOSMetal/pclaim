#!/usr/bin/env python3

import logging
import argparse
import os
import colorlog
import inspect
import pprint
import eospy.cleos
import datetime as dt
import pytz
import requests

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
args = parser.parse_args()

VERBOSE = args.verbose
DEBUG = args.debug
LOG_FILE = args.log_file
URI = args.uri
PERMISSION = args.permission
BP_ACCOUNT = args.bp_account
KEY = args.key


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s%(reset)s')
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


def main():
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
        print(resp)

    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
