# This bot submits bETH bids for liquidations on Anchors debt system
from sys import path
path.insert(1, './BotFile/Config/')
path.insert(1, './HelperFunctions/')
path.insert(1,'./BotFiles/Parameters')
import liqbot_helper as hlpr    # my file
from gas_fee_simulation_helper import get_gas_fees   # my file
import logger_init
from time import sleep
import logging
from datetime import date
from os.path import exists
import json
import time

print("Imports Complete")

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
need_to_swap_now = 0

import Parameters_Light as param

# Collect wallet info
start_time = time.time()
wallet_exposure, wallet_ust = hlpr.update_wallet_exposure(terra_inst)
print(wallet_exposure, wallet_ust)
end_time = time.time()
print("It takes %f seconds to update the wallet"%(end_time-start_time))


# Set up log_base (only if doesn't exist)
log_base = logger_init.logger_init(NETWORK, 'Luna')
logger_init.logger_init_pnl_df(NETWORK, wallet_ust, wallet_exposure, param, 'Luna')

# Main loop
while True:
    print("\n############### STARTING NEW LOOP ################## \n ")
    #log_base.info("------------ NEW LOOP -----------")

    start_time_loop = time.time()


    # Submit bid # Works
    bid_not_yet_submitted = hlpr.bid_not_yet_submitted_bLuna(terra_inst, bid_needs_retracting, log_base)
    if bid_not_yet_submitted :
            bid_amt_int_denom = hlpr.light_get_bid_amt_bLuna(terra_inst,wallet_ust, param)
            if(bid_amt_int_denom > 0):
                start_time = time.time()
                hlpr.light_submitbid(NETWORK, terra_inst, terra_inst.bLunaToken , bid_amt_int_denom, log_base, param, param.prem_slot_to_bid_bLuna, 'Luna')
                print("It takes %f seconds to Submit a bid wallet"%(time.time()-start_time))
            else:
                print("Not submitted bid since amt==0", bid_amt_int_denom)
                log_base.info("Not submitted bid since amt==0"+str(bid_amt_int_denom))
        
             
    # Retract bid   # Works
    bid_needs_retracting = hlpr.bid_needs_retracting(terra_inst, terra_inst.bLunaToken, bid_needs_retracting, log_base)
    if bid_needs_retracting :
            bids_by_user = hlpr.qry_active_bids(terra_inst, terra_inst.bLunaToken)
            for bid in bids_by_user:
                hlpr.light_retractbid(NETWORK, terra_inst, bid, log_base, param, 'Luna')

    # Activate bid  # Works
    does_bid_need_activated = hlpr.does_bid_need_activated(terra_inst, terra_inst.bLunaToken, log_base)
    if( does_bid_need_activated and (bid_needs_retracting==0) and (need_to_swap_now==0)):
        if hlpr.can_bid_be_activated(terra_inst, terra_inst.bLunaToken, log_base):
             hlpr.light_activatebid(NETWORK, terra_inst, terra_inst.bLunaToken , log_base, param, 'Luna')
        else:
             hlpr.sleep_until_can_activate(terra_inst, terra_inst.bLunaToken, log_base);



    # Claim Liq # Works # Only claim if get more than gas (->3*gas)
    can_claim_liq, sum_claimable_liq = hlpr.can_claim_liq_on_bid_bLuna(terra_inst, terra_inst.bLunaToken, log_base, param)
    if can_claim_liq and (bid_needs_retracting==0) :
        start_time = time.time()
        hlpr.light_claimliq(NETWORK, terra_inst, terra_inst.bLunaToken, log_base, param, 'Luna')
        print("It takes %f seconds to Submit a bid wallet"%(time.time()-start_time))
        need_to_swap_now = 1
    else:
        start_time = time.time()
        if(bid_not_yet_submitted==0 and bid_needs_retracting==0 and does_bid_need_activated==0 and hlpr.can_swap_btoken(terra_inst, 'bLuna', log_base)==0 and wallet_exposure['uLuna']==0):
            print("It takes %f seconds to check if can swap btoken"%(time.time()-start_time))
            print("Waiting for bid to get hit, so going to sleep for 10s"); sleep(10); # log_base.info("Waiting for bid to get hit, so going to sleep for 10s");sleep(10);
                        
            
    # Swap bLuna for Luna # Works   # Only claim if get more than gas (->3*gas)
    can_swap_btoken = hlpr.can_swap_btoken(terra_inst, 'bLuna' ,log_base)
    if( (can_swap_btoken==1) and (bid_needs_retracting==0) ) :
            start_time = time.time()
            hlpr.light_swapbid_bLuna_Luna(NETWORK, terra_inst, wallet_exposure, log_base, param, 'Luna')
            print("It takes %f seconds to Submit a bid wallet"%(time.time()-start_time))            

    # Swap Luna for UST # Works  # Only claim if get more than gas (->3*gas)
    can_swap_btoken = hlpr.can_swap_btoken(terra_inst, 'uLuna' ,log_base)
    if( (can_swap_btoken==1) and (bid_needs_retracting==0) ):
            start_time = time.time()
            hlpr.light_swapbid_uLuna_UST(NETWORK, terra_inst, wallet_exposure, log_base, param, 'Luna')
            print("It takes %f seconds to Submit a bid wallet"%(time.time()-start_time))            
            need_to_swap_now = 0
            
   
    # How long to finish the loop
    print("TICKTOCK -> It takes %f seconds to finish a single loop"%(time.time()-start_time_loop))
    

    










