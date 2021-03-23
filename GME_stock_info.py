#!/usr/bin/env python3

# import stock_info module from yahoo_fin
from yahoo_fin import stock_info as si
import time
import datetime
import argparse
import sys

assert sys.version_info >= (3, 0)

# current list of tickers
kGME = 'gme'
kAAPL = 'aapl'
kTSLA = 'tsla'
kAMC = 'amc'
kWaitTime = 5

tickerList = {
    kGME: 'GameStop ',
    kAAPL: 'Apple ',
    kTSLA: 'Tesla ',
    kAMC: 'AMC Corp'
}

headerStr = f"  Price        Open    % Chg          Lo  -  Hi            Volume"

# term codes for setting text colors
rst = '\033[0m'
bold = '\033[01m'
disable = '\033[02m'
underline = '\033[04m'
reverse = '\033[07m'
strikethrough = '\033[09m'
invisible = '\033[08m'

# Default update rate
updateRate = kWaitTime

# handle argument parsing
parser = argparse.ArgumentParser(description='Show a list of tickers. default is GME,APPL,TSLA and AMC')
parser.add_argument('--verbose', help='verbose output', action='store_true')
parser.add_argument('tickers', metavar='N', type=str, nargs='*',help='tickers')

args = parser.parse_args()
logOutput = args.verbose
theTickers = {}

if args.tickers:
    newTickerList = args.tickers
    for name in newTickerList:
        quoteData = si.get_quote_data(name)
#        print(quoteData)
        try:
            theTickers[name] = quoteData['displayName']
        except KeyError:
            print('no displayName')
            tempStr = quoteData['shortName']
            theTickers[name] = tempStr[0:16]
        
#        print(quoteData)
    print(theTickers)
else:
    theTickers = tickerList
    print(f'no list {theTickers}')



# theTickers = tickerList

class fg:
    black = '\033[30m'
    red = '\033[31m'
    green = '\033[32m'
    orange = '\033[33m'
    blue = '\033[34m'
    purple = '\033[35m'
    cyan = '\033[36m'
    lightgrey = '\033[37m'
    darkgrey = '\033[90m'
    lightred = '\033[91m'
    lightgreen = '\033[92m'
    yellow = '\033[93m'
    lightblue = '\033[94m'
    pink = '\033[95m'
    lightcyan = '\033[96m'


class bg:
    black = '\033[40m'
    red = '\033[41m'
    green = '\033[42m'
    orange = '\033[43m'
    blue = '\033[44m'
    purple = '\033[45m'
    cyan = '\033[46m'
    lightgrey = '\033[47m'


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
        self.percentChangeSinceClose = 0
        self.percentChange = 0
        self.aftermarketPrice = 0
        self.aftermarket = 0
        self.quoteData = 0
        self.regularMarketDayHigh = 0
        self.regularMarketDayLow = 0
        self.previousClose = 0
        self.lastPercentChange = 0
        self.lastRegularMarketDayLow = 0
        self.lastRegularMarketDayHigh = 0
        self.timeToPrint = 0
        self.marketVolume = 0
        
    def __repr__(self):
        return "Ticker('{}', {})".format(self.tickerName,self.tickerSymbol)

    def __str__(self):
        return "{}: '{}' ${} open:{} ".format(self.tickerName, self.tickerSymbol, self.currentVal, self.tickerOpen)

    def Print(self):
        print('Name: %s' % self.tickerName)
        print('Symbol: %s' % self.tickerSymbol)
        print('Current: %.2f' % self.currentVal)
        print('Last: %.2f' % self.lastVal)
        print('Open: %.2f' % self.tickerOpen)
        print('Previous Close: %.2f' % self.tickerPrevClose)
        print('Stats: %s' % self.tickerStat)

    def PrintTicker(self):
        if self.regularMarketDayHigh > self.lastRegularMarketDayHigh:
            newHighStr = f'new market day high: {self.regularMarketDayHigh:7.2f}'
        else:
            newHighStr = ''

        if self.regularMarketDayLow < self.lastRegularMarketDayLow:
            newLowStr = f'new market day low: {self.regularMarketDayLow:7.2f}'
        else:
            newLowStr = ''

        newMarketStr = ''
        newMarketDir = ''
        newMarketColor = ''

        if newLowStr != '':
            newMarketDir = downArrow
            newMarketStr = newLowStr
            newMarketColor = fg.red

        if newHighStr != '':
            newMarketDir = upArrow
            newMarketStr = newHighStr
            newMarketColor = fg.lightgreen

        # if self.timeToPrint != 0:
        #     self.timeToPrint -= 1
        #     return
        # else
        #     self.timeToPrint = kWaitTime
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

        fmt2 = f"{self.tickerName:<18} {txtColor2}{self.currentVal:8.2f} "
        fmt2 += f"{txtColor1}{tickerDirection} {rst} "
        fmt2 += f" [{txtColor2}{self.tickerPrevClose:7.2f} {self.percentChange:5.1f}% {prevCloseDirection} {rst}]"

        if self.aftermarket:
            fmt2 += f" {self.aftermarketPrice:8.2f} {self.percentChangeSinceClose:5.1f}%"
            #print(fmt2)

        else:
            # fmt = '%s: ' + txtColor2 + '%8.2f ' + txtColor1 + '%s' + rst + '   [' + txtColor2 + '%7.2f %5.1f%% %s ' + rst + '] [ %6.2f - %6.2f] %s%s %s' + rst
            tempName = self.tickerName + '              '

            # fmt2 = f"{self.tickerName:<17} {txtColor2} {self.currentVal:8.2f} "
            #  fmt2 += f"{txtColor1}{tickerDirection} {rst} "
            # fmt2 += f" [{txtColor2}{self.tickerPrevClose:7.2f} {self.percentChange:5.1f}% {prevCloseDirection} {rst}]"
            fmt2 += f" [ {self.regularMarketDayLow:7.2f} - {self.regularMarketDayHigh:7.2f} ] {rst}"
            fmt2 += f" {self.marketVolume:>12,d} "
            fmt2 += f" {newMarketColor}{newMarketStr}{newMarketDir} {rst}"

        print(fmt2)


    def Update(self):
        global headerStr
        self.updateTime = datetime.datetime.now()
        self.lastVal = self.currentVal
        self.currentVal = si.get_live_price(self.tickerSymbol)
        self.quoteData = si.get_quote_data(self.tickerSymbol)
        self.lastRegularMarketDayLow = self.regularMarketDayLow
        self.lastRegularMarketDayHigh = self.regularMarketDayHigh
        self.tickerStat = self.quoteData

        if self.tickerOpen == 0:
            self.tickerOpen = self.quoteData['regularMarketOpen']

        self.marketVolume = self.quoteData['regularMarketVolume']
            
        if self.tickerPrevClose == 0:
            self.tickerPrevClose = self.quoteData['regularMarketPreviousClose']

        if self.regularMarketDayLow == 0:
            self.regularMarketDayLow = self.quoteData['regularMarketDayLow']
        else:
            self.regularMarketDayLow = min(self.quoteData['regularMarketDayLow'], self.regularMarketDayLow )

        self.regularMarketDayHigh = max(self.quoteData['regularMarketDayHigh'], self.regularMarketDayHigh )

        if isPostMarket():
            self.aftermarket = 1
            self.aftermarketPrice = si.get_postmarket_price(self.tickerSymbol)
            self.previousClose = self.currentVal
            self.percentChangeSinceClose = 0 if self.tickerOpen == 0 else ((self.aftermarketPrice - self.previousClose) / self.previousClose) * 100
            headerStr = f"  Price        Open   % Chg      After Hours "


        self.lastPercentChange = self.percentChange
        self.percentChange = 0 if self.tickerPrevClose == 0 else ((self.currentVal - self.tickerPrevClose) / self.tickerPrevClose) * 100
        self.percentChangeSinceOpen = 0 if self.tickerOpen == 0 else ((self.currentVal - self.tickerOpen) / self.tickerOpen) * 100


pre_market = 0
post_market = 0
market_closed = 0
regular_market = 0


downArrow = '⬇'
upArrow = '⬆'


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


# ------------------------------------------
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

for ticker, name in theTickers.items():
    gTickers.append(Ticker(name, ticker))

headerStr = f"   Price        Open    % Chg          Lo  -  Hi            Volume"

if isPreMarket():
    print('GME PRE: %f' % si.get_premarket_price(kGME))

if isPostMarket():
    print('GME POST: %f' % si.get_postmarket_price(kGME))


while 1:
    UpdateMarketStatus()
    now = datetime.datetime.now()

    # time.sleep(1)  # Sleep for 1 seconds


    for myTicker in gTickers:
        myTicker.Update()
        
    timeStr = now.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f'{timeStr:<19} {headerStr}')

    for myTicker in gTickers:
        myTicker.PrintTicker()


    print('-')

    time.sleep(updateRate)  # Sleep for n seconds
