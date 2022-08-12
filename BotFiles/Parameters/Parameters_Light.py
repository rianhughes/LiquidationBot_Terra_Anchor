############
# Variables, Parameter
############

# Sleep time between tx
sleep_time_tx = 30

# denominations
denom_uusd  = 10**6
denom_uluna = 10**6
denom_bluna = 10**6
denom_bETH = 10**6

# Gas price est
gas_price = 0.22

# min amount of ust to hold in wallet (for gas)
wallet_min_ust = 0.1  

# Max amount of bETH to hold (same as amt_uusd_to_bid_bETH if only ever have a sinlge bid)
wallet_bidbook_max_bETH  = 10
wallet_bidbook_max_bLuna  = 100

# Only claim/swap when this amount has been hit
claim_swap_threshold_bETH = wallet_bidbook_max_bETH*0.5
claim_swap_threshold_bLuna = wallet_bidbook_max_bLuna*0.5

# Bid amount (min, max), premium
amt_uusd_to_bid_bETH = wallet_bidbook_max_bETH
amt_uusd_to_bid_bLuna = wallet_bidbook_max_bLuna

# Premium slot to bid for
prem_slot_to_bid_bETH = 1
prem_slot_to_bid_bLuna = 1


# Extras for neatness
amt_uusd_to_bid_bETH_str = str(amt_uusd_to_bid_bETH)+"uusd"
amt_uusd_to_bid_bETH_str = str(amt_uusd_to_bid_bLuna)+"uusd"


