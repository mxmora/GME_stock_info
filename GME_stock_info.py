#!/usr/bin/env python3

# import stock_info module from yahoo_fin
from yahoo_fin import stock_info as si
import time
import datetime


kGME = 'gme'
kAAPL = 'aapl'
kTSLA = 'tsla'
kAMC = 'amc'

tickerList = {
    kGME: 'GME ',
    kAAPL: 'AAPL ',
    kTSLA: 'TSLA ',
    kAMC: 'GME '
}

# term codes
rst = '\033[0m'
bold = '\033[01m'
disable = '\033[02m'
underline = '\033[04m'
reverse = '\033[07m'
strikethrough = '\033[09m'
invisible = '\033[08m'


class fg:
    black='\033[30m'
    red='\033[31m'
    green='\033[32m'
    orange='\033[33m'
    blue='\033[34m'
    purple='\033[35m'
    cyan='\033[36m'
    lightgrey='\033[37m'
    darkgrey='\033[90m'
    lightred='\033[91m'
    lightgreen='\033[92m'
    yellow='\033[93m'
    lightblue='\033[94m'
    pink='\033[95m'
    lightcyan='\033[96m'


class bg:
    black='\033[40m'
    red='\033[41m'
    green='\033[42m'
    orange='\033[43m'
    blue='\033[44m'
    purple='\033[45m'
    cyan='\033[46m'
    lightgrey='\033[47m'


class Ticker:
    def __init__(self, name, sym):
        self.updateTime = 0
        self.currentVal = 0
        self.lastVal = 0
        self.tickerStat = ''
        self.tickerOpen = 0
        self.tickerPrevClose = 0
        self.tickerSymbol = sym
        self.tickerName = name
        self.percentChangeSinceOpen = 0
        self.percentChange = 0
        self.aftermarketPrice = 0
        self.aftermarket = 0

    def Print(self):
        print('Name: %s' % self.tickerName)
        print('Symbol: %s' % self.tickerSymbol)
        print('Current: %.2f' % self.currentVal)
        print('Last: %.2f' % self.lastVal)
        print('Open: %.2f' % self.tickerOpen)
        print('Previous Close: %.2f' % self.tickerPrevClose)
        print('Stats: %s' % self.tickerStat)

    def PrintTicker(self):

        if self.lastVal == self.currentVal:
            tickerDirection = ' '
            txtColor1 = rst
        else:
            if self.lastVal > self.currentVal:
                txtColor1 = fg.red
                tickerDirection = downArrow
            else:
                txtColor1 = fg.lightgreen
                tickerDirection = upArrow

        if self.percentChange < 0:
            prevCloseDirection = downArrow
            txtColor2 = fg.red
        else:
            prevCloseDirection = upArrow
            txtColor2 = fg.lightgreen

        if self.aftermarket:
            fmt = '%s: ' + txtColor2 + '%8.2f ' + txtColor1 + '%s' + rst + '   [' + txtColor2 + '%7.2f %5.1f%% %s ' + rst + '] after: %8.2f'
            print( fmt % (self.tickerName, self.currentVal, tickerDirection, self.tickerPrevClose, self.percentChange, prevCloseDirection,self.aftermarketPrice))
        else:
            fmt = '%s: ' + txtColor2 + '%8.2f ' + txtColor1 + '%s' + rst + '   [' + txtColor2 + '%7.2f %5.1f%% %s ' + rst + ']'
            print(fmt  % ( self.tickerName, self.currentVal, tickerDirection, self.tickerPrevClose, self.percentChange, prevCloseDirection))

    def Update(self):
        self.updateTime = datetime.datetime.now()
        self.lastVal = self.currentVal
        self.currentVal = si.get_live_price(self.tickerSymbol)
        if isPostMarket():
            self.aftermarket = 1
            self.aftermarketPrice = si.get_postmarket_price(self.tickerSymbol)

        self.percentChange = 0 if self.tickerPrevClose == 0 else ((self.currentVal - self.tickerPrevClose) / self.tickerPrevClose) * 100
        self.percentChangeSinceOpen = 0 if self.tickerOpen == 0 else ((self.currentVal - self.tickerOpen) / self.tickerOpen) * 100


pre_market = 0
post_market = 0
market_closed = 0
regular_market = 0

downArrow = '⬇'
upArrow = '⬆'


# ------------------------------------------
def percentChange( init, current):
    return ((current - init) / init) * 100


# ------------------------------------------
def isPreMarket():
    return pre_market


# ------------------------------------------
def isPostMarket():
    return post_market


# ------------------------------------------
def isMarketClosed():
    return market_closed


# ------------------------------------------
def isRegularMarket():
    return regular_market


def UpdateMarketStatus():
    global pre_market
    global post_market
    global market_closed
    global regular_market

    market_status = si.get_market_status()

    pre_market = 0
    post_market = 0
    market_closed = 0
    regular_market = 0

    if market_status == 'REGULAR':
        regular_market = 1
    if market_status == 'PRE':
        pre_market = 1
    if market_status.startswith('POST'):
        post_market = 1
    if market_status == 'CLOSED' or market_status == 'POSTPOST':
        market_closed = 1
        # print('market closed')

# ------------------------------------------
def printTicker(tickerName, lastValue, currentValue, previousClose, percentChanged):
    if lastValue == currentValue:
        tickerDirection = ' '
    else:
        tickerDirection = downArrow if (lastValue > currentValue) else upArrow

    if percentChanged < 0:
        prevCloseDirection = downArrow
    else:
        prevCloseDirection = upArrow

    print('%s:  %8.2f %s [%8.2f %8.1f%% %s ]' % (tickerName, currentValue, tickerDirection, previousClose, percentChanged, prevCloseDirection))


# See if the market is open, pre or post. Quit if closed
UpdateMarketStatus()

if isMarketClosed():
    print('market closed')
    # exit()

gTickers = []

for ticker, name in tickerList.items():
    gTickers.append(Ticker(name, ticker))


# Build our tickers
myGME = Ticker('GME ', kGME)
myAAPL = Ticker('AAPL', kAAPL)
myTSLA = Ticker('TSLA', kTSLA)
myAMC = Ticker('AMC ', kAMC)

if isPreMarket():
    print('GME PRE: %f' % si.get_premarket_price(kGME))

if isPostMarket():
    print('GME POST: %f' % si.get_postmarket_price(kGME))

if isPostMarket() or isRegularMarket():
    the_gme_list = si.get_quote_data(kGME)
    the_aapl_list = si.get_quote_data(kAAPL)
    the_tsla_list = si.get_quote_data(kTSLA)
    the_amc_list = si.get_quote_data(kAMC)

    myGME.tickerStat = the_gme_list 
    myAAPL.tickerStat = the_aapl_list
    myTSLA.tickerStat = the_tsla_list
    myAMC.tickerStat = the_amc_list

    # get open info
    gme_open = the_gme_list['regularMarketOpen']
    aapl_open = the_aapl_list['regularMarketOpen']
    tsla_open = the_tsla_list['regularMarketOpen']
    amc_open = the_amc_list['regularMarketOpen']

    myGME.tickerOpen = gme_open
    myAAPL.tickerOpen = aapl_open
    myTSLA.tickerOpen = tsla_open
    myAMC.tickerOpen = amc_open

    # get stats for each stock
    gme_prev_close = the_gme_list['regularMarketPreviousClose']
    aapl_prev_close = the_aapl_list['regularMarketPreviousClose']
    tsla_prev_close = the_tsla_list['regularMarketPreviousClose']
    amc_prev_close = the_amc_list['regularMarketPreviousClose']

    myGME.tickerPrevClose = gme_prev_close
    myAAPL.tickerPrevClose = aapl_prev_close
    myTSLA.tickerPrevClose = tsla_prev_close
    myAMC.tickerPrevClose = amc_prev_close

    # list previous and open
    print('GME  previous close:  %8.2f' % gme_prev_close )
    print('AAPL previous close: %8.2f' % aapl_prev_close )
    print('TSLA previous close: %8.2f' % tsla_prev_close)
    print('AMC  previous close:  %8.2f' % amc_prev_close)
    print(' ')
    print('GME  open: %8.2f' % gme_open )
    print('AAPL open: %8.2f' % aapl_open )
    print('TSLA open: %8.2f' % tsla_open)
    print('AMC  open: %8.2f' % amc_open)
    print(' ')


while 1:
    UpdateMarketStatus()
    now = datetime.datetime.now()

    myGME.Update()
    myAAPL.Update()
    myTSLA.Update()
    myAMC.Update()


    # time.sleep(1)  # Sleep for 1 seconds

    print(now.strftime('%Y-%m-%d %H:%M:%S'))
    # for myTicker in gTickers:
    #     myTicker.Update()
    #     myTicker.PrintTicker()

    myGME.PrintTicker()
    myAAPL.PrintTicker()
    myTSLA.PrintTicker()
    myAMC.PrintTicker()

    print('-')

    time.sleep(5)  # Sleep for 5 seconds
