#!/usr/bin/env python3

# import stock_info module from yahoo_fin
from yahoo_fin import stock_info as si
import time
import datetime
import argparse
import sys
import os
# import curses
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import queue as que
import threading

# Windows
if os.name == 'nt':
    import msvcrt

# Posix (Linux, OS X)
else:
    import sys
    import termios
    import atexit
    from select import select
    
assert sys.version_info >= (3, 0)


class KBHit:

    def __init__(self):
        # Creates a KBHit object that you can call to do various keyboard things.
        #

        if os.name == 'nt':
            pass
        else:

            # Save the terminal settings
            self.fd = sys.stdin.fileno()
            self.new_term = termios.tcgetattr(self.fd)
            self.old_term = termios.tcgetattr(self.fd)

            # New terminal setting unbuffered
            self.new_term[3] = (self.new_term[3] & ~termios.ICANON & ~termios.ECHO)
            termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.new_term)

            # Support normal-terminal reset at exit
            atexit.register(self.set_normal_term)

    def set_normal_term(self):
        # Resets to normal terminal.  On Windows this is a no-op.
        #

        if os.name == 'nt':
            pass

        else:
            termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old_term)

    def getch(self):
        # Returns a keyboard character after kbhit() has been called.
        #    Should not be called in the same program as getarrow().
        #

        s = ''

        if os.name == 'nt':
            return msvcrt.getch().decode('utf-8')

        else:
            return sys.stdin.read(1)

    def getarrow(self):
        # Returns an arrow-key code after kbhit() has been called. Codes are
        # 0 : up
        # 1 : right
        # 2 : down
        # 3 : left
        # Should not be called in the same program as getch().
        #

        if os.name == 'nt':
            msvcrt.getch()  # skip 0xE0
            c = msvcrt.getch()
            vals = [72, 77, 80, 75]

        else:
            c = sys.stdin.read(3)[2]
            vals = [65, 67, 66, 68]

        return vals.index(ord(c.decode('utf-8')))

    def kbhit(self):
        #  Returns True if keyboard character was hit, False otherwise.
        #
        if os.name == 'nt':
            return msvcrt.kbhit()

        else:
            dr, dw, de = select([sys.stdin], [], [], 0)
            return dr != []


# =======================================================================================
# Globals
# =======================================================================================
kMARKET = "MARKET"
kUPDATE = "UPDATE"
kSTOP = "STOP"
kPAUSE = "PAUSE"

kSortOrderTickerAsc = '1'
kSortOrderTickerDsc = '2'
kSortOrderPercentAsc = '3'
kSortOrderPercentDsc = '4'
kSortOrderVolumeAsc = '5'
kSortOrderVolumeDsc = '6'
kSortOrderIndexAsc = '7'
kSortOrderIndexDsc = '8'
valid_sort_options = {'1', '2', '3', '4', '5', '6', '7', '8'}

gCurrentSortOrder = None
gEmailQueue = que.Queue(maxsize=100)
gMailThread = None
# gUseThreading = False
gTickerThread = None
gTickerQueue = que.Queue(maxsize=10)

#gShowFiftyTwo = 0
gShowSorted = True
#gSendEmail = False

gColumns = []
gTickers = []
gTopMoversTickers = []
# movers = []
gTopMoversList = {}

pre_pre_market = 0
pre_market = 0
post_market = 0
market_closed = 0
regular_market = 0

downArrow = '⬇'
upArrow = '⬆'
warningSign = '⚠'

# current list of tickers
kGME = 'gme'
kAAPL = 'aapl'
kTSLA = 'tsla'
kAMC = 'amc'
kWaitTime = 5
kDisplayName = 'displayName'

tickerList = {
    kGME: 'GameStop ',
    kAAPL: 'Apple ',
    kTSLA: 'Tesla ',
    kAMC: 'AMC Corp'
}

gHeaderStr = f"        Price           Open    % Chg          Lo    -    Hi                   Volume"

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


# =======================================================================================
# debugLog
# =======================================================================================
def debugLog(dbg_msg):
    print(dbg_msg) if gLogOutput else None


# =======================================================================================
# build a ticker dictionary from a list of symbols
# =======================================================================================
def BuildTickerDict(in_dict, in_list):

    for theSymbol in in_list:
       
        debugLog(theSymbol)
        quoteData = si.get_quote_data(theSymbol)

        debugLog(quoteData)
        try:
            tempStr = quoteData[kDisplayName]
        except KeyError:
           
            debugLog('no displayName')
            tempStr = quoteData['shortName']

        in_dict[theSymbol] = tempStr[0:20]
    debugLog(in_dict)


# =======================================================================================
# Update Header String
# =======================================================================================
def UpdateHeaderString(afterMarket):
    global gHeaderStr
    global gCurrentSortOrder

    tickerSortOrder = " "
    percentSortOrder = " "
    volumeSortOrder = " "

    if gCurrentSortOrder == kSortOrderTickerAsc:
        tickerSortOrder = upArrow
    if gCurrentSortOrder == kSortOrderVolumeAsc:
        volumeSortOrder = upArrow
    if gCurrentSortOrder == kSortOrderPercentAsc:
        percentSortOrder = upArrow
    if gCurrentSortOrder == kSortOrderTickerDsc:
        tickerSortOrder = downArrow
    if gCurrentSortOrder == kSortOrderVolumeDsc:
        volumeSortOrder = downArrow
    if gCurrentSortOrder == kSortOrderPercentDsc:
        percentSortOrder = downArrow

    gHeaderStr = f" Ticker {tickerSortOrder} "  # symbol
    gHeaderStr += "Name                      "
    gHeaderStr += f"Price      "
    gHeaderStr += "[    Open  "
    gHeaderStr += f"% Chg {percentSortOrder}  ] "
    if not afterMarket:
        gHeaderStr += "[       Lo    -    Hi   ] "
    if gShowFiftyTwo:
        gHeaderStr += "[    52 wk Lo  -    Hi      % Chg  ] "
    if not afterMarket:
        gHeaderStr += f"            Volume {volumeSortOrder}"
    if afterMarket:
        gHeaderStr += "[  After Hours    % Chg ]"
                    

# =======================================================================================
# handle argument parsing
# =======================================================================================
parser = argparse.ArgumentParser(description='Show a list of stock tickers. It will show the current price is market is open, after hours price and volume. (default is GME, APPL, TSLA and AMC)')
parser.add_argument('--verbose', help='Enable verbose output. Mostly for debugging', action='store_true')
parser.add_argument('--alert', help='Ring the bell on new lows and new highs', action='store_true')
parser.add_argument('--top', type=int, default=0, help='Show top moving stocks, provide a number less than 100')
parser.add_argument('--file', type=str, default='', help='a file containing a list of tickers')
parser.add_argument('--rate', type=int, help='How many seconds to pause between updates.' )
parser.add_argument('--fiftytwo', help='Show the 52 week high low', action='store_true')
parser.add_argument('--curses', help='Show the list using curses.', action='store_true')
parser.add_argument('--email', help='If alerts are on, send an email also', action='store_true')
parser.add_argument('--thread', help='use threading for updates', action='store_true')
parser.add_argument('--sort', type=int, default=0, help='Sort by column ( 1. Ticker ascending 2. Ticker descending 3. Percent ascending 4. Percent descending 5. Vol ascending 6. Vol descending 7. Added ascending 8. Added descending )')
parser.add_argument('tickers', metavar='symbols', type=str, nargs='*', help='A one or more stock symbols that you want to display.')

args = parser.parse_args()
gLogOutput = args.verbose
gShowTopMovers = args.top
gShowFiftyTwo = args.fiftytwo
gBell = args.alert
gUseCurses = args.curses
gSendEmail = args.email
gUseThreading = args.thread
gShowSorted = args.sort

if gShowSorted:
    if gShowSorted.__str__() in valid_sort_options:
        gCurrentSortOrder = gShowSorted

# gLogOutput = True

theTickers = {}
# Adjust the rate of update
if args.rate:
    if args.rate < 1:
        updateRate = 1
    else:
        updateRate = args.rate

    print(f"Update rate set to {updateRate} second(s)")


if args.tickers:
    newTickerList = args.tickers
    BuildTickerDict(theTickers, newTickerList)
    debugLog(theTickers)
else:
    theTickers = tickerList

    debugLog(f'No list supplied. using default : {theTickers}')
        
class HeaderRec:
    def __init__(self, in_name, in_width):
        self.name = in_name
        self.width = in_width
    
    def __repr__(self):
        return "HeaderRec('{}', {})".format(self.name, self.width)

    def __str__(self):
        return f"{self.name}: {self.width}"
   

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
        self.updateTime = datetime.datetime.now()
        self.index = 0
        self.tickerSymbol = sym.upper()
        self.tickerName = name
        self.percentChangeSinceOpen = 0
        self.percentChangeSinceClose = 0
        self.percentChange = 0
        self.FiftyTwoPercentChange = 0
        self.aftermarketPrice = 0
        self.aftermarket = 0
        self.previousClose = 0
        self.lastPercentChange = 0
        self.timeToPrint = 0
        
        self.quoteData = GetQuoteData(self.tickerSymbol)
        self.currentVal = self.quoteData['regularMarketPrice']
        
        self.lastRegularMarketDayLow = self.quoteData['regularMarketDayLow']
        self.lastRegularMarketDayHigh = self.quoteData['regularMarketDayHigh']
        self.regularMarketDayLow = self.lastRegularMarketDayLow
        self.regularMarketDayHigh =  self.lastRegularMarketDayHigh
        self.lastFiftyTwoWeekLow = self.quoteData['fiftyTwoWeekLow']
        self.lastFiftyTwoWeekHigh = self.quoteData['fiftyTwoWeekHigh']
        self.marketVolume = self.quoteData['regularMarketVolume']
        self.fiftyTwoWeekHigh = self.lastFiftyTwoWeekHigh 
        self.fiftyTwoWeekLow = self.lastFiftyTwoWeekLow
        self.tickerOpen = self.quoteData['regularMarketOpen']
        self.tickerPrevClose = self.quoteData['regularMarketPreviousClose']
        self.lastVal = self.currentVal

    def __repr__(self):
        return "Ticker('{}', {})".format(self.tickerName, self.tickerSymbol)

    def __str__(self):
        return f"{self.tickerName}: '{self.tickerSymbol}' ${self.currentVal} open:{self.tickerOpen} lastVal:{self.lastVal} prevClose:{self.tickerPrevClose} [{self.quoteData}]"

    def GetIndex(self):
        return self.index

    def SetIndex(self, in_index):
        self.index = in_index

    def GetTicker(self):
        return self.tickerSymbol

    def GetPercentChanged(self):
        return self.percentChange

    def GetVolume(self):
        return self.marketVolume

    def GetFiftyTwoOutputStr(self):
        return f" [ {self.fiftyTwoWeekLow:9.2f} - {self.fiftyTwoWeekHigh:9.2f} {self.FiftyTwoPercentChange:9.2f}% ]{rst}"

    def PrintTicker(self):
        newLowStr = ''
        newHighStr = ''

        if self.regularMarketDayHigh > self.lastRegularMarketDayHigh:
            self.currentVal = max (self.currentVal , self.regularMarketDayHigh)
            
            newHighStr = f'new market day high: {self.regularMarketDayHigh:9.2f}'
            if gBell:
                newHighStr += '\u0007'

        if self.regularMarketDayLow < self.lastRegularMarketDayLow:
            self.currentVal = min(self.currentVal , self.regularMarketDayLow)

            newLowStr = f'new market day low: {self.regularMarketDayLow:9.2f}'
            if gBell:
                newLowStr += '\u0007'

        if gShowFiftyTwo:
            # Check to see if we hit a new 52 week low or high
            if self.currentVal > self.lastFiftyTwoWeekHigh:
                newHighStr = f'new 52 week high: {self.fiftyTwoWeekHigh:9.2f}'
                if gBell:
                    newHighStr += '\u0007'
                    newHighStr += '\u0007'

            if self.currentVal < self.lastFiftyTwoWeekLow:
                newLowStr = f'new 52 week low: {self.fiftyTwoWeekLow:9.2f}'
                if gBell:
                    newLowStr += '\u0007'
                    newLowStr += '\u0007'

        newMarketStr = ''
        newMarketDir = ''
        newChartDir = ''
        newMarketColor = ''
        warningStr = ' '
        warningColor = rst
        invertText = False
        invertBkgndColor = bg.black
        invertFgColor = fg.lightgreen

        if newLowStr != '':
            newMarketDir = downArrow
            newChartDir = "📉"
            newMarketStr = newLowStr
            newMarketColor = bg.red
            warningStr = downArrow
            warningColor = bg.red
            invertText = True
            invertBkgndColor = bg.red
            invertFgColor = fg.lightgreen

        if newHighStr != '':
            newMarketDir = upArrow
            newChartDir = "📈"
            newMarketStr = newHighStr
            newMarketColor = bg.green
            warningStr = upArrow
            warningColor = bg.green
            invertText = True
            invertBkgndColor = bg.green
            invertFgColor = fg.blue

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

        if invertText:
            outputStr = f"{invertBkgndColor}{invertFgColor}{warningStr} {self.tickerSymbol:<8} {self.tickerName:<22} {self.currentVal:9.2f} "
            outputStr += f"{tickerDirection}  "
            outputStr += f" [{self.tickerPrevClose:9.2f} {self.percentChange:5.1f}% {prevCloseDirection} ]{rst}"
        else:
            outputStr = f"{warningColor}{warningStr}{rst} {self.tickerSymbol:<8} {self.tickerName:<22} {txtColor2}{self.currentVal:9.2f} "
            outputStr += f"{txtColor1}{tickerDirection} {rst} "
            outputStr += f" [{txtColor2}{self.tickerPrevClose:9.2f} {self.percentChange:5.1f}% {prevCloseDirection} {rst}]"

        if self.aftermarket:
            if gShowFiftyTwo:
                outputStr += self.GetFiftyTwoOutputStr()
            outputStr += f" [{self.aftermarketPrice:11.2f}    {self.percentChangeSinceClose:6.1f}% ]"
        else:
            outputStr += f" [ {self.regularMarketDayLow:9.2f} - {self.regularMarketDayHigh:9.2f} ]{rst}"
            if gShowFiftyTwo:
                outputStr += self.GetFiftyTwoOutputStr()
            outputStr += f" {self.marketVolume:>18,d} "
            outputStr += f" {newMarketColor}{newMarketStr}{newMarketDir} {rst}"

        print(outputStr)

        if gSendEmail and newMarketStr:
            tempSymbol = self.tickerSymbol.upper()
            # build clean output string no terminal commands
            outputStr = f"Ticker: {self.tickerSymbol:<18}\n"
            outputStr += f"Name:   {self.tickerName:<22}\n"
            outputStr += f"Price:      {self.currentVal:18.2f}\n"
            outputStr += f"Prv Close:  {self.tickerPrevClose:18.2f}\n"
            outputStr += f"% Change:   {self.percentChange:18.2f}%\n"
            outputStr += f"Day Low:    {self.regularMarketDayLow:18.2f}\n"
            outputStr += f"Day High:   {self.regularMarketDayHigh:18.2f}\n"
            outputStr += f"52 Wk Lo:   {self.fiftyTwoWeekLow:18.2f}\n"
            outputStr += f"52 Wk Hi:   {self.fiftyTwoWeekHigh:18.2f}\n"

            outputStr += f"Volume:  {self.marketVolume:>18,d}.00\n"
            # outputStr += f"Status: {newMarketStr}\n"
            curValStr = f"$ {self.currentVal:.2f} {self.percentChange:5.1f}%"

            body_text = f"{tempSymbol}: {self.tickerName} {newMarketStr} \n\n {outputStr} \n"

            outputStr = f"Ticker: {self.tickerSymbol:<18}<br>\n"
            outputStr += f"Name:   {self.tickerName:<22}<br>\n"
            outputStr += f"Price:      {self.currentVal:18.2f}<br>\n"
            outputStr += f"Prv Close:  {self.tickerPrevClose:18.2f}<br>\n"
            outputStr += f"% Change:   {self.percentChange:18.2f}%<br>\n"
            outputStr += f"Day Low:    {self.regularMarketDayLow:18.2f}<br>\n"
            outputStr += f"Day High:   {self.regularMarketDayHigh:18.2f}<br>\n"
            outputStr += f"52 Wk Lo:   {self.fiftyTwoWeekLow:18.2f}<br>\n"
            outputStr += f"52 Wk Hi:   {self.fiftyTwoWeekHigh:18.2f}<br><hr><br>\n"

            # Build a table
            outputStr += f"""
            <table style="width:30%">
              <tr>
                <th>{self.tickerName:<22}</th>
                <th style="text-align:center">{self.tickerSymbol:<18}</th> 
              </tr>
              <tr>
                <td>Price</td>
                <td style="text-align:right"><span>{self.currentVal:.2f}</span></td>
              </tr>
              <tr>
                <td>Previous Close</td>
                <td style="text-align:right"><span>{self.tickerPrevClose:.2f}</span></td>
              </tr>
              <tr>
                <td>Percent Changed</td>
                <td style="text-align:right"><span>{self.percentChange:.3f}%</span></td>
              </tr>
              <tr>
                <td>Market Day Low</td>
                <td style="text-align:right"><span>{self.regularMarketDayLow:.2f}</span></td>
              </tr>              
              <tr>
                <td>Market Day High</td>
                <td style="text-align:right"><span>{self.regularMarketDayHigh:.2f}</span></td>
              </tr>
              <tr>
                <td>52 Week Low</td>
                <td style="text-align:right"><span>{self.fiftyTwoWeekLow:.2f}</span></td>
              </tr>
              <tr>
                <td>52 Week High</td>
                <td style="text-align:right"><span>{self.fiftyTwoWeekHigh:.2f}</span></td>
              </tr>
              <tr>
                <td>Volume</td>
                <td style="text-align:right"><span>{self.marketVolume:>18,d}</span></td>
              </tr>
            </table>"""

            body_html = f"{tempSymbol}: {self.tickerName} {newMarketStr} <br><br> {outputStr} \n"

            tempMsg = buildEmailMessage(tempSymbol, curValStr, self.tickerName,  newMarketStr, body_text, body_html, newMarketDir, newChartDir)
            # print(outputStr)
            queueEmail(tempMsg)
            # sendEmail(tempMsg)

    def Update(self):
        global gHeaderStr
        self.updateTime = datetime.datetime.now()
        self.lastVal = self.currentVal
        self.lastRegularMarketDayLow = min(self.regularMarketDayLow, self.lastRegularMarketDayLow)
        self.lastRegularMarketDayHigh = max(self.regularMarketDayHigh, self.lastRegularMarketDayHigh)
        self.lastFiftyTwoWeekLow = min(self.fiftyTwoWeekLow, self.lastFiftyTwoWeekLow)
        self.lastFiftyTwoWeekHigh = max(self.fiftyTwoWeekHigh, self.lastFiftyTwoWeekHigh)
                
        # self.currentVal = si.get_live_price(self.tickerSymbol)
        self.quoteData = GetQuoteData(self.tickerSymbol)
 
        self.regularMarketDayLow = min(self.quoteData['regularMarketDayLow'], self.regularMarketDayLow)
        self.regularMarketDayHigh = max(self.quoteData['regularMarketDayHigh'], self.regularMarketDayHigh)
        self.currentVal = self.quoteData['regularMarketPrice']
        self.marketVolume = self.quoteData['regularMarketVolume']
        self.fiftyTwoWeekHigh = self.quoteData['fiftyTwoWeekHigh']
        self.fiftyTwoWeekLow = self.quoteData['fiftyTwoWeekLow']
        self.tickerOpen = self.quoteData['regularMarketOpen']
        self.tickerPrevClose = self.quoteData['regularMarketPreviousClose']

        UpdateHeaderString(isPostMarket())
        
        if isPostMarket():
            self.aftermarket = 1
            if self.quoteData['quoteType'] == 'CRYPTOCURRENCY':
                self.aftermarketPrice = self.quoteData['regularMarketPrice']
            else:
                self.aftermarketPrice = self.quoteData['postMarketPrice']  # si.get_postmarket_price(self.tickerSymbol)
            self.previousClose = self.currentVal
            self.percentChangeSinceClose = 0 if self.previousClose == 0 else ((self.aftermarketPrice - self.previousClose) / self.previousClose) * 100

        self.lastPercentChange = self.percentChange
        self.percentChange = 0 if self.tickerPrevClose == 0 else ((self.currentVal - self.tickerPrevClose) / self.tickerPrevClose) * 100
        self.FiftyTwoPercentChange = ((self.fiftyTwoWeekHigh - self.fiftyTwoWeekLow) / self.fiftyTwoWeekLow) * 100

        self.percentChangeSinceOpen = 0 if self.tickerOpen == 0 else ((self.currentVal - self.tickerOpen) / self.tickerOpen) * 100


# =======================================================================================
# Utility functions
# =======================================================================================
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


# =======================================================================================
# UpdateMarketStatus
# =======================================================================================
def UpdateMarketStatus():
    global pre_pre_market
    global pre_market
    global post_market
    global market_closed
    global regular_market

    market_status = GetQuoteData(kMARKET)

    debugLog(f"Market Status: {market_status}")

    pre_pre_market = 0
    pre_market = 0
    post_market = 0
    market_closed = 0
    regular_market = 0

    if market_status == 'REGULAR':
        regular_market = 1
    if market_status == 'PRE':
        pre_market = 1
    if market_status == 'PREPRE':
        pre_pre_market = 1
    if market_status.startswith('POST'):
        post_market = 1
    if market_status == 'CLOSED' or market_status == 'POSTPOST':
        market_closed = 1
        # print('market closed')


# =======================================================================================
# GetQuoteData
# =======================================================================================
def GetQuoteData(tickerSymbol):
    quoteData = ''

    try:
    
        if tickerSymbol == kMARKET:
            quoteData = si.get_market_status()
        else:
            quoteData = si.get_quote_data(tickerSymbol)
            
    except KeyboardInterrupt:
        pass
    except ConnectionError:
        pass
    except TypeError:
        print("network may be down")
        pass
    except OSError as e:
        if e.errno == 50:
            exit()
    except AssertionError:
        if gLogOutput:
            print("assertion error. Likely data not available")
        else:
            print("something is up... hold on...")
        pass
    
    return quoteData


# =======================================================================================
# Show Top Movers
# =======================================================================================
def ShowTopMovers(topNum, tempTickers):
    df = si.get_day_most_active()
    movers = df.loc[1:topNum, "Symbol"]

    # tempTickers = {}

    print(f"Top {topNum} Movers")
    for symName in movers:
        quoteData = si.get_quote_data(symName)

        try:
            tempStr = quoteData[kDisplayName]
        except KeyError:
            debugLog('no displayName')

            tempStr = quoteData['shortName']
        tempTickers[symName] = tempStr[0:22]
        print(f"{tempTickers[symName]:<24}: {symName:<5}{quoteData['regularMarketPrice']:9.2f}")
    print('-\n')


# =======================================================================================
# setRate new update rate
# =======================================================================================
def setRate():
    global updateRate

    print(f'enter new rate (seconds):')
    newRate = input()
    if newRate:
        updateRate = int(newRate)
        print(f"setting new rate. current rate = {updateRate}\n")

    else:
        print(f"skipping. not setting new rate. current rate = {updateRate}\n")


# =======================================================================================
# addSymbol Add a symbols(s) to the current display
# =======================================================================================
def addSymbol():
    print(f'enter symbols to add (space separated):')
    newSymbols = input()
    if newSymbols:
        newTickersToAdd = {}
        list1 = list(newSymbols.split(" ")) 
        print(list1)
        BuildTickerDict(newTickersToAdd, list1)

        print(newTickersToAdd)
        for ticker, tickerName in newTickersToAdd.items():
            gTickers.append(Ticker(tickerName, ticker))
    else:
        print("skipping. no symbols entered\n")


# =======================================================================================
# deleteSymbol remove a symbols(s) to the current display
# =======================================================================================
def deleteSymbol():
    print(f'Enter symbols to delete (space separated list):')
    newSymbols = input()
    if newSymbols:
        newTickersToDelete = {}
        list1 = list(newSymbols.split(" "))
        print(list1)
        BuildTickerDict(newTickersToDelete, list1)

        print(newTickersToDelete)
        for ticker, tickerName in newTickersToDelete.items():
            count = 0
            for tempTicker in gTickers:
                cmpStr = ticker.upper()
                if tempTicker.GetTicker() == cmpStr:
                    tempObject = gTickers.pop(count)
                    print(f"deleting: {cmpStr}")
                    del tempObject
                    break
                else:
                    count += 1

    else:
        print("skipping. no symbols entered\n")


# =======================================================================================
# displayHelp Handle argument parsing
# =======================================================================================
def displayHelp():
    print("\n Help Menu")
    print(" ---------")
    print("Type a 'q' or ESC to exit.")
    print("Type an 'a' to add new symbols to track.")
    print("Type an 'h' to display help.")
    print("Type an 'f' to toggle 52 week range display")
    print("Type an 'r' to set a new update rate in seconds")
    print(" ")
    

# =======================================================================================
# buildEmailMessage
# =======================================================================================
def cursesMain(stdscr):

    stdscr = curses.initscr()

    stdscr.clear()
    stdscr.addstr(10, 10, "Hello World!")
    stdscr.refresh()
    time.sleep(5)


# =======================================================================================
# buildEmailMessage
# =======================================================================================
def buildEmailMessage(inTicker, inValue, inName, inSubject,  inBodyTEXT, inBodyHTML, direction, chart):
    # outMessage = f"Subject:{inTicker}: {inValue} {inName} {inSubject} \n\n {inBody}"
    
    sender_email = "gme.dev.2003@gmail.com"
    receiver_email = "gme.dev.2003@gmail.com"

    message = MIMEMultipart("alternative")
    message["Subject"] = f"{chart} {direction} {inTicker}:  {inValue} {inName} {inSubject}"
    message["From"] = sender_email
    message["To"] = receiver_email    

    eol = "\n"
    br = "<br>"
    text = inBodyTEXT

    html = f"<html>{eol}"
    html += """
            <head>
            <style>
            table {
              font-family: helvetica, sans-serif;
              border-collapse: collapse;
              width: 20%;
            }
            th, td {
                padding: 5px;
            }
            td, th {
              border: 1px solid #dddddd;
              text-align: left;
              padding: 8px;
            }
            th {
              background-color:#0099ff;
              color:white
            }
            tr:nth-child(even) {
                background-color: #eeeeeee;
            }
            td span {
                text-align: right;
                display: inline-block;
            }
            </style>
            </head>
            """
    html += f" <body>{eol}"
    html += f" {inBodyHTML}<br>{eol}"
    html += f" </body>{eol}"
    html += f"</html>{eol}"

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)
    # print(message)
    return message
    # return outMessage


# =======================================================================================
# sendEmail
# =======================================================================================
def sendEmail(msg):
    port = 465  # For SSL
    password = "Testing$3512"
    sender_email = "gme.dev.2003@gmail.com"
    receiver_email = "gme.dev.2003@gmail.com"
    smtp_server = "smtp.gmail.com"
    
    # Create a secure SSL context
    context = ssl.create_default_context()
    debugLog(f"Sending email :{msg} ")
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())

# =======================================================================================
# queueEmail
# =======================================================================================
def queueEmail(in_message):
    global gEmailQueue
    gEmailQueue.put(in_message)


# =======================================================================================
# email thread_function
# =======================================================================================
def email_thread_function(name):
    global gEmailQueue
    print("Email processor starting")

    while True:
        temp_msg = gEmailQueue.get()
        debugLog(f"got message {temp_msg}")
        if temp_msg == kSTOP:
            print("Stopping Email processor")
            break
        sendEmail(temp_msg)
        debugLog("msg sent")

        time.sleep(.5)
        debugLog("check for email")
    print("Email processor stopped")


# =======================================================================================
# queueTicker
# =======================================================================================
def queueTicker(in_message):
    global gTickerQueue
    global gUseThreading

    if gUseThreading:
        gTickerQueue.put(in_message)


# =======================================================================================
# ticker thread_function
# =======================================================================================
def ticker_thread_function(name):
    global gTickerQueue
    print("ticker processor starting")
    running = True;

    while True:
        temp_msg = gTickerQueue.get()
        debugLog(f"got message {temp_msg}")
        if temp_msg == kSTOP:
            print("Stopping ticker processor")
            break

        debugLog(f"{temp_msg} tickers")
        if temp_msg == kPAUSE:
            running = False
            print("pausing ticker processor")

        if temp_msg == kUPDATE and not running:
            running = True
            print("resuming ticker processor")


        if running:
            handleTickerUpdate()
        UpdateMarketStatus()        
        
    print("ticker processor stopped")


# =======================================================================================
# myTickerFunc
# =======================================================================================
def myTickerFunc(e):
    return e.GetTicker()


# =======================================================================================
# myPercentChangeFunc
# =======================================================================================
def myPercentChangeFunc(e):
    return e.GetPercentChanged()


# =======================================================================================
# myVolumeFunc
# =======================================================================================
def myVolumeFunc(e):
    return e.GetVolume()


# =======================================================================================
# myIndexFunc
# =======================================================================================
def myIndexFunc(e):
    return e.GetIndex()


# =======================================================================================
# sortDict
# =======================================================================================
def sortDict(in_dict):
    sorted_age = sorted(in_dict.items(), key=lambda kv: kv[1])


# =======================================================================================
# sortList
# =======================================================================================
def sortList(in_list, item_to_sort):

    if item_to_sort == kSortOrderTickerAsc:
        in_list.sort(key=myTickerFunc)
    if item_to_sort == kSortOrderTickerDsc:
        in_list.sort(reverse=True, key=myTickerFunc)

    if item_to_sort == kSortOrderPercentAsc:
        in_list.sort(key=myPercentChangeFunc)
    if item_to_sort == kSortOrderPercentDsc:
        in_list.sort(reverse=True, key=myPercentChangeFunc)

    if item_to_sort == kSortOrderVolumeAsc:
        in_list.sort(key=myVolumeFunc)
    if item_to_sort == kSortOrderVolumeDsc:
        in_list.sort(reverse=True, key=myVolumeFunc)

    if item_to_sort == kSortOrderIndexAsc:
        in_list.sort( key=myIndexFunc)
    if item_to_sort == kSortOrderIndexDsc:
        in_list.sort(reverse=True, key=myIndexFunc)


# =======================================================================================
# SetSortOrder
# =======================================================================================
def SetSortOrder(newSortOrder):
    global gCurrentSortOrder

    if newSortOrder == kSortOrderTickerAsc:
        print("sorting by ticker ascending")
        gCurrentSortOrder = newSortOrder

    if newSortOrder == kSortOrderTickerDsc:
        print("sorting by ticker descending")
        gCurrentSortOrder = newSortOrder

    if newSortOrder == kSortOrderPercentAsc:
        print("sorting by Percent changed ascending")
        gCurrentSortOrder = newSortOrder

    if newSortOrder == kSortOrderPercentDsc:
        print("sorting by Percent changed descending")
        gCurrentSortOrder = newSortOrder

    if newSortOrder == kSortOrderVolumeAsc:
        print("sorting by Volume ascending")
        gCurrentSortOrder = newSortOrder

    if newSortOrder == kSortOrderVolumeDsc:
        print("sorting by Volume descending")
        gCurrentSortOrder = newSortOrder

    if newSortOrder == kSortOrderIndexAsc:
        print("sorting by Index ascending")
        gCurrentSortOrder = newSortOrder

    if newSortOrder == kSortOrderIndexDsc:
        print("sorting by Index descending")
        gCurrentSortOrder = newSortOrder

    if newSortOrder in valid_sort_options:
        sortList(gTickers, gCurrentSortOrder)

    UpdateHeaderString(isPostMarket())


# =======================================================================================
# handleSort
# =======================================================================================
def handleSort():
    global gCurrentSortOrder

    print(f'enter the number for how you want to sort the list:')
    print(f'{kSortOrderTickerAsc}) Ticker ascending')
    print(f'{kSortOrderTickerDsc}) Ticker descending')
    print(f'{kSortOrderPercentAsc}) Percent changed ascending')
    print(f'{kSortOrderPercentDsc}) Percent changed descending')
    print(f'{kSortOrderVolumeAsc}) Volume ascending')
    print(f'{kSortOrderVolumeDsc}) Volume descending')
    print(f'{kSortOrderIndexAsc}) Index ascending')
    print(f'{kSortOrderIndexDsc}) Index descending')
    print(f'return key to exit')

    newSortOrder = input()
    if newSortOrder:
        SetSortOrder(newSortOrder)


# =======================================================================================
# UpdateTickers
# =======================================================================================
def UpdateTickers():
    global gTickers
    for myTicker in gTickers:
        myTicker.Update()


# =======================================================================================
# handleTickerUpdate
# =======================================================================================
def handleTickerUpdate():
    global gShowTopMovers
    global gTopMoversTickers
    global gCurrentSortOrder
    global gTickerThread
    global gTickers
    global gHeaderStr

    now = datetime.datetime.now()

    # update the list of symbols
    UpdateTickers()

    # if the list is sorted update the sort list
    if gCurrentSortOrder:
        sortList(gTickers, gCurrentSortOrder)

    # if there are top movers to show
    if gTopMoversTickers:
        for myTicker in gTopMoversTickers:
            myTicker.Update()

    timeStr = now.strftime('%Y-%m-%d %H:%M:%S')

    print(f'{timeStr:<19}\n {gHeaderStr}')

    for myTicker in gTickers:
        myTicker.PrintTicker()

    if gTopMoversTickers:
        print('-')
        print(f" Top {gShowTopMovers} Movers")
        print('-')
        for myTicker in gTopMoversTickers:
            myTicker.PrintTicker()

    print('-')


# =======================================================================================
# main code
# =======================================================================================
def CheckSortOrder():
    global gCurrentSortOrder
    global gTickers
    global gCurrentSortOrder
    if gCurrentSortOrder:
        UpdateTickers()
        UpdateHeaderString(isPostMarket())
        sortList(gTickers, gCurrentSortOrder)

# =======================================================================================
# main code
# =======================================================================================
def main():
    global gShowFiftyTwo
    global gShowSorted
    global gMailThread
    global gSendEmail
    global gCurrentSortOrder
    global gTickerThread

    if gSendEmail:
        gMailThread = threading.Thread(target=email_thread_function, args=(1,))
        gMailThread.start()

    gColumns.append(HeaderRec(" ",2))
    gColumns.append(HeaderRec("Ticker",10))
    gColumns.append(HeaderRec("Name",26))
    gColumns.append(HeaderRec("Price",14))
    gColumns.append(HeaderRec("Open",8))
    gColumns.append(HeaderRec("% Chg",8))
    gColumns.append(HeaderRec("Lo    -    Hi", 14))
    gColumns.append(HeaderRec("52 wk low - high", 8))
    gColumns.append(HeaderRec("After Hours", 8))
    print("Enter q or esc to quit. h for help\n")

    # See if the market is open, pre or post. Quit if closed
    UpdateMarketStatus()

    # Top mover list building
    if gShowTopMovers:
        ShowTopMovers(gShowTopMovers, gTopMoversList)
        for ticker, name in gTopMoversList.items():
            gTopMoversTickers.append(Ticker(name, ticker))

    # build up main listing
    for ticker, tickerName in theTickers.items():
        tempTicker = Ticker(tickerName, ticker)
        tempTicker.SetIndex(len(gTickers))
        gTickers.append(tempTicker)

    if gUseThreading:
        gTickerThread = threading.Thread(target=ticker_thread_function, args=(1,))
        gTickerThread.start()

    kb = KBHit()

    CheckSortOrder()

    # main while loop

    while 1:
        if not gUseThreading:
            handleTickerUpdate()
        else:
            queueTicker(kUPDATE)

        if isMarketClosed():
            print("Market is now closed.")
            exit()

        count = updateRate * 100
        while count:
            if kb.kbhit():
                c = kb.getch()
                if ord(c) == 27 or c == 'q':    # ESC or quit
                    print('stopping...')
                    if gSendEmail:
                        queueEmail(kSTOP)
                        time.sleep(1)
                    if gUseThreading:
                        queueTicker(kSTOP)
                        time.sleep(1)                        
                    print('done')
                    exit()
                if c == 'a':                    # add symbols
                    kb.set_normal_term()
                    addSymbol()
                    CheckSortOrder()
                    kb = KBHit()
                    count = 0
                    break
                if c == 'd':                    # delete symbols
                    kb.set_normal_term()
                    deleteSymbol()
                    CheckSortOrder()
                    kb = KBHit()
                    count = 0
                    break
                if c == 'r':                    # set a new rate
                    kb.set_normal_term()
                    queueTicker(kPAUSE)
                    setRate()
                    kb = KBHit()
                    count = 0
                    break
                if c in valid_sort_options:     # fast access to sort options
                    SetSortOrder(c)
                    count = 0
                    break
                if c == 's':                    # sort menu
                    kb.set_normal_term()
                    queueTicker(kPAUSE)
                    handleSort()
                    kb = KBHit()
                    count = 0
                    break
                if c == 'f':                    # set the option for 52 week view
                    gShowFiftyTwo = not gShowFiftyTwo
                    tempStr = f"Setting 52 week option "
                    tempStr += "on" if gShowFiftyTwo else "off"
                    print(tempStr)
                    count = 0

                    break
                if c == 'h':
                    queueTicker(kPAUSE)
                    displayHelp()
                    count = 0
                    break
            if count == 0:
                if gUseThreading:
                    print("sending an update message")
                    queueTicker(kUPDATE)
            else:
                count -= 1
            time.sleep(.01)  # Sleep for 10ms seconds

            if not gUseThreading:
                UpdateMarketStatus()
    kb.set_normal_term()


# curses support
if gUseCurses:
    curses.wrapper(cursesMain)
else:
    main()
