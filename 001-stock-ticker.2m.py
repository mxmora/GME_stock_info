#!/usr/local/bin/python3

# <xbar.title>Stock Ticker</xbar.title>
# <xbar.version>1.1</xbar.version>
# <xbar.author>Matt Mora</xbar.author>
# <xbar.author.github>?</xbar.author.github>
# <xbar.desc>Provides a rotating stock ticker in your menu bar, with color and percentage changes</xbar.desc>
# <xbar.dependencies>python</xbar.dependencies>
# <xbar.image>https://i.imgur.com/Nf4jiRd.png</xbar.image>
# <xbar.abouturl>?</xbar.abouturl>
 
from yahoo_fin import stock_info as si
import json
import pandas as pd

# -----------------------------------------------------------------------------
# Enter your stock symbols here in the format: ["symbol1", "symbol2", ...]
# stock_symbols = ["MSFT", "AAPL", "GME","AMC","SQ"]
# -----------------------------------------------------------------------------

gTickers = []
kMARKET = 'MARKET'
gFileName = "/Users/mmora/Dev/GME_stock_info/stocks.txt" 
downArrow = '⬇'
upArrow = '⬆'
font="Menlo"
font_size="16"
after_hours = False


# =======================================================================================
# GetQuoteData
# =======================================================================================
def GetQuoteData(tickerSymbol):
    quoteData = ''

    #print(f"+GetQuoteData: {tickerSymbol}")
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
    except Exception as e:
        print(e.__doc__)
        print(e.message)
        pass

    #print(f"-GetQuoteData: ")
    return quoteData


# this is a wonky way to get status
qd = GetQuoteData(kMARKET)

if qd == '' :
    print("no connection")
    exit()
    
status = si.get_market_status()

#print(f"$ {status}")
# status == "POST" or
if status == "POSTPOST" or status == "CLOSED":
    if status == "POSTPOST":
        tempStr = "$ After after hours  "
    else:
        tempStr = "$ Market closed"

    print(tempStr)
    exit()
else:
    print("loading...")

if status == "POST":
    tempStr = "$ After hours  "
    after_hours = True
    
    
with open(gFileName) as f:
    data = f.read()
    theTickers = json.loads(data)
    # print(theTickers)
    

row_list = []

stock_symbols = []
stock_dict = {}

topStr = ""
outputStr = ""
df = pd.DataFrame(columns=['Ticker', 'Name' ,'Price', 'Price Chng', '% Chng', 'Day Lo', 'Day Hi','52w Lo', '52w Hi','Vol','Open','Prev close'])


for ticker, tickername in theTickers.items():
    stock_symbols.append(ticker.upper())
    stock_dict[ticker.upper()] = tickername


for stock_symbol in stock_symbols:
    stock_quote = si.get_quote_data(stock_symbol)
    price_current = float(stock_quote['regularMarketPrice'])
    price_changed = float(stock_quote['regularMarketChange'])

    price_percent_changed = float(stock_quote['regularMarketChangePercent'])
    # print(stock_symbol)

    postStr = " "

    if after_hours:
        postStr = "P "
        after_market_price = float(stock_quote.get('postMarketPrice', 0))
        after_market_percent_changed = float(stock_quote.get('postMarketChangePercent', 0))
        after_market_price_changed = float(stock_quote.get('postMarketChange', 0))
        price_changed = after_market_price_changed  # price_current - after_market_price
        price_percent_changed = after_market_percent_changed  # (((price_current - after_market_price) / after_market_price) * 100) if (after_market_price != 0) else 0
        price_current = after_market_price
        # print(f"After: {price_changed} {after_market_price} {price_percent_changed}")
        
    stock_name = stock_dict[stock_symbol]

    lastRegularMarketDayLow = float(stock_quote['regularMarketDayLow'])
    lastRegularMarketDayHigh = float(stock_quote['regularMarketDayHigh'])
    lastFiftyTwoWeekLow = float(stock_quote['fiftyTwoWeekLow'])
    lastFiftyTwoWeekHigh = float(stock_quote['fiftyTwoWeekHigh'])
    marketVolume = int(stock_quote['regularMarketVolume'])
    tickerOpen = float(stock_quote['regularMarketOpen'])
    tickerPrevClose = float(stock_quote['regularMarketPreviousClose'])
    
    row_list.append(stock_symbol)       # ticker
    row_list.append(stock_name)         # name
    row_list.append(price_current)      # price
    row_list.append(price_changed)
    row_list.append(price_percent_changed)
    row_list.append(lastRegularMarketDayLow)
    row_list.append(lastRegularMarketDayHigh)
    row_list.append(lastFiftyTwoWeekLow)
    row_list.append(lastFiftyTwoWeekHigh)
    row_list.append(marketVolume)
    row_list.append(tickerOpen)
    row_list.append(tickerPrevClose)
    
    df.loc[len(df.index)] = row_list
    
    row_list = []
    stock_quote = ""
    paddedstr = stock_symbol + "        "
    
    if price_changed is not None:
        color = "red" if float(price_changed) < 0 else "green"
        arrow = downArrow if float(price_changed) < 0 else upArrow
        topStr += f"{arrow} { paddedstr[0:8]}  {price_current:8.2f}{postStr} ${price_changed:8.2f}  ({price_percent_changed:.2f}%) | trim=false color={color}\n"
    else:
        color = "black"
        topStr += f"{paddedstr[0:8]} {price_current:8.2f} | trim=false color={color}\n"

sorted_df = df.sort_values(by='% Chng', ascending=False)

versionStr = "        version 1.1"
outputStr = f"{versionStr}"
outputStr += f"| font=Menlo-Bold size=12 trim=false color=blue\n"


for index, row in sorted_df.iterrows():
    stock_symbol = row.get(key = 'Ticker')
    paddedstr = stock_symbol + "        "
    stock_name = row.get(key = 'Name')
    price_current = row.get(key = 'Price')
    price_changed = row.get(key = 'Price Chng')
    price_percent_changed = row.get(key = '% Chng')
    lastRegularMarketDayLow = row.get(key = 'Day Lo')
    lastRegularMarketDayHigh = row.get(key = 'Day Lo')
    lastFiftyTwoWeekLow = row.get(key = '52w Lo')
    lastFiftyTwoWeekHigh = row.get(key = '52w Hi')
    marketVolume = row.get(key = 'Vol')
    tickerOpen = row.get(key = 'Open')
    tickerPrevClose = row.get(key = 'Prev close')
    
    if price_changed is not None:
        color = "red" if float(price_changed) < 0 else "green"
        arrow = downArrow if float(price_changed) < 0 else upArrow
        outputStr += f"{arrow} {paddedstr[0:8]} ${price_current:9.2f}{postStr} {price_percent_changed:.2f}%  "
    else:
        color = "black"
        outputStr += f" {paddedstr[0:8]} ${price_current:9.2f} "

    outputStr += f"| href=https://finance.yahoo.com/quote/{stock_symbol}?"
    outputStr += f"| font=Menlo-Bold size={font_size} trim=false color={color}\n"
    
    centered_name = stock_name.center(30)
    menuStyle = f"| font={font} size={font_size} trim=false color=blue\n"
    outputStr += f"--{centered_name} | font=Menlo-Bold size={font_size} trim=false color=black\n"
    outputStr += f"--Price:          {price_current:15.2f} {menuStyle}"
    outputStr += f"--Open Price:     {tickerOpen:15.2f} {menuStyle}"
    outputStr += f"--Previous Close: {tickerPrevClose:15.2f} {menuStyle}"
    outputStr += f"--$Changed:       {price_changed:15.2f} {menuStyle}"
    outputStr += f"--%Changed:       {price_percent_changed:15.2f}% {menuStyle}"
    outputStr += f"--Day Low:        {lastRegularMarketDayLow:15.2f} {menuStyle}"
    outputStr += f"--Day High:       {lastRegularMarketDayHigh:15.2f} {menuStyle}"
    outputStr += f"--52 wk Low:      {lastFiftyTwoWeekLow:15.2f} {menuStyle}"
    outputStr += f"--52 wk High:     {lastFiftyTwoWeekHigh:15.2f} {menuStyle}"
    outputStr += f"--Volume:      {marketVolume:>18,d} {menuStyle}"

print(topStr, end="")
print("---")
print(outputStr, end="")
