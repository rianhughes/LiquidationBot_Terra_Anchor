from datetime import date
from os.path import exists
import logging
from pandas import Timestamp, DataFrame

def log_tx_error_check(resp, context_str):
    if('out of gas in location' in resp.raw_log):
        logging.warning("TX FAILED, GAS USED" + str(resp))
    else:
        logging.info(context_str + str(resp))

def logger_init(NETWORK, token_str):
    # Logger file!
    print("Logging system : Starting initialisation")
    today = date.today()
    today_date = today.strftime("%d_%m_%Y")
    log_filename = 'BotFiles/Logs/Log_Light_'+token_str+'_'+today_date+'__'+NETWORK+'.log'
    if exists(log_filename):
        #pass
        #logging.basicConfig(filename=log_filename, filemode='a', format='%(name)s - %(levelname)s - %(message)s',level=logging.INFO)
        log_base = logging.getLogger('log_base')
        log_base.addHandler(logging.FileHandler(log_filename))
        #log_base.info('############## Starting new run ################')
        
    else:
        print("Log file doesn't exist so going to create it :", log_filename)
        logging.basicConfig(filename=log_filename, filemode='w', format='%(name)s - %(levelname)s - %(message)s',level=logging.INFO)
        log_base = logging.getLogger('log_base')
        log_base.addHandler(logging.FileHandler(log_filename))
        log_base.info('############## Starting new run ################')
    print("Logging system : Finished initialisation")
    return log_base


def logger_init_pnl_df(NETWORK, wallet_ust, wallet_exposure, param, token_str):
    # Logger file!
    print("Logging PnL system : Starting initialisation")
    today = date.today()
    today_date = today.strftime("%d_%m_%Y")
    log_filename = 'BotFiles/Logs/Log_Light_'+token_str+'_'+today_date+'__'+NETWORK+'_PnL.csv'
    if not exists(log_filename):
        ust_in_bidbook_and_wallet = wallet_ust['wallet'] + wallet_ust['bidbook_bLuna'] + wallet_ust['bidbook_bETH']
        data = [[Timestamp.now(), 0, ust_in_bidbook_and_wallet,'Init', wallet_ust['wallet'], wallet_ust['bidbook_bLuna'], wallet_ust['bidbook_bETH'], wallet_exposure['bLuna'], wallet_exposure['uLuna'], wallet_exposure['bETH'], '']]
        df = DataFrame(data,columns=['Time','Gas','Coins','Action','wallet_ust','wallet_ust_bidbook_bLuna','wallet_ust_bidbook_bETH','wallet_exp_bLuna','wallet_exp_uLuna','wallet_exp_bETH', 'tx_hash'])
        df.to_csv(log_filename, mode='a', header=not exists(log_filename))


#def logger_update_pnl_df(NETWORK, gas, coins, action):     #### MOVED TO liqbot_helper
#    # Logger file!
#    print("Logging PnL system : Starting initialisation")
#    today = date.today()
#    today_date = today.strftime("%d_%m_%Y")
#    log_filename = 'BotFiles/Logs/Log_Light_bETH_'+today_date+'__'+NETWORK+'_PnL.csv'
#    data = [pd.Timestamp.now(), gas, coins,action] 
#    df = pd.DataFrame(data,columns=['Time','Gas','Coins','Action'])
#    df.to_csv(log_filename, mode='a', header=not os.path.exists(output_path))

    

def logger_init_pnl(NETWORK, token_str):
    # Logger file!
    print("Logging PnL system : Starting initialisation")
    today = date.today()
    today_date = today.strftime("%d_%m_%Y")
    log_filename = 'BotFiles/Logs/Log_Light_'+token_str+'_'+today_date+'__'+NETWORK+'_PnL.log'
    if exists(log_filename):
        logging.basicConfig(filename=log_filename, filemode='a', format='%(name)s - %(levelname)s - %(message)s',level=logging.INFO)
        log_pnl = logging.getLogger()
        log_pnl = logging.getLogger('log_pnl')
        log_pnl.addHandler(logging.FileHandler(log_filename))
        #log_pnl.info('############## Starting new run ################')

    else:
        print("Log PnL file doesn't exist so going to create it :", log_filename)
        logging.basicConfig(filename=log_filename, filemode='w', format='%(name)s - %(levelname)s - %(message)s',level=logging.INFO)
        log_pnl = logging.getLogger('log_pnl')
        log_pnl.addHandler(logging.FileHandler(log_filename))
        #log_pnl.info('############## Starting new run ################')
    print("Logging PnL system : Finished initialisation")
    return log_pnl



