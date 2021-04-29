#!/usr/bin/env python3

# import stock_info module from yahoo_fin
from yahoo_fin import stock_info as si
import time
import datetime
import argparse
import sys
import os
# import curses
import smtplib, ssl
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
            msvcrt.getch() # skip 0xE0
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
            dr,dw,de = select([sys.stdin], [], [], 0)
            return dr != []


# =======================================================================================
# Globals
# =======================================================================================
gEmailQueue = que.Queue(maxsize = 100)
gMailThread = None

gShowFiftyTwo = 0
gShowSorted = True
gSendEmail = False

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
    
    gHeaderStr = " Ticker   " # symbol
    gHeaderStr += "Name                      "
    gHeaderStr += "Price         "
    gHeaderStr += "Open    "
    gHeaderStr += "% Chg   "
    if not afterMarket:
        gHeaderStr += "         Lo    -    Hi"
    if gShowFiftyTwo:
        gHeaderStr += "          52 wk low - high"
    if not afterMarket:
        gHeaderStr += "                   Volume"
    if afterMarket:
        gHeaderStr += "         After Hours "
                    

# =======================================================================================
# handle argument parsing
# =======================================================================================
parser = argparse.ArgumentParser(description='Show a list of stock tickers. It will show the current price is market is open, after hours price and volume. (default is GME, APPL, TSLA and AMC)')
parser.add_argument('--verbose', help='Enable verbose output. Mostly for debugging', action='store_true')
parser.add_argument('--alert', help='Ring the bell on new lows and new highs', action='store_true')
parser.add_argument('--top', type=int, default=0, help='Show top moving stocks, provide a number less than 100')
parser.add_argument('--rate', type=int, help='How many seconds to pause between updates.', )
parser.add_argument('--fiftytwo', help='Show the 52 week high low', action='store_true')
parser.add_argument('--curses', help='Show the list using curses.', action='store_true')
parser.add_argument('--email', help='If alerts are on, send an email too', action='store_true')
parser.add_argument('tickers', metavar='symbols', type=str, nargs='*', help='A one or more stock symbols that you want to display.')

args = parser.parse_args()
gLogOutput = args.verbose
gShowTopMovers = args.top
gShowFiftyTwo = args.fiftytwo
gBell = args.alert
gUseCurses = args.curses
gSendEmail = args.email


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

        self.tickerSymbol = sym.upper()
        self.tickerName = name
        self.percentChangeSinceOpen = 0
        self.percentChangeSinceClose = 0
        self.percentChange = 0
        self.aftermarketPrice = 0
        self.aftermarket = 0
        self.previousClose = 0
        self.lastPercentChange = 0
        self.timeToPrint = 0
        
        self.GetQuoteData()
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
        newMarketColor = ''
        warningStr = ' '
        warningColor = rst
        invertText = False
        invertBkgndColor = bg.black;
        invertBkgndColor = fg.lightgreen;

        
        if newLowStr != '':
            newMarketDir = downArrow
            newMarketStr = newLowStr
            newMarketColor = bg.red
            warningStr = downArrow
            warningColor = bg.red
            invertText = True
            invertBkgndColor = bg.red
            invertFgColor = fg.lightgreen

        if newHighStr != '':
            newMarketDir = upArrow
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
                outputStr += f" [ {self.fiftyTwoWeekLow:9.2f} - {self.fiftyTwoWeekHigh:9.2f} ] {rst}"
            outputStr += f" {self.aftermarketPrice:9.2f} {self.percentChangeSinceClose:5.1f}%"
        else:
            outputStr += f" [ {self.regularMarketDayLow:9.2f} - {self.regularMarketDayHigh:9.2f} ] {rst}"
            if gShowFiftyTwo:
                outputStr += f" [ {self.fiftyTwoWeekLow:9.2f} - {self.fiftyTwoWeekHigh:9.2f} ] {rst}"
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
            curValStr = f"{self.currentVal:9.2f}"

            tempMsg = buildEmailMessage(tempSymbol, curValStr, self.tickerName,  newMarketStr, f"{tempSymbol}: {self.tickerName} {newMarketStr} \n\n {outputStr} \n")
            # print(outputStr)
            queueEmail(tempMsg)
    def GetQuoteData(self):
        try:
            self.quoteData = si.get_quote_data(self.tickerSymbol)

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
            
    def Update(self):
        global gHeaderStr
        self.updateTime = datetime.datetime.now()
        self.lastVal = self.currentVal
        self.lastRegularMarketDayLow = min(self.regularMarketDayLow, self.lastRegularMarketDayLow)
        self.lastRegularMarketDayHigh = max(self.regularMarketDayHigh, self.lastRegularMarketDayHigh)
        self.lastFiftyTwoWeekLow = min(self.fiftyTwoWeekLow, self.lastFiftyTwoWeekLow)
        self.lastFiftyTwoWeekHigh = max(self.fiftyTwoWeekHigh,self.lastFiftyTwoWeekHigh)
                
        # self.currentVal = si.get_live_price(self.tickerSymbol)
        self.GetQuoteData()
 
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
                self.aftermarketPrice = si.get_postmarket_price(self.tickerSymbol)
            self.previousClose = self.currentVal
            self.percentChangeSinceClose = 0 if self.previousClose == 0 else ((self.aftermarketPrice - self.previousClose) / self.previousClose) * 100

        self.lastPercentChange = self.percentChange
        self.percentChange = 0 if self.tickerPrevClose == 0 else ((self.currentVal - self.tickerPrevClose) / self.tickerPrevClose) * 100
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


# ------------------------------------------
def UpdateMarketStatus():
    global pre_pre_market
    global pre_market
    global post_market
    global market_closed
    global regular_market

    try:
        market_status = si.get_market_status()
    except KeyboardInterrupt:
        pass

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
# Add a symbols(s) to the current display
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
# handle argument parsing
# =======================================================================================
def displayHelp():
    print("\n Help Menu")
    print(" ---------")
    print("Type a 'q' or ESC to exit.")
    print("Type an 'a' to add new symbols to track.")
    print("Type an 'h' to display help.")
    print("Type an 'f' to toggle 52 week range display")
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
def buildEmailMessage(inTicker, inValue, inName, inSubject,  inBody):
    outMessage = f"Subject:{inTicker}: {inValue} {inName} {inSubject} \n\n {inBody}"
    return outMessage


# =======================================================================================
# sendEmail
# =======================================================================================
def sendEmail(msg):
    port = 465  # For SSL
    password = "Testing$3512"
    sender_email = "gme.dev.2003@gmail.com"
    receiver_email = "mxmora@gmail.com"
    smtp_server = "smtp.gmail.com"
    
    # Create a secure SSL context
    context = ssl.create_default_context()
    # print(f"Sending email :{msg} ")
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg)


# =======================================================================================
# queueEmail
# =======================================================================================
def queueEmail(in_message):
    global gEmailQueue;
    gEmailQueue.put(in_message)


def thread_function(name):
    global gEmailQueue
    print("Email processor starting")

    while True:
        temp_msg = gEmailQueue.get()
        debugLog(f"got message {temp_msg}")
        if temp_msg == "STOP":
            print("Stopping Email processor")
            break
        sendEmail(temp_msg)
        debugLog("msg sent")

        time.sleep(.5)
        debugLog("check for email")

    print("Email processor stopped")


# =======================================================================================
# sortDict
# =======================================================================================
def sortDict(in_dict):
    sorted_age = sorted(in_dict.items(), key=lambda kv: kv[1])

# =======================================================================================
# main code
# =======================================================================================
def main():
    global gShowFiftyTwo
    global gShowSorted
    global gMailThread
    global gSendEmail

    if gSendEmail:
        gMailThread = threading.Thread(target=thread_function, args=(1,))
        gMailThread.start()

    gColumns.append(HeaderRec(" ",2))
    gColumns.append(HeaderRec("Ticker",10))
    gColumns.append(HeaderRec("Name",26))
    gColumns.append(HeaderRec("Price",14))
    gColumns.append(HeaderRec("Open",8))
    gColumns.append(HeaderRec("% Chg",8))
    gColumns.append(HeaderRec("Lo    -    Hi",14))
    gColumns.append(HeaderRec("52 wk low - high",8))
    gColumns.append(HeaderRec("After Hours",8))

    print("Enter q or esc to quit. h for help\n")

    # See if the market is open, pre or post. Quit if closed
    UpdateMarketStatus()

    # Top mover list building

    if gShowTopMovers:
        ShowTopMovers(showTopMovers, gTopMoversList)
        for ticker, name in gTopMoversList.items():
            gTopMoversTickers.append(Ticker(name, ticker))


    # build up main listing
    for ticker, tickerName in theTickers.items():
        gTickers.append(Ticker(tickerName, ticker))

    kb = KBHit()

    # main while loop
    while 1:
        UpdateMarketStatus()
        now = datetime.datetime.now()

        # update the list of symbols
        for myTicker in gTickers:
            myTicker.Update()

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

        if isMarketClosed():
            print("Market is now closed.")
            exit()

        print('-')

        count = updateRate * 100
        while count:
            if kb.kbhit():
                c = kb.getch()
                if ord(c) == 27 or c == 'q':  # ESC
                    print('stopping...')
                    if gSendEmail:
                        queueEmail("STOP")
                        time.sleep(1)
                    print('done')
                    exit()
                if c == 'a':
                    kb.set_normal_term()
                    addSymbol()
                    kb = KBHit()
                    break
                if c == 'f':
                    gShowFiftyTwo = not gShowFiftyTwo
                    tempStr = f"Setting 52 week option "
                    tempStr += "on" if gShowFiftyTwo else "off"
                    print(tempStr)
                    count = 1
                    break
                if c == 'h':
                    displayHelp()
                    count = 1
                    break
            count -= 1
            time.sleep(.01)  # Sleep for 10ms seconds

    kb.set_normal_term()


# curses support
if gUseCurses:
    curses.wrapper(cursesMain)
else:
    main()
