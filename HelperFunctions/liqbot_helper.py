# Requir Python3.9, and terra_sdk. If you have problems, make a clean conda environment.
# run conda activate data_science_stuff

# Mainnet addresses https://finder.extraterrestrial.money/mainnet/anchor
# Testnet addresses https://finder.extraterrestrial.money/testnet/anchor


# Terra Blockchain 101:
#   1. Need to create and sign a transaction (via wallter is easiet)
#   2. Then need to broadcast that trasnaction to the network
#   3. Each broadcast costs fees. Current code isn't very tx-efficient

# Anchor Dev Notes:
# 1. Bids are made with uusd, not aUST.

# Terraswap Notes:
# No aUST on terraswaps test net => Have to get aUST via Anchor deposits
# No bLuna-UST pool on terraswap => Need to route bLuna->Luna, and Luna->UST
# UST is called uusd
# Swapping Token1 for Token2, requires a different msg than Token2 for Token1 

# Misc:
#  1. StdFee(gas_fee_would_like, gas_fee_amount_willing_to_spend)
#  2. Gas fees
#  3. There is a spread_tax when trading UST and Luna
#  4. There is a tobin_stax when trading between stablecoins

# To do:
# 1. Insert terraswap swap fees for PnL estimate
# 2. User BidPool to gather info about Mainnet bid pool

import requests
import urllib
import json

import time
from terra_sdk.client.lcd import LCDClient
from terra_sdk.key.mnemonic import MnemonicKey
from terra_sdk.core.coins import Coins
from terra_sdk.core.coins import Coin
#from terra_sdk.core.auth import StdFee
from terra_sdk.core.bank import MsgSend
from terra_sdk.core.wasm import MsgExecuteContract
from terra_sdk.exceptions import LCDResponseError
from terra_sdk.client.lcd.api.tx import CreateTxOptions

from time import sleep

from contact_addresses import contact_addresses
from datetime import datetime
from datetime import date

import os
from os.path import exists

from pprint import pprint
from ast import literal_eval
from pandas import Timestamp, DataFrame


##########################################
# Custom Terra class to hold relevant data
##########################################

def get_terra_gas_prices():
    terra_swap_endpoint = 'https://fcd.terra.dev'
    try:
        r = requests.get("https://fcd.terra.dev/v1/txs/gas_prices")
        r.raise_for_status()
        if r.status_code == 200:
            return r.json()
    except requests.exceptions.HTTPError as err:
        print(f"Could not fetch get_terra_gas_prices from Terra's FCD. Error message: {err}")

class Terra:
    def __init__(self, NETWORK_, wallet_seed):
        if NETWORK_ == 'MAINNET':
            self.chain_id = 'columbus-5'
            self.public_node_url = 'https://lcd.terra.dev'
            self.get_contract_addresses = contact_addresses(network='MAINNET')
            # self.public_node_url = 'http://192.168.130.2:1317'
            #self.tx_look_up = f'https://finder.terra.money/{self.chain_id}/tx/'     # I commented this out
        else:
            self.chain_id = 'bombay-12'
            self.public_node_url = 'https://bombay-lcd.terra.dev'
            self.get_contract_addresses = contact_addresses(network='bombay-12')
            # self.chain_id = 'tequila-0004'
            # self.public_node_url = 'https://tequila-lcd.terra.dev'
            # self.public_node_url = 'http://127.0.0.1:1317'
            #self.tx_look_up = f'https://finder.terra.money/{self.chain_id}/tx/'     # I commented this out 

        # Contract required
        self.aUST = self.get_contract_addresses['aUST']
        self.mmMarket = self.get_contract_addresses['mmMarket']
        self.mmOverseer = self.get_contract_addresses['mmOverseer']
        self.mmLiquidation = self.get_contract_addresses['mmLiquidation']
        self.bLunaCustody = self.get_contract_addresses['bLunaCustody']
        self.bLunaToken = self.get_contract_addresses['bLunaToken']
        self.bETHToken = self.get_contract_addresses['bETHToken']
        self.ANCToken = self.get_contract_addresses['ANC']
        self.aUST = self.get_contract_addresses['aUST']
        self.terraswapbLunaLunaPool = self.get_contract_addresses['terraswapbLunaLunaPool']
        self.terraswapRouter = self.get_contract_addresses['terraswapRouter']
        self.terraswapbETHUstPool = self.get_contract_addresses['terraswapbETHUstPool']
        
        # Load Terra LCD client
        self.terra = LCDClient(
            chain_id=self.chain_id,
            url=self.public_node_url,
            gas_prices= get_terra_gas_prices(),   # I changed this
            gas_adjustment=1.5)

        # Load wallet
        #mnemonic_ = wallet_seed
        mnemonic = os.environ.get('MNEMONIC', wallet_seed)
        self.mk = MnemonicKey(mnemonic=mnemonic)
        self.wallet = self.terra.wallet(self.mk)

        # Load (native) balance
        self.balance = self.terra.bank.balance(self.wallet.key.acc_address)

        # Denoms (should be params file, or vice versa?)
        self.denom_uusd = 10**6
        self.denom_uluna = 10**6
        self.denom_bluna = 10**6
        self.denom_bETH = 10**6
    
# Instantiate Terra class
#terra_inst = Terra()


##################################
# Get Balances (Native, and Token)
##################################

def get_token_balance(terra_inst, token_address):
    query_msg = {'balance': { 'address': terra_inst.wallet.key.acc_address } }
    return int(terra_inst.terra.wasm.contract_query(token_address, query_msg)['balance'])

def qry_full_balance(terra_inst):
    bal ={}
    bal['coins'] = terra_inst.balance[0]
    bal['aUST'] = get_token_balance(terra_inst, terra_inst.aUST)
    bal['bLuna'] = get_token_balance(terra_inst, terra_inst.bLunaToken)
    bal['bETH'] = get_token_balance(terra_inst, terra_inst.bETHToken)
    return bal 

def update_wallet_exposure(terra_inst):
    bal = qry_full_balance(terra_inst)
    wlt_exp = {}
    try:
        wlt_exp['bLuna'] = bal['bLuna']
    except Exception as e:
        if(str(e) == '\'bLuna\''):
            wlt_exp['bLuna'] = 0

    try:
        wlt_exp['uLuna'] = bal['coins'].get('uluna').amount
    except Exception as e:
        if(str(e) == '\'NoneType\' object has no attribute \'amount\''):
            wlt_exp['uLuna'] = 0           

    try:
        wlt_exp['bETH'] = bal['bETH']
    except Exception as e:
        if(str(e) == '\'NoneType\' object has no attribute \'amount\''):
            wlt_exp['bETH'] = 0

    where_ust = {}
    bal = qry_full_balance(terra_inst)
    claimable_liq = qry_claimable_liq(terra_inst, terra_inst.bLunaToken)
    where_ust['wallet'] =  bal['coins'].get('uusd').amount/terra_inst.denom_uusd

    bids_by_user_bLuna = qry_active_bLuna_bids(terra_inst, terra_inst.bLunaToken)
    where_ust['bidbook_bLuna'] = sum_bidbook_liq(bids_by_user_bLuna)/terra_inst.denom_uusd

    bids_by_user_bETH = qry_active_bETH_bids(terra_inst, terra_inst.bETHToken)
    where_ust['bidbook_bETH'] = sum_bidbook_liq(bids_by_user_bETH)/terra_inst.denom_uusd    

    return wlt_exp, where_ust

if 0:
    print("")
    print("Balance : ",terra_inst.balance)
    print("Balance [aUST] : ", get_token_balance(terra_inst, terra_inst.aUST)/(10**6))    
    print("Balance [bLuna] : ", get_token_balance(terra_inst, terra_inst.bLunaToken)/(10**6)) 
    print("Balance [ANC] : ", get_token_balance(terra_inst, terra_inst.ANCToken)/(10**6))
    print("")

#############################
# Query and Execute Terraswap
#############################

def get_bLuna_to_Luna_price():
    terra_swap_endpoint = 'https://fcd.terra.dev'
    terraswap_Luna_bLuna_add = 'terra1jxazgm67et0ce260kvrpfv50acuushpjsz2y0p'
    query_msg = {"simulation":
                 {"offer_asset":
                     {"amount":"1000000",
                      "info":  { "token":{"contract_addr": "terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp" }}}}  }
    resp = requests.get(terra_swap_endpoint + '/wasm/contracts/' + terraswap_Luna_bLuna_add + '/store', params={'query_msg': str(query_msg)}).json()["result"]
    return int(resp['return_amount'])/1000000

def execute_terraswap_coins_fee(terra_inst, contract_ad, execute_msg, amt_to_send, gas_fee):
    execute = MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=execute_msg,  coins=amt_to_send  )
    created_tx = terra_inst.wallet.create_and_sign_tx([execute] , memo = "Swap",  fee=StdFee(gas_fee, str(gas_fee)+"uusd"))
    return terra_inst.terra.tx.broadcast(created_tx)

def execute_terraswap_coins_no_fee(terra_inst, contract_ad, execute_msg, amt_to_send):
    execute = MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=execute_msg,  coins=amt_to_send  )
    created_tx = terra_inst.wallet.create_and_sign_tx([execute] , memo = "Swap")
    return terra_inst.terra.tx.broadcast(created_tx)

def execute_terraswap_coins_no_fees_update(terra_inst, contract_ad, execute_msg, amt_to_send):
    tx = [MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=execute_msg,  coins=amt_to_send  )]
    tx = CreateTxOptions(msgs=tx,  gas_prices="0.15uusd",    gas_adjustment="1.2")  # Doesn't use 0.15, not sure what it's for..
    tx = terra_inst.wallet.create_and_sign_tx(tx)
    return terra_inst.terra.tx.broadcast(tx)

# execute terraswap no coins
def execute_terraswap_fee(terra_inst, contract_ad, execute_msg, gas_fee):
    execute = MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=execute_msg)
    created_tx = terra_inst.wallet.create_and_sign_tx([execute] , memo = "Swap",  fee=StdFee(gas_fee, str(gas_fee)+"uusd"))
    return terra_inst.terra.tx.broadcast(created_tx)


def execute_terraswap_no_fee(terra_inst, contract_ad, execute_msg):
    execute = MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=execute_msg)
    created_tx = terra_inst.wallet.create_and_sign_tx([execute] , memo = "Swap")
    return terra_inst.terra.tx.broadcast(created_tx)

def execute_terraswap_no_fees_update(terra_inst, contract_ad, execute_msg):
    tx = [MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=execute_msg)]
    tx = CreateTxOptions(msgs=tx,  gas_prices="0.15uusd",    gas_adjustment="1.2")  # Doesn't use 0.15, not sure what it's for..
    tx = terra_inst.wallet.create_and_sign_tx(tx)
    return terra_inst.terra.tx.broadcast(tx)

def get_terraswap_bLuna_to_Luna_price(input_amt):
    # Bluna to Luna. See old_files for reverse price.
    # Note: Just some websites endpoint. Not interacting with any smart contract.
    terra_swap_endpoint = 'https://fcd.terra.dev'
    contract_address = 'terra1jxazgm67et0ce260kvrpfv50acuushpjsz2y0p'
    query_msg = '{"simulation":{"offer_asset":{"amount":'+"\""+str(input_amt)+"\""+',"info":{"token":{"contract_addr":"terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp"}}}}}'
    resp = requests.get(terra_swap_endpoint + '/wasm/contracts/' + contract_address + '/store', params={'query_msg': query_msg}).json()
    return int(resp['result']['return_amount'])/input_amt

def get_terraswap_Luna_to_UST_price(input_amt):
    # Get the price for LUNA ---> UST (Sell). See old_files for reverse price.
    terra_swap_endpoint = 'https://fcd.terra.dev'
    contract_address = 'terra1tndcaqxkpc5ce9qee5ggqf430mr2z3pefe5wj6'
    query_msg = '{"simulation":{"offer_asset":{"amount":' + "\"" +str(input_amt) + "\"" +',"info":{"native_token":{"denom":"uluna"}}}}}'
    resp = requests.get(terra_swap_endpoint + '/wasm/contracts/' + contract_address + '/store', params={'query_msg': query_msg}).json()
    return int(resp['result']['return_amount'])/input_amt

def get_terraswap_bLuna_to_UST_price(input_amt):
    bLuna_to_Luna = get_terraswap_bLuna_to_Luna_price(input_amt)
    Luna_to_UST = get_terraswap_Luna_to_UST_price(input_amt)
    return bLuna_to_Luna*Luna_to_UST

# Execute bLuna->Luna [Offer asset is contract-minted token]
def execute_swap_bLuna_for_Luna_testnet(terra_inst, amt_to_send:str, gas_fee):
    # amt_to_send = str(1*(10**4))+"bluna"
    coin_to_send = Coin.from_str(amt_to_send)
    terraswap_pair_add = terra_inst.terraswapbLunaLunaPool
    token_add = terra_inst.bLunaToken
    exec_msg = {"send": {"contract": terraswap_pair_add, "amount": str(coin_to_send.amount) , "msg": "eyJzd2FwIjp7fX0=" }}
    return execute_terraswap_fee(terra_inst, token_add, exec_msg, gas_fee )

def execute_swap_bLuna_for_Luna_testnet_no_fee(terra_inst, wallet_exposure):
    # amt_to_send = str(1*(10**4))+"bluna"
    coin_to_send = Coin.from_str(amt_to_send)
    terraswap_pair_add = terra_inst.terraswapbLunaLunaPool
    token_add = terra_inst.bLunaToken
    exec_msg = {"send": {"contract": terraswap_pair_add, "amount": str(wallet_exposure['bLuna']) , "msg": "eyJzd2FwIjp7fX0=" }}
    return execute_terraswap_no_fee(terra_inst, token_add, exec_msg)

def execute_swap_bLuna_for_Luna_testnet_no_fees_update(terra_inst, wallet_exposure):
    terraswap_pair_add = terra_inst.terraswapbLunaLunaPool
    token_add = terra_inst.bLunaToken
    exec_msg = {"send": {"contract": terraswap_pair_add, "amount": str(wallet_exposure['bLuna']) , "msg": "eyJzd2FwIjp7fX0=" }}
    return execute_terraswap_no_fees_update(terra_inst, token_add, exec_msg)


def execute_swap_bETH_for_UST_testnet_no_fees_update(terra_inst, wallet_exposure):
    terraswap_pair_add = terra_inst.terraswapbETHUstPool
    token_add = terra_inst.bETHToken
    exec_msg = {"send": {"contract": terraswap_pair_add, "amount": str(wallet_exposure['bETH']) , "msg": "eyJzd2FwIjp7fX0=" }}
    return execute_terraswap_no_fees_update(terra_inst, token_add, exec_msg)



# Execute Luna -> UST swap [Offer asset is native & IBC token]
def execute_swap_Luna_for_UST_testnet(terra_inst, amt_to_send:str, gas_fee): # Update the exec_msg min_r
    coin_to_send = Coin.from_str(amt_to_send)
    terraswap_router_add = terra_inst.terraswapRouter
    exec_msg = { "execute_swap_operations": { "operations": [ { "native_swap": { "ask_denom": "uusd",  "offer_denom": "uluna"  } }  ],
                "offer_amount": coin_to_send.amount, "minimum_receive": "10"  }}
    return execute_terraswap_coins_fee(terra_inst, terraswap_router_add, exec_msg, amt_to_send, gas_fee)


def execute_swap_Luna_for_UST_testnet_no_fee(terra_inst, amt_to_send:str): # Update the exec_msg min_r
    coin_to_send = Coin.from_str(amt_to_send)
    terraswap_router_add = terra_inst.terraswapRouter # Correct
    exec_msg = { "execute_swap_operations": { "operations": [ { "native_swap": { "ask_denom": "uusd",  "offer_denom": "uluna"  } }  ],
                "offer_amount": coin_to_send.amount, "minimum_receive": "10"  }}
    return execute_terraswap_coins_no_fee(terra_inst, terraswap_router_add, exec_msg, amt_to_send)

def execute_swap_Luna_for_UST_testnet_no_fees_update(terra_inst, wallet_exposure): # Update the exec_msg min_r
    terraswap_router_add = terra_inst.terraswapRouter
    exec_msg = { "execute_swap_operations": { "operations": [ { "native_swap": { "ask_denom": "uusd",  "offer_denom": "uluna"  } }  ],
                "offer_amount": str(wallet_exposure['uLuna']), "minimum_receive": "10"  }}
    return execute_terraswap_coins_no_fees_update(terra_inst, terraswap_router_add, exec_msg, str(wallet_exposure['uLuna'])+"uluna")


if 0:
    print("Price [bLuna->Luna] :", get_terraswap_bLuna_to_Luna_price(1))
    print("Price [Luna->UST] :" , get_terraswap_Luna_to_UST_price(1))
    print("Price [bLuna->UST] :" ,get_terraswap_bLuna_to_UST_price(1))

#############################
# Estimate PnL -> Need to turn this into a function
#############################

# 1. Gas fees. [Done]
# 2. Terra UST-Luna swap spread_tax. [Done]. Fucking the PnL.
# 3. Price impact. [Done]
# 4. Terraswap swap fee
if 0:
    # Parameters
    gas_fees = float(get_terra_gas_prices()['uusd'])
    spread_tax = 0.995 # Luna only
    prem_slot = 0.002
    loop_val_s = 10000 # uusd
    gas_cnt = 0
    
    bLuna_to_UST_price = get_terraswap_bLuna_to_UST_price(loop_val_s)
    bLuna_to_Luna_price = get_terraswap_bLuna_to_Luna_price(loop_val_s)
    Luna_to_UST_price = get_terraswap_Luna_to_UST_price(loop_val_s)
    
    # 1. Get collateral (eg bLuna) for prem_slot% discount
    loop_val = loop_val_s*(1+prem_slot)/bLuna_to_UST_price
    gas_cnt = gas_cnt + gas_fees
    
    # 2. Claim liquidation
    loop_val = loop_val
    gas_cnt = gas_cnt + gas_fees
    
    # 3. Swap bLuna for Luna
    #   Terraswap swap fee
    loop_val = loop_val*bLuna_to_Luna_price
    gas_cnt = gas_cnt + gas_fees
    
    # 4. Swap Luna for UST
    #   Terraswap swap fee
    # Spread_tax is only Luna/UST only. Not ETH/UST.
    loop_val = (loop_val*Luna_to_UST_price)*(spread_tax)
    gas_cnt = gas_cnt + gas_fees
    
    # 5. Loops PnL
    loop_val = loop_val - gas_cnt
    loop_collapsed = loop_val_s*spread_tax*(1+prem_slot)
    
    # Print dat mad PnL
    print("Loop PnL [%]:",loop_val_s/loop_val)
    print("Start Loop with :",loop_val_s, ", End Loop with :", loop_val)
    print("Collapsed loop", loop_val_s*spread_tax*(1+prem_slot))
    print("gas_cnt", gas_cnt)
    



##########################
# Anchor Query and Execute
##########################

def get_query(terra_inst,contract_ad, query_msg):
    # query the anchor contract
    return terra_inst.terra.wasm.contract_query(contract_ad, query_msg)

def execute_anchor(terra_inst, contract_ad, execute_msg):
    # Execute Anchor contract. Don't send coins.
    execute = MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=execute_msg )
    created_tx =  terra_inst.wallet.create_and_sign_tx([execute])
    return terra_inst.terra.tx.broadcast(created_tx)

def execute_anchor_fees(terra_inst, contract_ad, exec_msg, gas_fee):
    # Execute Anchor contract + send coins
    #tx = terra_inst.wallet.create_and_sign_tx( msgs=[MsgSend( terra_inst.wallet.key.acc_address,  contract_ad,  amt_to_send )], memo="test transaction!",fee=StdFee(200000, "120000uusd"))
    tx = MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=exec_msg)
    tx = terra_inst.wallet.create_and_sign_tx([tx], fee=StdFee(gas_fee, str(gas_fee) + "uusd"))
    return terra_inst.terra.tx.broadcast(tx)

def execute_anchor_no_fees(terra_inst, contract_ad, exec_msg):
    # Execute Anchor contract + send coins
    #tx = terra_inst.wallet.create_and_sign_tx( msgs=[MsgSend( terra_inst.wallet.key.acc_address,  contract_ad,  amt_to_send )], memo="test transaction!",fee=StdFee(200000, "120000uusd"))
    tx = MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=exec_msg)
    tx = terra_inst.wallet.create_and_sign_tx([tx])
    return terra_inst.terra.tx.broadcast(tx)

def execute_anchor_no_fees_update(terra_inst, contract_ad, exec_msg):
    # Execute Anchor contract + send coins
    tx = [MsgExecuteContract( sender = terra_inst.wallet.key.acc_address, contract = contract_ad, execute_msg = exec_msg )]
    tx = CreateTxOptions( msgs=tx, gas_prices="0.2uusd", gas_adjustment="1.2") # , denoms=["uusd"] )
    tx = terra_inst.wallet.create_and_sign_tx(tx)
    return terra_inst.terra.tx.broadcast(tx)


def execute_anchor_coins_fees(terra_inst, contract_ad, exec_msg, amt_to_send, gas_fee): 
    # Execute Anchor contract + send coins
    tx = MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=exec_msg,  coins=amt_to_send)
    tx = terra_inst.wallet.create_and_sign_tx([tx], fee=StdFee(gas_fee, str(gas_fee)+"uusd"))
    result = terra_inst.terra.tx.broadcast(tx)
    return result 

def execute_anchor_coins_no_fees(terra_inst, contract_ad, exec_msg, amt_to_send):
    # Execute Anchor contract + send coins
    tx = MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=exec_msg,  coins=amt_to_send)
    tx = terra_inst.wallet.create_and_sign_tx([tx])
    result = terra_inst.terra.tx.broadcast(tx)
    return result


def execute_anchor_coins_no_fees_update(terra_inst, contract_ad, exec_msg, amt_to_send):
    # Execute Anchor contract + send coins
    tx = [MsgExecuteContract( sender = terra_inst.wallet.key.acc_address, contract = contract_ad, execute_msg = exec_msg, coins = amt_to_send  )]
    tx = CreateTxOptions( msgs=tx, gas_prices="0.2uusd", gas_adjustment="1.2") # , denoms=["uusd"] )
    tx = terra_inst.wallet.create_and_sign_tx(tx)
    return terra_inst.terra.tx.broadcast(tx)

def create_tx_fee(terra_inst, contract_ad, execute_msg, gas_req, gas_amt): # Need to BROADCAST??
    send_coins = Coins()
    execute = MsgExecuteContract( sender=terra_inst.wallet.key.acc_address, contract=contract_ad, execute_msg=execute_msg,  coins=send_coins)
    return terra_inst.wallet.create_and_sign_tx([execute]) #, fee=StdFee(gas_req, gas_amt))

def broadcast_tx_fee(terra_inst, created_tx):
    return terra_inst.terra.tx.broadcast(created_tx)

def execute_anchor_fee(terra_inst, contract_ad, execute_msg, gas_req, gas_amt):
    created_tx = create_tx_fee(terra_inst, contract_ad, execute_msg, gas_req, gas_amt)
    return broadcast_tx_fee(terra_inst, created_tx_fee)

def get_terraswap_bLuna_to_Luna_price_testnet(input_amt):
    # Bluna to Luna. See old_files for reverse price.
    terra_swap_endpoint = 'https://fcd.terra.dev'
    contract_address = 'terra1jxazgm67et0ce260kvrpfv50acuushpjsz2y0p'
    query_msg = '{"simulation":{"offer_asset":{"amount":'+"\""+str(input_amt)+"\""+',"info":{"token":{"contract_addr":"terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp"}}}}}'
    resp = requests.get(terra_swap_endpoint + '/wasm/contracts/' + contract_address + '/store', params={'query_msg': query_msg}).json()
    return int(resp['result']['return_amount'])/input_amt

def get_terraswap_Luna_to_UST_price_testnet(input_amt):
    # Get the price for LUNA ---> UST (Sell).
    terra_swap_endpoint = 'https://fcd.terra.dev'
    contract_address = 'terra1tndcaqxkpc5ce9qee5ggqf430mr2z3pefe5wj6'
    query_msg = '{"simulation":{"offer_asset":{"amount":' + "\"" +str(input_amt) + "\"" +',"info":{"native_token":{"denom":"uluna"}}}}}'
    resp = requests.get(terra_swap_endpoint + '/wasm/contracts/' + contract_address + '/store', params={'query_msg': query_msg}).json()
    return int(resp['result']['return_amount'])/input_amt


def get_bLuna_to_Luna_to_UST_profitable(wallet_exposure, terraswap_fee, terra_ust_luna_swap_fee, gas_fee_uusd, denom_uluna, denom_bluna):
    # Is the effective bLuna->UST price enough to cover gas?
    # neglects slippage?
    if wallet_exposure['bLuna']==0:
        exchange_rate_bluna_to_luna = 1
    else:
        exchange_rate_bluna_to_luna = get_terraswap_bLuna_to_Luna_price_testnet(wallet_exposure['bLuna']) 
    
    if wallet_exposure['uLuna']==0: 
        exchange_rate_luna_to_ust = 1
    else:
        exchange_rate_luna_to_ust = get_terraswap_Luna_to_UST_price_testnet(wallet_exposure['bLuna'] + wallet_exposure['uLuna']) # Rough estimate
        
    amt_luna_from_bluna = (wallet_exposure['bLuna']/denom_bluna)*exchange_rate_bluna_to_luna*(1-terraswap_fee)
    print(amt_luna_from_bluna + wallet_exposure['uLuna'])
    amt_ust_from_luna = (amt_luna_from_bluna + wallet_exposure['uLuna']/denom_uluna)*exchange_rate_luna_to_ust*(1- terraswap_fee - terra_ust_luna_swap_fee)
    print(amt_ust_from_luna)
    pnl = amt_ust_from_luna - 2*gas_fee_uusd
    return pnl


def qry_active_bids(terra_inst, token):
    qry_msg = {  "bids_by_user": {    "collateral_token": token, "bidder": terra_inst.wallet.key.acc_address}} # Start_after, and limit params
    return get_query(terra_inst, terra_inst.mmLiquidation, qry_msg)['bids']


def qry_active_bLuna_bids(terra_inst, token_bLuna_whitelist):
    qry_msg = {  "bids_by_user": {    "collateral_token": token_bLuna_whitelist, "bidder": terra_inst.wallet.key.acc_address}} # Start_after, and limit params
    return get_query(terra_inst, terra_inst.mmLiquidation, qry_msg)['bids']

def qry_active_bETH_bids(terra_inst, token_bETH_whitelist):
    qry_msg = {  "bids_by_user": {    "collateral_token": token_bETH_whitelist, "bidder": terra_inst.wallet.key.acc_address}} # Start_after, and limit params
    return get_query(terra_inst, terra_inst.mmLiquidation, qry_msg)['bids']


def get_active_bids_ids(terra_inst, token_bLuna_whitelist):
    qry_msg = {  "bids_by_user": {    "collateral_token": token_bLuna_whitelist, "bidder": terra_inst.wallet.key.acc_address}} # Start_after, and limit params
    qry = get_query(terra_inst, terra_inst.mmLiquidation, qry_msg)['bids']
    ids = []
    for k in qry:
        ids.append(k['idx'])
    return ids # print("ID of all my bids",ids)


def qry_claimable_liq(terra_inst, token):
    qry_msg = {"bids_by_user": { "collateral_token": token, "bidder": terra_inst.wallet.key.acc_address }}
    resp =  get_query(terra_inst, terra_inst.mmLiquidation, qry_msg)['bids']
    tmp = {}
    for k in resp:
        tmp[k['idx']] = k['pending_liquidated_collateral']
    return tmp

def sum_bidbook_liq(bids_by_user_bLuna):
    tmp = 0
    for k in bids_by_user_bLuna:
        tmp += int(k['amount'])
    return tmp
    

def execute_submit_bLuna_bid(terra_inst, token_bLuna_whitelist, amt_uusd, prem_slot, gas_fee):
    exec_msg = { "submit_bid": {"collateral_token": str(token_bLuna_whitelist), "premium_slot": int(prem_slot) } }
    print(terra_inst.mmLiquidation)
    return    execute_anchor_coins_fees(terra_inst, terra_inst.mmLiquidation, exec_msg, amt_uusd, gas_fee)

def execute_submit_bLuna_bid_no_fees(terra_inst, token_bLuna_whitelist, amt_uusd, prem_slot):
    exec_msg = { "submit_bid": {"collateral_token": str(token_bLuna_whitelist), "premium_slot": int(prem_slot) } }
    return    execute_anchor_coins_no_fees(terra_inst, terra_inst.mmLiquidation, exec_msg, amt_uusd)

def execute_submit_bLuna_bid_no_fees_update(terra_inst, token_bLuna_whitelist, amt_uusd, prem_slot):
    exec_msg = { "submit_bid": {"collateral_token": str(token_bLuna_whitelist), "premium_slot": int(prem_slot) } }
    return    execute_anchor_coins_no_fees_update(terra_inst, terra_inst.mmLiquidation, exec_msg, amt_uusd)

def execute_submit_bETH_bid(terra_inst, token_bETH_whitelist, amt_uusd, prem_slot, gas_fee):
    exec_msg = { "submit_bid": {"collateral_token": str(token_bETH_whitelist), "premium_slot": int(prem_slot) } }
    return    execute_anchor_coins_fees(terra_inst, terra_inst.mmLiquidation, exec_msg, amt_uusd, gas_fee)

def execute_submit_bETH_bid_no_fees_update(terra_inst, token_bETH_whitelist, amt_uusd, prem_slot):
    exec_msg = { "submit_bid": {"collateral_token": str(token_bETH_whitelist), "premium_slot": int(prem_slot) } }
    return    execute_anchor_coins_no_fees_update(terra_inst, terra_inst.mmLiquidation, exec_msg, amt_uusd)

def execute_submit_btoken_bid_no_fees_update(terra_inst, token, amt_uusd, prem_slot):
    exec_msg = { "submit_bid": {"collateral_token": str(token), "premium_slot": int(prem_slot) } }
    return    execute_anchor_coins_no_fees_update(terra_inst, terra_inst.mmLiquidation, exec_msg, amt_uusd)


def get_amt_uusd_to_bid_bLuna(wallet_bidbook_max_bLUNA, where_ust, wallet_min_ust, denom_uusd):
    amt_uusd_to_bid = int(max(wallet_bidbook_max_bLUNA*denom_uusd - where_ust['bidbook_bLuna']*denom_uusd, 0 ))
    amt_uusd_to_bid = int(min(amt_uusd_to_bid, where_ust['wallet']*denom_uusd-wallet_min_ust*denom_uusd))
    return [str(amt_uusd_to_bid) + "uusd", amt_uusd_to_bid]

def get_amt_uusd_to_bid_bETH(wallet_bidbook_max_bETH, where_ust, wallet_min_ust, denom_uusd):
    amt_uusd_to_bid = int(max(wallet_bidbook_max_bETH*denom_uusd - where_ust['bidbook_bETH']*denom_uusd, 0 ))
    amt_uusd_to_bid = int(min(amt_uusd_to_bid, where_ust['wallet']*denom_uusd-wallet_min_ust*denom_uusd))
    return [str(amt_uusd_to_bid) + "uusd", amt_uusd_to_bid]

def bool_place_bid_bLUNA(where_ust, wallet_exposure, wallet_min_ust, wallet_bidbook_max, exposure_bluna_swap_threshold, exposure_uluna_swap_threshold,denom_uluna,denom_bluna, amt_uusd_to_bid_bLuna_int, min_bid, denom_uusd):
    # Don't place bid if currently exposed
    # Don't place bid if less than 100 ust
    # Don't place bid if there is claimable liq
    # Otherwise, bid 10UST
    if(where_ust['wallet'] <= wallet_min_ust):
        print("Not Placing [bLUNA] Bid : Not enough money in wallet")
        return False
    if(where_ust['bidbook_bLuna'] >= wallet_bidbook_max):
        print("Not Placing [bLUNA] Bid : Too much currently up for bid")
        return False
    if(wallet_exposure['bLuna'] >= exposure_bluna_swap_threshold*denom_bluna):
        print("Not Placing [bLUNA] Bid : Overexposed in bLuna")
        return False
    if(wallet_exposure['uLuna'] >= exposure_uluna_swap_threshold*denom_uluna):
        print("Not Placing [bLUNA] Bid : Overexposed in uLuna")
        return False
    if(amt_uusd_to_bid_bLuna_int < min_bid or amt_uusd_to_bid_bLuna_int > wallet_bidbook_max*denom_uusd):
        print("Not Places [bLuna] Bid : Bid_amt is outside (min,max)", min_bid, amt_uusd_to_bid_bLuna_int, wallet_bidbook_max)       
        return False        
    return True

def bool_place_bid_bETH(where_ust, wallet_exposure, wallet_min_ust, wallet_bidbook_max, exposure_beth_swap_threshold,denom_beth, amt_uusd_to_bid_bETH_int, min_bid, denom_uusd):
    # Don't place bid if currently exposed
    # Don't place bid if less than 100 ust
    # Don't place bid if there is claimable liq
    # Otherwise, bid 10UST
    if(where_ust['wallet'] < wallet_min_ust):
        print("Not Placing [bETH] Bid : Not enough money in wallet")
        return False
    if(where_ust['bidbook_bETH'] >= wallet_bidbook_max):
        print("Not Placing [bETH] Bid : Too much currently up for bid")
        return False
    if(wallet_exposure['bETH'] >= exposure_beth_swap_threshold*denom_beth):
        print("Not Placing [bETH] Bid : Overexposed in bETH")
        return False        
    if(amt_uusd_to_bid_bETH_int < min_bid or amt_uusd_to_bid_bETH_int > wallet_bidbook_max*denom_uusd):
        print("Not Places [bETH] Bid : Bid_amt is outside (min,max)", min_bid, amt_uusd_to_bid_bETH_int, wallet_bidbook_max*denom_uusd)    
        return False
    return True

def get_prem_slot_to_bid_bLuna(prem_to_bid):
    return prem_to_bid

def get_prem_slot_to_bid_bETH(prem_to_bid):
    return prem_to_bid


# Claim Liq
def execute_claim_all_liquidation(terra_inst, token_bLuna_whitelist, gas_fee):
    exec_msg = {"claim_liquidations": {    "collateral_token": token_bLuna_whitelist}} #, "bids_idx": bid_ids_to_activate  }} # bids_idx Optional
    return execute_anchor_fees(terra_inst, terra_inst.mmLiquidation, exec_msg, gas_fee)

def execute_claim_all_liquidation_no_fee(terra_inst, token_bLuna_whitelist):
    exec_msg = {"claim_liquidations": {    "collateral_token": token_bLuna_whitelist}} #, "bids_idx": bid_ids_to_activate  }} # bids_idx Optional
    return execute_anchor(terra_inst, terra_inst.mmLiquidation, exec_msg)

def execute_claim_all_liquidation_no_fees_update(terra_inst, token_bLuna_whitelist):
    exec_msg = {"claim_liquidations": {    "collateral_token": token_bLuna_whitelist}} #, "bids_idx": bid_ids_to_activate  }} # bids_idx Optional
    return execute_anchor_no_fees_update(terra_inst, terra_inst.mmLiquidation, exec_msg)


# Activate Bids
def execute_activate_bids(terra_inst, token_bLuna_whitelist, bids_that_can_be_activated, gas_fee):
    exec_msg = { "activate_bids": {  "collateral_token": token_bLuna_whitelist , "bids_idx": bids_that_can_be_activated } } # Just activate all?
    return execute_anchor_fees(terra_inst, terra_inst.mmLiquidation, exec_msg, gas_fee) 

def execute_activate_all_bids(terra_inst, token_bLuna_whitelist, gas_fee):
    exec_msg = { "activate_bids": {  "collateral_token": token_bLuna_whitelist } } 
    return execute_anchor_fees(terra_inst, terra_inst.mmLiquidation, exec_msg, gas_fee)

def execute_activate_all_bids_no_fee(terra_inst, token_bLuna_whitelist):
    exec_msg = { "activate_bids": {  "collateral_token": token_bLuna_whitelist } }
    return execute_anchor(terra_inst, terra_inst.mmLiquidation, exec_msg)

def execute_activate_all_bids_no_fees_update(terra_inst, token_bLuna_whitelist):
    exec_msg = { "activate_bids": {  "collateral_token": token_bLuna_whitelist } }
    return execute_anchor_no_fees_update(terra_inst, terra_inst.mmLiquidation, exec_msg)


# Retract Bids
def execute_retract_bid(terra_inst, bid_idx, gas_fee):
    exec_msg = {  "retract_bid": {    "bid_idx": bid_idx}}
    return execute_anchor_fees(terra_inst, terra_inst.mmLiquidation, exec_msg, gas_fee)   

def execute_retract_bid_no_fees(terra_inst, bid_idx):
    exec_msg = {  "retract_bid": {    "bid_idx": bid_idx}}
    return execute_anchor_no_fees(terra_inst, terra_inst.mmLiquidation, exec_msg)

def execute_retract_bid_no_fees_update(terra_inst, bid_idx):
    exec_msg = {  "retract_bid": {    "bid_idx": bid_idx}}
    return execute_anchor_no_fees_update(terra_inst, terra_inst.mmLiquidation, exec_msg)


#############
# GAS
#############

def get_gas_used(resp):
    
    if(resp.height==0):
        return resp.gas_used
    elif(resp.height>0):
        return resp.gas_wanted
    else:
        print("GET_GAS_USED ERROR")
        import sys
        sys.exit()




###########
# LIGHT BOT
###########

def update_active_inactive_bids(terra_inst, token):
        # Query all bids
        bids_by_user = qry_active_bLuna_bids(terra_inst, token)
        internal_are_bids_active = {}
        bids_that_can_be_activated = []
        bids_that_cant_be_activated = []
        time_now = 0 ##########???

        # Update internal internal_are_bids_active ledger
        for bid in bids_by_user:
            # Check if bids are active nor not
            if(bid['wait_end']==None):
                internal_are_bids_active[bid['idx']] = "active"
            else:
                internal_are_bids_active[bid['idx']] = "in_active"
                # Store whether the bid can be activated, or if its not time yet
                if(int(bid['wait_end'])<time_now):
                    bids_that_can_be_activated.append(bid['idx'])
                else:
                     bids_that_cant_be_activated.append(bid['idx'])

        return bids_that_can_be_activated, bids_that_cant_be_activated, internal_are_bids_active

def can_bid_be_activated(terra_inst, token, logging):
    bids_by_user = qry_active_bids(terra_inst, token)
    print(bids_by_user)
    if bids_by_user==[]:
        return 0
    for bid in bids_by_user:
        #if(bid['wait_end']==None):
        #    return 1
        if(int(time.time())>int(bid['wait_end'])):
                print("Can the bid be activated?", int(time.time())>int(bid['wait_end']), int(time.time()), int(bid['wait_end']))
                logging.info("Can the bid be activated? "+ str(int(time.time())>int(bid['wait_end']))+ " " +str(time.time())+ ", " + str(bid['wait_end']))
                return 1
        else:
                print("Can the bid be activated?", int(time.time())>int(bid['wait_end']), int(time.time()), int(bid['wait_end']))
                logging.info("Can the bid be activated? "+ str(int(time.time())>int(bid['wait_end']))+ " " +str(time.time())+", " + str(bid['wait_end']))
                return 0


def sleep_until_can_activate(terra_inst, token, logging):
    bids_by_user = qry_active_bids(terra_inst, token)
    bid = bids_by_user[0]
    print("Sleep until activate times :", int(time.time()), int(bid['wait_end']))
    sleep_time = max(-int(time.time())+int(bid['wait_end']),0)
    print("Sleeping for " + str(sleep_time)+"s, until bid can be activated")
    logging.info("Sleeping for " + str(sleep_time)+"s, until bid can be activated")
    sleep(sleep_time)


def can_claim_liq_on_bid_bLuna(terra_inst, token, logging, param):
    claimable_liq = qry_claimable_liq(terra_inst, token)        
    sum_claimable_liq = sum([int(k) for k in claimable_liq.values()])
    if (sum_claimable_liq>0):
        return 1, sum_claimable_liq
    else:
        return 0, sum_claimable_liq

def can_claim_liq_on_bid_bETH(terra_inst, token, logging, param):
    claimable_liq = qry_claimable_liq(terra_inst, token)
    sum_claimable_liq = sum([int(k) for k in claimable_liq.values()])
    if (sum_claimable_liq>0):
        print("Can claim liq since above threshold,", sum_claimable_liq,">", (param.claim_swap_threshold_bETH)*(param.denom_bETH))
        return 1, sum_claimable_liq
    else:
        print("Can't claim liq since below threshold,", sum_claimable_liq,"<", (param.claim_swap_threshold_bETH)*(param.denom_bETH))
        return 0, sum_claimable_liq




def does_bid_need_activated(terra_inst, token, logging):    
    bids_by_user = qry_active_bids(terra_inst, token)  
    if(bids_by_user == []):        
        print("Not Activating bid since bids_by_user==[],",bids_by_user)
        logging.info("Not Activating bid since bids_by_user==[],"+str(bids_by_user))
        return 0
    bid = bids_by_user[0]
    if(bid['wait_end']==None):
            print("Not Activating bid since wait_end==None,",bid['wait_end'])
            logging.info("Not Activating bid since wait_end==None,"+str(bid['wait_end']))
            return 0
    else:
            return 1

def bid_not_yet_submitted_bLuna(terra_inst,bid_needs_retracting, logging):
    if(bid_needs_retracting==0):
        wallet_exposure, wallet_ust = update_wallet_exposure(terra_inst)
        #print("     Wallet Exposure, wallet_ust : ", wallet_exposure, wallet_ust)
        if((wallet_ust['bidbook_bLuna']==0) and (wallet_exposure['bLuna']==0) and (wallet_exposure['uLuna']==0)):
            print("Going to submit bit, because no bid has been submitted")
            logging.info("Going to submit bit, because no bid has been submitted")
            return 1
        else:
            print("Not submitting bid since wallet_ust!=0, ",wallet_ust['bidbook_bLuna'])
            logging.info("Not submitting bid since wallet_ust!=0, "+str(wallet_ust['bidbook_bLuna']))
            return 0
    else:
        print("Not submitting bid since bid_needs_retracting==1,",bid_needs_retracting)
        logging.info("Not submitting bid since bid_needs_retracting==0"+str(bid_needs_retracting))
        return 0

def bid_not_yet_submitted_bETH(terra_inst,bid_needs_retracting, logging):
    if(bid_needs_retracting==0):
        wallet_exposure, wallet_ust = update_wallet_exposure(terra_inst)
        if((wallet_ust['bidbook_bETH']==0) and (wallet_exposure['bETH']==0)): 
            print("Going to submit bit, because no bid has been submitted")
            logging.info("Going to submit bit, because no bid has been submitted")
            return 1
        else:
            print("Not submitting bid since wallet_ust!=0, ",wallet_ust['bidbook_bETH'])
            logging.info("Not submitting bid since wallet_ust!=0, "+str(wallet_ust['bidbook_bETH']))
            return 0
    else:
        print("Not submitting bid since bid_needs_retracting==1,",bid_needs_retracting)
        logging.info("Not submitting bid since bid_needs_retracting==0"+str(bid_needs_retracting))
        return 0


def can_swap_btoken(terra_inst, wallet_exposure_key, logging):
    wallet_exposure, wallet_ust = update_wallet_exposure(terra_inst)
    #print("     Wallet Exposure, wallet_ust : ", wallet_exposure, wallet_ust)
    if(wallet_exposure[wallet_exposure_key]>0):
        print("Can swap %s"%(wallet_exposure_key))
        return 1
    else:
        print("Can't swap %s since there is none in wallet, wallet_exposure[%s]"%(wallet_exposure_key,wallet_exposure_key),wallet_exposure[wallet_exposure_key])
        logging.info("Can't swap %s since there is none in wallet, wallet_exposure[%s]"%(wallet_exposure_key,wallet_exposure_key)+str(wallet_exposure[wallet_exposure_key]))
        return 0
    

def light_get_bid_amt_bETH(terra_inst, wallet_ust, param):
    amt_left_after = wallet_ust['wallet'] - param.amt_uusd_to_bid_bETH    
    if(amt_left_after> param.wallet_min_ust):
        return int(param.amt_uusd_to_bid_bETH*param.denom_bETH)
    else:
        return 0

def light_get_bid_amt_bLuna(terra_inst, wallet_ust, param):
    amt_left_after = wallet_ust['wallet'] - param.amt_uusd_to_bid_bLuna
    if(amt_left_after> param.wallet_min_ust):
        return int(param.amt_uusd_to_bid_bLuna*param.denom_bluna)
    else:
        return 0 


def bid_needs_retracting(terra_inst, token_ad,  bid_needs_retracting, logging):
    if(bid_needs_retracting==1):
        bids_by_user = qry_active_bids(terra_inst, token_ad)
        if(bids_by_user==[]):
            print("Not retracting bid because there are none, bids_by_user=",bids_by_user)
            logging.info("Not retracting bid because there are none, bids_by_user="+str(bids_by_user))
            return 0
        else:
            print("Retracting bid, bids_by_user=",bids_by_user)
            logging.info("Retracting bid, bids_by_user="+str(bids_by_user)+", bid_needs_retracting="+str(bid_needs_retracting))
            return 1
    else:
        print("Not retracting bid, bid_needs_retracting="+str(bid_needs_retracting))
        logging.info("Not retracting bid, bid_needs_retracting="+str(bid_needs_retracting))        
        return 0
    

def light_get_gas_spent(resp, param):
    gas_fee = (param.gas_price*int(resp.gas_used))/(param.denom_uusd)
    return gas_fee

# Log pnl
def logger_update_pnl_df(NETWORK, gas, coins, action, log_token, wallet_ust, wallet_exposure, tx_hash):
    # Logger file!
    today = date.today()
    today_date = today.strftime("%d_%m_%Y")
    log_filename = 'BotFiles/Logs/Log_Light_'+log_token+'_'+today_date+'__'+NETWORK+'_PnL.csv'

    if (type(coins)==str): 
        #coins[-4:] == "uusd":
        coins = int(coins[:-5])
    data = [[Timestamp.now(), gas, int(coins), action,  wallet_ust['wallet'], wallet_ust['bidbook_bLuna'], wallet_ust['bidbook_bETH'], wallet_exposure['bLuna'], wallet_exposure['uLuna'], wallet_exposure['bETH'], tx_hash]]
    df = DataFrame(data,columns=['Time','Gas','Coins','Action','wallet_ust','wallet_ust_bidbook_bLuna','wallet_ust_bidbook_bETH','wallet_exp_bLuna','wallet_exp_uLuna','wallet_exp_bETH','tx_hash'])
    df.to_csv(log_filename, mode='a', header=not exists(log_filename))


def light_error_check(resp, logging):
    if( 'insufficient funds' in resp.raw_log):
        print("ERROR : insufficient funds, shutting down bot. Risk of being highly exposed.")
        logging.warning("Insufficient Funds : " + str(resp))
        import sys
        sys.exit()
    return 0
        
        


# light weight bot transactions


def light_submitbid(NETWORK, terra_inst, token_to_bid , bid_amt_int_denom, logging, param, premium_slot, log_token):
    try:
        amt_to_bid_str = str(bid_amt_int_denom)+"uusd" 
        resp = execute_submit_btoken_bid_no_fees_update(terra_inst, token_to_bid, amt_to_bid_str, premium_slot); 
        print("Submit bid resp :",resp);
        logging.info("Submit bETH bid : "+str(resp))
        
        # Error Check
        light_error_check(resp, logging)
        #print("Sleep "+str(param.sleep_time_tx));   sleep(param.sleep_time_tx);  logging.info("Submit bid, Sleep "+str(param.sleep_time_tx))

        # Update wallet
        gas_spent = light_get_gas_spent(resp, param)        
        wallet_exposure, wallet_ust = update_wallet_exposure(terra_inst)
        logger_update_pnl_df(NETWORK, gas_spent, amt_to_bid_str, 'Submit', log_token, wallet_ust, wallet_exposure, resp.txhash)

    except Exception as e:
        print("Submit bid error : ", e)
        logging.error("Swap error : "+str(e))
        light_error_check(e, logging)
                                

def light_retractbid(NETWORK,terra_inst, bid, logging, param, log_token):
    try:
        resp = execute_retract_bid_no_fees_update(terra_inst, bid['idx']);
        print("Retract bid resp :",resp);
        logging.info("Retract bid : "+str(resp))
        
        # Error Check
        light_error_check(resp, logging)
        #print("Sleep "+str(param.sleep_time_tx));        sleep(param.sleep_time_tx);        logging.info("Retract bid, Sleep "+str(param.sleep_time_tx))

        raw_log = literal_eval(resp.raw_log)
        ust_retracted = raw_log[0]["events"][0]["attributes"][-1]["value"]
        gas_spent = light_get_gas_spent(resp, param)

        # Update wallet
        wallet_exposure, wallet_ust = update_wallet_exposure(terra_inst)
        logger_update_pnl_df(NETWORK, gas_spent,  ust_retracted, 'Retract', log_token, wallet_ust, wallet_exposure , resp.txhash)

    except Exception as e:
        logging.error("Swap error : "+str(e))
        print(e)
        light_error_check(e, logging)

def light_activatebid(NETWORK,terra_inst,token, logging, param, log_token):
    try:
        resp= execute_activate_all_bids_no_fees_update(terra_inst, token);
        print("Activate bid resp",resp);
        logging.info("Activate bid:"+str(resp))
        
        # Error Check
        light_error_check(resp, logging)
        #print("Sleep "+str(param.sleep_time_tx));      sleep(param.sleep_time_tx);    logging.info("Activate bid, Sleep "+str(param.sleep_time_tx))
        gas_spent = light_get_gas_spent(resp, param)
            
        # Update wallet
        wallet_exposure, wallet_ust = update_wallet_exposure(terra_inst)
        logger_update_pnl_df(NETWORK, gas_spent, 0, 'Activate', log_token, wallet_ust, wallet_exposure, resp.txhash)

    except Exception as e:
        logging.error("Swap error : "+str(e))
        print(e)
        light_error_check(e, logging)
        

def light_claimliq(NETWORK,terra_inst, token, logging, param, log_token):
    try:
        resp = execute_claim_all_liquidation_no_fees_update(terra_inst, token);
        print("Claim Liq resp",resp);
        logging.info("Claim liq:"+str(resp))
        
        # Error Check
        light_error_check(resp, logging)
        #print("Sleep "+str(param.sleep_time_tx));        sleep(param.sleep_time_tx);        logging.info("Claim Liq, Sleep "+str(param.sleep_time_tx))

        gas_spent = light_get_gas_spent(resp, param)

        # Update wallet
        wallet_exposure, wallet_ust = update_wallet_exposure(terra_inst)
        logger_update_pnl_df(NETWORK, gas_spent, 0, 'Claim', log_token, wallet_ust, wallet_exposure, resp.txhash)


    except Exception as e:
        logging.error("Swap error : "+str(e))
        print(e)
        light_error_check(e, logging)
        
def light_swapbid_bETH_UST(NETWORK,terra_inst, wallet_exposure, logging, param, log_token):
    try:
        amt_to_swap = wallet_exposure['bETH']
        resp = execute_swap_bETH_for_UST_testnet_no_fees_update(terra_inst, wallet_exposure);
        logging.info("Swap [bETH]"+str(resp))        
        print("Swap [bETH] resp", resp);
        # Error Check
        light_error_check(resp, logging)
        #print("Sleep "+str(param.sleep_time_tx));   sleep(param.sleep_time_tx);  logging.info("Swap [bETH], Sleep "+str(param.sleep_time_tx))

        # Update wallet
        gas_spent = light_get_gas_spent(resp, param)
        wallet_exposure, wallet_ust = update_wallet_exposure(terra_inst)
        logger_update_pnl_df(NETWORK, gas_spent, amt_to_swap, 'Swap [bETH]', log_token, wallet_ust, wallet_exposure, resp.txhash)

    except Exception as e:
        logging.error("Swap [bETH] error : "+str(e))
        print(e)
        light_error_check(e, logging)


def light_swapbid_bLuna_Luna(NETWORK,terra_inst, wallet_exposure, logging, param, log_token):
    try:
        amt_to_swp = wallet_exposure['bLuna']
        resp = execute_swap_bLuna_for_Luna_testnet_no_fees_update(terra_inst, wallet_exposure);
        print("Swap [bLuna] resp", resp);
        logging.info("Swap [bLuna]"+str(resp))
        # Error Check
        light_error_check(resp, logging)
        #print("Sleep "+str(param.sleep_time_tx)); sleep(param.sleep_time_tx); logging.info("Swap [bLuna], Sleep "+str(param.sleep_time_tx))
        gas_spent = light_get_gas_spent(resp, param)

        # Update wallet
        wallet_exposure, wallet_ust = update_wallet_exposure(terra_inst)
        logger_update_pnl_df(NETWORK, gas_spent,  amt_to_swp, 'Swap [bLuna]', log_token, wallet_ust, wallet_exposure, resp.txhash)
    except Exception as e:
        logging.error("Swap [bLuna] error : "+str(e))
        print(e)
        light_error_check(e, logging)

def light_swapbid_uLuna_UST(NETWORK,terra_inst, wallet_exposure, logging, param, log_token):
    try:
        amt_to_swap = wallet_exposure['uLuna']
        resp = execute_swap_Luna_for_UST_testnet_no_fees_update(terra_inst, wallet_exposure);
        print("Swap [uLuna] resp", resp);
        logging.info("Swap [uLuna] "+str(resp))

        # Error Check
        light_error_check(resp, logging)
        # Sleep + log
        #print("Sleep "+str(param.sleep_time_tx));sleep(param.sleep_time_tx);logging.info("Swap [uLuna], Sleep "+str(param.sleep_time_tx))
        gas_spent = light_get_gas_spent(resp, param)

        # Update wallet + log
        logging.info("Swap [uLuna] "+str(resp))
        wallet_exposure, wallet_ust = update_wallet_exposure(terra_inst)
        logger_update_pnl_df(NETWORK, gas_spent, amt_to_swap, 'Swap [uLuna]', log_token, wallet_ust, wallet_exposure, resp.txhash)

    except Exception as e:
        logging.error("Swap [uLuna] error : "+str(e))
        print(e)
        light_error_check(e, logging)


##

import subprocess
def run_again(script_name):
    subprocess.call(["python3", script_name])

