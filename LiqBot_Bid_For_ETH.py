# This bot submits bETH bids for liquidations on Anchors debt system
from sys import path
path.insert(1, './BotFile/Config/')
path.insert(1, './HelperFunctions/')
path.insert(1,'./BotFiles/Parameters')
import liqbot_helper as hlpr    
from gas_fee_simulation_helper import get_gas_fees   
import logger_init
from time import sleep
import logging
from datetime import date
from os.path import exists
import json


###################
# CONFIG
###################
# Config
NETWORK = 'MAINNET'
wallet_seed =  ''
terra_inst =  hlpr.Terra(NETWORK, wallet_seed)

################################
# 0. Initialisation + Parameters
################################

# Parameters
bid_needs_retracting    = 0
import Parameters_Light as param

# Collect wallet info
wallet_exposure, wallet_ust = hlpr.update_wallet_exposure(terra_inst)
print(wallet_exposure, wallet_ust)


# Set up log_base
log_base = logger_init.logger_init(NETWORK, 'bETH')
logger_init.logger_init_pnl_df(NETWORK, wallet_ust, wallet_exposure, param, 'bETH')

# Main loop
while True:
    print("\n############### STARTING NEW LOOP ################## \n ")
    log_base.info("------------ NEW LOOP -----------")
         
    # Submit bid
    bid_not_yet_submitted = hlpr.bid_not_yet_submitted_bETH(terra_inst, bid_needs_retracting, log_base)
    if bid_not_yet_submitted:
            bid_amt_int_denom = hlpr.light_get_bid_amt_bETH(terra_inst,wallet_ust, param)
            if(bid_amt_int_denom > 0):
                hlpr.light_submitbid(NETWORK, terra_inst, terra_inst.bETHToken , bid_amt_int_denom, log_base, param, param.prem_slot_to_bid_bETH,'bETH')
                wallet_exposure, wallet_ust = hlpr.update_wallet_exposure(terra_inst)
            else:
                print("Not submitted bid since amt==0", bid_amt_int_denom)
                log_base.info("Not submitted bid since amt==0"+str(bid_amt_int_denom))

    # Retract bid
    bid_needs_retracting = hlpr.bid_needs_retracting(terra_inst, terra_inst.bETHToken, bid_needs_retracting, log_base)
    if bid_needs_retracting:
            bids_by_user = hlpr.qry_active_bids(terra_inst, terra_inst.bETHToken)
            for bid in bids_by_user:
                hlpr.light_retractbid(NETWORK, terra_inst, bid, log_base, param, 'bETH')
            wallet_exposure, wallet_ust = hlpr.update_wallet_exposure(terra_inst)

    # Activate bid
    does_bid_need_activated = hlpr.does_bid_need_activated(terra_inst, terra_inst.bETHToken, log_base)
    if( does_bid_need_activated and (bid_needs_retracting==0) ):
        if hlpr.can_bid_be_activated(terra_inst, terra_inst.bETHToken, log_base):
             hlpr.light_activatebid(NETWORK, terra_inst, terra_inst.bETHToken , log_base, param, 'bETH')
             wallet_exposure, wallet_ust = hlpr.update_wallet_exposure(terra_inst)
        else:
             hlpr.sleep_until_can_activate(terra_inst, terra_inst.bLunaToken, log_base);

    # Claim Liq
    can_claim_liq, sum_claimable_liq = hlpr.can_claim_liq_on_bid_bETH(terra_inst, terra_inst.bETHToken, log_base, param)
    if can_claim_liq and (bid_needs_retracting==0):
        hlpr.light_claimliq(NETWORK, terra_inst, terra_inst.bETHToken, log_base, param, 'bETH')
        wallet_exposure, wallet_ust = hlpr.update_wallet_exposure(terra_inst)
    else:
        print("Can't claim Liq since sum is "+str(sum_claimable_liq))
        if(bid_not_yet_submitted==0 and bid_needs_retracting==0 and does_bid_need_activated==0 and hlpr.can_swap_btoken(terra_inst, 'bETH', log_base)==0):
            print("Waiting for bid to get hit, so going to sleep for 60s"); log_base.info("Waiting for bid to get hit, so going to sleep for 60s");sleep(60);
                        
           
    # Swap bETH for UST
    can_swap_btoken = hlpr.can_swap_btoken(terra_inst, 'bETH' ,log_base)
    if( (can_swap_btoken==1) and (bid_needs_retracting==0) ):
            hlpr.light_swapbid_bETH_UST(NETWORK, terra_inst, wallet_exposure, log_base, param, 'bETH')
            wallet_exposure, wallet_ust = hlpr.update_wallet_exposure(terra_inst)
        

    











