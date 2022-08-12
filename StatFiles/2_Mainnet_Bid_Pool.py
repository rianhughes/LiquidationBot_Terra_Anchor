

import requests
import urllib
import json

import time
from terra_sdk.client.lcd import LCDClient
from terra_sdk.key.mnemonic import MnemonicKey
from terra_sdk.core.coins import Coins
from terra_sdk.core.coins import Coin
from terra_sdk.core.auth import StdFee
from terra_sdk.core.bank import MsgSend
from terra_sdk.core.wasm import MsgExecuteContract
from terra_sdk.exceptions import LCDResponseError
from time import sleep
from contact_addresses import contact_addresses
from datetime import datetime
import os
from pprint import pprint
#import terraswap_swap_watch as terraswap

# Config
NETWORK = 'MAINNET'
mnemonic = os.environ.get('MNEMONIC', '')


terra_swap_endpoint = 'https://fcd.terra.dev'

##########################################
# Custom Terra class to hold relevant data
##########################################

def get_terra_gas_prices():
    try:
        r = requests.get("https://fcd.terra.dev/v1/txs/gas_prices")
        r.raise_for_status()
        if r.status_code == 200:
            return r.json()
    except requests.exceptions.HTTPError as err:
        print(f"Could not fetch get_terra_gas_prices from Terra's FCD. Error message: {err}")

class Terra:
    def __init__(self):
        if NETWORK == 'MAINNET':
            self.chain_id = 'columbus-5'
            self.public_node_url = 'https://lcd.terra.dev'
            # self.public_node_url = 'http://192.168.130.2:1317'
            self.tx_look_up = f'https://finder.terra.money/{self.chain_id}/tx/'
            self.get_contract_addresses = contact_addresses(network='MAINNET')
        else:
            self.chain_id = 'bombay-12'
            # self.chain_id = 'tequila-0004'
            # self.public_node_url = 'https://tequila-lcd.terra.dev'
            self.public_node_url = 'https://bombay-lcd.terra.dev'
            # self.public_node_url = 'http://127.0.0.1:1317'
            self.tx_look_up = f'https://finder.terra.money/{self.chain_id}/tx/'
            self.get_contract_addresses = contact_addresses(network='bombay-12')

        # Contract required
        #self.aTerra = self.get_contract_addresses['aTerra']
        self.mmMarket = self.get_contract_addresses['mmMarket']
        self.mmOverseer = self.get_contract_addresses['mmOverseer']
        self.mmLiquidation = self.get_contract_addresses['mmLiquidation']
        self.bLunaCustody = self.get_contract_addresses['bLunaCustody']
        self.bLunaToken = self.get_contract_addresses['bLunaToken']
        self.ANCToken = self.get_contract_addresses['ANC']
        self.aUST = self.get_contract_addresses['aUST']
        

        #self.terraswapbLunaLunaPair = self.contract_addresses['terraswapblunaLunaPair']

        # Collateral tokens
        self.bLuna = "terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp"
        self.bEth = "terra1dzhzukyezv0etz22ud940z7adyv7xgcjkahuun"

        # Load Terra LCD client
        self.terra = LCDClient(
            chain_id=self.chain_id,
            url=self.public_node_url,
            gas_prices=get_terra_gas_prices(),
            gas_adjustment=1.6)

        # Load wallet
        mnemonic_ = ""
        self.mk = MnemonicKey(mnemonic=mnemonic)
        self.wallet = self.terra.wallet(self.mk)

        # Load (native) balance
        self.balance = self.terra.bank.balance(self.wallet.key.acc_address)


# Instantiate Terra class
terra_inst = Terra()



##########################
# Anchor Query and Execute
##########################

def get_query(contract_ad, query_msg):
    # query the anchor contract
    return terra_inst.terra.wasm.contract_query(contract_ad, query_msg)


def get_bidpool_totalbidamt(prem_slot, token):
    qry_msg = { "bid_pool": { "collateral_token": token,    "bid_slot": prem_slot }}
    resp = get_query(terra_inst.mmLiquidation, qry_msg)
    return resp['total_bid_amount']

## Get the Mainnet BidPool
# I think total_bid_amount is uusd
# Can you query multiple things at once? Would speed this up.

bLuna_token = terra_inst.bLuna
bEth_token = terra_inst.bEth

bLuna_pool = {} # key = prem_slot. value = total_bid_amount in UST.
bEth_pool  = {} # key = prem_slot. value = total_bid_amount in UST.

for k in range(0,10):
    bLuna_pool[k] = int(get_bidpool_totalbidamt(k, bLuna_token))/(10**6)
    bEth_pool[k]  = int(get_bidpool_totalbidamt(k, bEth_token))/(10**6)

print(bLuna_pool)
print(bEth_pool)


# Plot the BidPool
import matplotlib.pyplot as plt

fig, ax = plt.subplots()

plt.subplot(1,2,1)
plt.bar(list(bLuna_pool.keys()), list(bLuna_pool.values()))
plt.xlabel("Prem_slot"); plt.ylabel("Amount UST"); plt.title("bLuna BidPool")

plt.subplot(1,2,2)
plt.bar(list(bEth_pool.keys()), list(bEth_pool.values()))
plt.xlabel("Prem_slot"); plt.ylabel("Amount UST"); plt.title("bEth BidPool")

ax.ticklabel_format(useOffset=False)

plt.show()



