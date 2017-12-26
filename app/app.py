#!/usr/local/bin/python

import os
import json
import time
from bittrex import Bittrex
from twilio.rest import Client

# Read in the configurtion
with open("secrets.json") as secrets_file:
    secrets = json.load(secrets_file)
    secrets_file.close()

CONFIG = {
    'bittrex_key': os.environ.get('BITTREX_KEY', secrets['bittrex_key']),
    'bittrex_secret': os.environ.get('BITTREX_SECRET', secrets['bittrex_secret']),
    'twilio_key': os.environ.get('TWILIO_KEY', secrets['twilio_key']),
    'twilio_secret': os.environ.get('TWILIO_SECRET', secrets['twilio_secret']),
    'twilio_phone_number': os.environ.get('TWILIO_PHONE_NUMBER', secrets['my_number'])
}

# Let's test an API call to get our BTC balance as a test
# print(BITTREX_CLIENT.get_balance('BTC')['result']['Balance'])

COIN_PAIRS = ['BTC-ETH', 'BTC-OMG', 'BTC-GNT', 'BTC-CVC', 'BTC-BAT', 'BTC-STRAT', 'BTC-LSK', 'BTC-BCC', 'BTC-NEO', 'BTC-OK', 'BTC-TRIG', 'BTC-PAY', 'BTC-XMR']

#print(historical_data = BITTREX_CLIENT.getHistoricalData('BTC-ETH', 30, "thirtyMin"))
def getClosingPrices(coin_pair, period, unit):
    """
    Returns closing prices within a specified time frame for a coin pair
    :type coin_pair: str
    :type period: str
    :type unit: int
    :return: Array of closing prices
    """

    historical_data = BITTREX_CLIENT.getHistoricalData(coin_pair, period, unit)
    closing_prices = []
    for i in historical_data:
        closing_prices.append(i['C'])
    return closing_prices

def calculateSMA(coin_pair, period, unit):
    """
    Returns the Simple Moving Average for a coin pair
    """

    total_closing = sum(getClosingPrices(coin_pair, period, unit))
    return (total_closing / period)

def calculateEMA(coin_pair, period, unit):
    """
    Returns the Exponential Moving Average for a coin pair
    """

    closing_prices = getClosingPrices(coin_pair, period, unit)
    previous_EMA = calculateSMA(coin_pair, period, unit)
    constant = (2 / (period + 1))
    current_EMA = (closing_prices[-1] * (2 / (1 + period))) + (previous_EMA * (1 - (2 / (1 + period))))
    return current_EMA

# Improvemnts to calculateRSI are courtesy of community contributor "pcartwright81"
def calculateRSI(coin_pair, period, unit):
    """
    Calculates the Relative Strength Index for a coin_pair
    If the returned value is above 70, it's overbought (SELL IT!)
    If the returned value is below 30, it's oversold (BUY IT!)
    """
    closing_prices = getClosingPrices(coin_pair, period * 3, unit)
    count = 0
    change = []
    # Calculating price changes
    for i in closing_prices:
        if count != 0:
            change.append(i - closing_prices[count - 1])
        count += 1
        if count == 15:
           break
    # Calculating gains and losses
    advances = []
    declines = []
    for i in change:
        if i > 0:
            advances.append(i)
        if i < 0:
            declines.append(abs(i))
    average_gain = (sum(advances) / 14)
    average_loss = (sum(declines) / 14)
    newAvgGain = average_gain
    newAvgLoss = average_loss
    for i in closing_prices:
        if count > 14 and count < len(closing_prices):
          close = closing_prices[count]
          newChange = close - closing_prices[count - 1]
          addLoss = 0;
          addGain = 0;
          if newChange > 0:
              addGain = newChange
          if newChange < 0:
              addLoss = abs(newChange)
          newAvgGain = (newAvgGain * 13 + addGain) / 14
          newAvgLoss = (newAvgLoss * 13 + addLoss) / 14
          count += 1

    rs = newAvgGain / newAvgLoss;
    newRS = 100 - 100 / (1 + rs);
    return newRS


def calculateBaseLine(coin_pair, unit):
    """
    Calculates (26 period high + 26 period low) / 2
    Also known as the "Kijun-sen" line
    """

    closing_prices = getClosingPrices(coin_pair, 26, unit)
    period_high = max(closing_prices)
    period_low = min(closing_prices)
    return (period_high + period_low) / 2

def calculateConversionLine(coin_pair, unit):
    """
    Calculates (9 period high + 9 period low) / 2
    Also known as the "Tenkan-sen" line
    """
    closing_prices = getClosingPrices(coin_pair, 9, unit)
    period_high = max(closing_prices)
    period_low = min(closing_prices)
    return (period_high + period_low) / 2

def calculateLeadingSpanA(coin_pair, unit):
    """
    Calculates (Conversion Line + Base Line) / 2
    Also known as the "Senkou Span A" line
    """

    base_line = calculateBaseLine(coin_pair, unit)
    conversion_line = calculateConversionLine(coin_pair, unit)
    return (base_line + conversion_line) / 2

def calculateLeadingSpanB(coin_pair, unit):
    """
    Calculates (52 period high + 52 period low) / 2
    Also known as the "Senkou Span B" line
    """
    closing_prices = getClosingPrices(coin_pair, 52, unit)
    period_high = max(closing_prices)
    period_low = min(closing_prices)
    return (period_high + period_low) / 2

def findBreakout(coin_pair, period, unit):
    """
    Finds breakout based on how close the High was to Closing and Low to Opening
    """
    hit = 0
    historical_data = BITTREX_CLIENT.getHistoricalData(coin_pair, period, unit)
    for i in historical_data:
        if (i['C'] == i['H']) and (i['O'] == i['L']):
            hit += 1

    if (hit / period) >= .75:
        message = TWILIO_CLIENT.api.account.messages.create(to=secrets['my_number'],from_=secrets['twilio_number'],body="{} is breaking out!".format(coin_pair))
        return "Breaking out!"
    else:
        return "#Bagholding"

def get_signal():
    for coin_pair in COIN_PAIRS:
        breakout = findBreakout(coin_pair=coin_pair, period=5, unit="fiveMin")
        rsi = calculateRSI(coin_pair=coin_pair, period=14, unit="thirtyMin")
        print("{}: \tBreakout: {} \tRSI: {}".format(coin_pair, breakout, rsi))
    time.sleep(300)

if __name__ == "__main__":
    BITTREX_CLIENT = Bittrex(CONFIG['bittrex_key'], CONFIG['bittrex_secret'])
    TWILIO_CLIENT = Client(CONFIG['twilio_key'], CONFIG['twilio_secret'])

    while True:
        get_signal()