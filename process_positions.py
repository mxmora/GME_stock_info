#!/usr/bin/env python3
import json
import pandas as pd
import os
import sys
from yahoo_fin import stock_info as si

kDisplayName = 'displayName'

if (len(sys.argv) > 1):
    gFileName = sys.argv[1]
    print(f"Processing file: {gFileName}\n")
else:
    print("error no file name.  Pass in filename to process")
    exit(1)
    
if os.path.isfile(gFileName):
    df = pd.read_table(gFileName, header=0, engine='python', skiprows=7,skipfooter=4,usecols=[0,1,2])
    print(df)

    Symbol_list = df["Symbol"].values.tolist()
    print(Symbol_list)

    Name_list = []

    for symbol in Symbol_list:
        quoteData = si.get_quote_data(symbol)

        try:
            tempStr = quoteData[kDisplayName]
            print(f"displayName: {tempStr}")
        except KeyError:
            tempStr = quoteData['shortName']
            print(f"shortName  : {tempStr}")

        Name_list.append(tempStr)

#print(Name_list)
newDict = dict(zip(Symbol_list, Name_list))

print(newDict)
newFileName = "newStocks.txt"

print(f"writeing file {newFileName}")
with open(newFileName, 'w') as convert_file:
    convert_file.write(json.dumps(newDict))

print("Done")

