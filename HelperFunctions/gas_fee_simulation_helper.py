
# Hacked the bot-file to simulate gas fees (although actually swaps on terraswap, so need luna, and bluna).

import liqbot_helper as hlpr
from time import sleep
import logging
from datetime import date
from os.path import exists
import json

def get_gas_fees(NETWORK ,gas_fee_filename, num_gas_fees):
    """
    gas_fee_filename : the location to try and read gas_fees from. Needs to be a dictionary of the different gas fees
    num_gas_fees : the number of items that need to be contained in the dictionary
    eg {'submit_bid': 211011, 'retract_bid': 236056, 'activate_bid': 209872, 'claim_liq': 814473, 'terraswap_bluna_luna': 968576, 'terraswap_luna_ust': 412280}
    Note: This is a gas intensive calculation! Do not run on mainnet
    """
    
    if(NETWORK!='TEST_MAINNET'):
        have_all_gas_fees = 0       
        # Try and load the file
        if exists(gas_fee_filename):
                with open(gas_fee_filename) as f:
                    gas_fee_data = f.read()
                    simulated_gas_fees = json.loads(gas_fee_data)
                    have_all_gas_fees = check_have_all_gas_fees(simulated_gas_fees)
        else:
           import sys
           print("ERROR : DONT HAVE GAS ESTIMATION FILE. SHUTTING BOT DOWN. TOO EXPENSIVE TO ESTIMATE ON MAINNET.")
           sys.exit() 

        # Return the dictionary if file was loaded correctly
        if have_all_gas_fees==0:
           import sys
           print("ERROR : DONT HAVE GAS ESTIMATION FILE. SHUTTING BOT DOWN.")
           sys.exit() 
        else:
            return simulated_gas_fees

    if(NETWORK=='TEST_MAINNET'):

        # Simualted gas fees
        have_all_gas_fees = 0
        while have_all_gas_fees == 0:
            if exists(gas_fee_filename):
                with open(gas_fee_filename) as f:
                    gas_fee_data = f.read()
                simulated_gas_fees = json.loads(gas_fee_data)
                have_all_gas_fees = check_have_all_gas_fees(num_gas_fees, simulated_gas_fees)
            else:
                try:
                    print("No Gas Estimation file. Going to try and create it.")
                    simulated_gas_fees = simulate_gas_fees(1)
                    print("simulated_gas_fees",simulated_gas_fees)
                    have_all_gas_fees = check_have_all_gas_fees(num_gas_fees, simulated_gas_fees)
                except:
                    print("... Trying to simulated gas fees, but failing ...")
        
        if have_all_gas_fees==1:
            json_data = json.dumps(simulated_gas_fees)
            f = open(gas_fee_filename,"w")
            f.write(json_data)
            f.close()
        return simulated_gas_fees


def check_have_all_gas_fees(num_gas_fees, simulated_gas_fees):
    if len(simulated_gas_fees)==num_gas_fees:
        return 1
    else:
        return 0

def simulate_gas_fees(print_bool):

    ###################
    # 0. Initialisation
    ###################
    
    # Terra Gas fee
    gas_fee_uusd = float(hlpr.get_terra_gas_prices()['uusd'])
    
    
    # Data frames
    where_ust = {}
    wallet_exposure = {}
    internal_are_bids_active = {}
    
    
    ############
    # Parameters (push to class?)
    ############
    
    NETWORK = 'TEST_MAINNET'
    wallet_seed =  ''
    terra_inst =  hlpr.Terra(NETWORK, wallet_seed)
    
    token_bLuna_whitelist = terra_inst.bLunaToken
    token_bETH_whitelist = terra_inst.bETHToken
    denom_uusd = 10**6
    denom_uluna = 10**6
    denom_bluna = 10**6
    denom_beth = 10**6
        
    
    gas_fee = int(gas_fee_uusd*denom_uusd)          # Important : if too low, txs will fail, but still charged gas
    gas_fee_terraswap = gas_fee*5                   # Important : if too low, txs will fail, but still charged gas
    gas_fee_activate_bid = 290000
    
    terraswap_fee = 3/100
    terra_ust_luna_swap_fee = 0.5/100
    
    bool_retract_all_bids = 0
    
    exposure_uluna_swap_threshold = 0.1*denom_uluna
    exposure_bluna_swap_threshold = 0.1*denom_bluna
    exposure_beth_swap_threshold = 0.1*denom_beth
    
    pnl_swap_threshold = 10 # Threshold that full bLuna->Luna->UST swap needs to pass in order to execute swap
    wallet_min_ust = 10 # *denon_uusd. Eg needed for gas.
    wallet_bidbook_max_bLUNA = 100 # (* denom_uusd)
    wallet_bidbook_max_bETH  = 100 # (* denom_uusd)

    
    amt_uusd_to_bid_bLUNA = 10 # wallet_bidbook_max_bLUNA  # Should be wallet_bidbook_max - where_ust['bidbook'] (if have enough in wallet)
    prem_to_bid_bLUNA = 1
    
    amt_uusd_to_bid_bETH = 10 # wallet_bidbook_max_bETH  # Should be wallet_bidbook_max - where_ust['bidbook'] (if have enough in wallet)
    prem_to_bid_bETH = 1
    
    time_to_wait_bw_txs = 0.1
    time_to_wait_bw_terraswap_swaps = 7

    
    
############################# MAIN FUNCITON ########################################
    gas_fee_sim_dic = {} 

    if print_bool : print("\n################################# \n ")
    
    ###############
    # 4. Submit bid? (Gas, state altering tx)
    ###############
    if 1:

        [amt_uusd_to_bid_bLUNA_str, amt_uusd_to_bid_bLUNA_int] = ["10uusd", 10]
        prem_slot_to_bid_bLUNA = 2
    
        try:
            resp_bLuna = hlpr.execute_submit_bLuna_bid_no_fees(terra_inst, token_bLuna_whitelist, amt_uusd_to_bid_bLUNA_str, prem_slot_to_bid_bLUNA)
            if print_bool : print("###### GAS COST [SUBMIT BID] ", resp_bLuna.gas_wanted)
            gas_fee_sim_dic['submit_bid'] =  resp_bLuna.gas_wanted          ####### <-------

            if print_bool : print("[Gas] Submit bid response for [bLUNA]", resp_bLuna)

        except Exception as e:
                if print_bool : print("[Gas] Submit bid [bLUNA] Response FAILED" )
                if print_bool : print(e)
                if print_bool : print("--------------------------------------- \n")


    ###################
    # 5. Retract Bids
    ####################
    import json
    if(1):
        bids_by_user = hlpr.qry_active_bLuna_bids(terra_inst, token_bLuna_whitelist)
        bids_by_user = bids_by_user[0]
        resp = hlpr.execute_retract_bid_no_fees(terra_inst, bids_by_user['idx'])
        if print_bool :print("[Gas] RETRACT ALL BIDS", resp)
        if print_bool :print("##### GAS EST [RETRACT] ", resp.gas_wanted)
        gas_fee_sim_dic['retract_bid'] = resp.gas_wanted            ####### <-------


    ################## [NEED bETH]
    # 5. Activate bids (Gas, State alt txs) <- needs work.
    ##################

    if 1:
        if(1):
            try:
                #resp = hlpr.execute_activate_all_bids(terra_inst, token_bLuna_whitelist, gas_fee_activate_bid) # This will fail if there is a lot of bids to activate 
                resp = hlpr.execute_activate_all_bids_no_fee(terra_inst, token_bLuna_whitelist) # This will fail if there is a lot of bids to activate 
                if print_bool :print("[Gas] Activate All Bids ", resp,'\n')
                if print_bool :print("####### GAS EST [ACTIVATE BIDS]", resp.gas_wanted)
                gas_fee_sim_dic['activate_bid'] = resp.gas_wanted            ####### <-------

            except Exception as e:
                if print_bool :print("[Gas] Activate All Bids Failed. Bid_ID ", bids_that_can_be_activated )                
                if print_bool :print(e,'\n')        
    
    ################## [NEED bETH]
    # 6. Claimable Liq (Gas, State alt txs)
    ##################

    if (1): # Execute
       try:
           resp = hlpr.execute_claim_all_liquidation_no_fee(terra_inst, token_bLuna_whitelist) 
           if print_bool :print("[Gas] Claim Liq :", resp)
           if print_bool :print("##### GAS EST [CLAIM LIQ]",resp.gas_wanted)
           gas_fee_sim_dic['claim_liq'] = resp.gas_wanted            ####### <-------
       except Exception as e:
                if print_bool :print("[Gas] Claim Liq Failed.")
                if print_bool :print(e)

    ################### [NEED bETH]
    # 7. Swap bad debt (Gas, state altering tx)
    ###################
    if(1):

        # SWAP bLUNA for LUNA
        if (1): 
            try:
                resp = hlpr.execute_swap_bLuna_for_Luna_testnet_no_fee(terra_inst, "1bluna")
                if print_bool :print("##### GAS EST [Terraswap bLuna->Luna]", resp.gas_wanted)
                gas_fee_sim_dic['terraswap_bluna_luna'] = resp.gas_wanted            ####### <-------
                #print("[Gas] Swapped bLuna :", resp,'\n')
            except Exception as e:
                if print_bool :print(e)
                if print_bool :print("[Gas] FAILED TO SWAP bLUNA for LUNA \n RISK : bLuna Exposure!!",'\n')
                
   
        # SWAP LUNA for bLUNA
        if (1):
            try:    
                resp = hlpr.execute_swap_Luna_for_UST_testnet_no_fee(terra_inst, "1uluna")
                if print_bool :print("###### GAS EST [Terraswap Luna->UST]",resp.gas_wanted)
                gas_fee_sim_dic['terraswap_luna_ust'] = resp.gas_wanted            ####### <-------
            except Exception as e:
                if print_bool :print(e)
                if print_bool :print("--------------------------------------- \n")
                        
    return gas_fee_sim_dic

#print("###############")
#print("Gas fee simulation estimates")
#print(gas_fee_sim_dic)


