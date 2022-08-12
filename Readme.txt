This liquidation bot was designed to profit from liquidations on Anchor, the largest money-market protocol on Terra (before Terra blew up!).



It is relatively simple, but was fully functional and returned a small profit. It provided a great opportunity to learn more about how Terra worked, and besides, it was a ton of fun to build!.

The bot is structured such that it continuously runs in the following loop:
    1. Check if we need to submit a bid for ETH or Luna. If so, submit bid, if not, pass.
    2. Check if we need to retract our bid, and if so retract it.
    3. Check if we can activate our bid, and if so, activate it.
    4. Check if our bid has been 'hit', and claim all the ETH/Luna we can.
    5. Swap the bad-debt for UST, using TerraSwap. Speed is particularly important at this point due to price-risk.

LiqBot_Bid_For_ETH : 
    This is the main file that seeks to profit on bad ETH based debt.

LiqBot_Bid_For_Luna : 
    This is the main file that seeks to profit on bad LUNA based debt.

BotFiles/Logs:
    The bot also stores a log of any action taken by the bot, which is very useful to observe it's behaviour, particularly when sometihng unexpected happens. 
    Logs record the time, gas used, coins spent, action taken, tx_hash, and location of the money (eg, is it in the bidbook, or the bots wallet, etc). 
    An example log is given in 'BotFiles' (although tx hashes have been deleted for privacy).

BotFiles/Config:
    This file contains the typical transaction fee given in multiple currencies.

BotFiles/Params:
    This file contains the parameters of the bot, such as bid size, maximum to bid at any given time, etc.
