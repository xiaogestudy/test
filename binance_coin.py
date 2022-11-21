"""
Binance Future http requests.
币安币本位合约api
"""
import requests
import time
import hmac
import hashlib
import pandas as pd
from enum import Enum
from datetime import datetime
import os
pd.set_option("expand_frame_repr", False)
class OrderStatus(object):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
class RequestMethod(Enum):
    """
    请求的方法.
    """
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'
class Interval(Enum):
    """
    请求的K线数据..
    """
    MINUTE_1 = '1m'
    MINUTE_3 = '3m'
    MINUTE_5 = '5m'
    MINUTE_15 = '15m'
    MINUTE_30 = '30m'
    HOUR_1 = '1h'
    HOUR_2 = '2h'
    HOUR_4 = '4h'
    HOUR_6 = '6h'
    HOUR_8 = '8h'
    HOUR_12 = '12h'
    DAY_1 = '1d'
    DAY_3 = '3d'
    WEEK_1 = '1w'
    MONTH_1 = '1M'
class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"
class BinanceFutureHttp(object):

    def __init__(self, api_key=None, secret=None, symbol=None,size=None,timeout=5):
        self.key = api_key
        self.secret = secret
        self.host = "https://dapi.binance.com"
        self.recv_window = 5000
        self.timeout = timeout
        self.symbol = symbol
        self.size = size

    def build_parameters(self, params: dict):
        keys = list(params.keys())
        keys.sort()
        return '&'.join([f"{key}={params[key]}" for key in params.keys()])

    def request(self, req_method: RequestMethod, path: str, requery_dict=None, verify=False):
        url = self.host + path
        if requery_dict:
            requery_dict['recvWindow'] = 50000
        if verify:
            query_str = self._sign(requery_dict)
            url += '?' + query_str
        elif requery_dict:
            url += '?' + self.build_parameters(requery_dict)
        # print(url)
        headers = {"X-MBX-APIKEY": self.key}

        try:
            response = requests.request(req_method.value, url=url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                print(response.text)
                print(f"请求没有成功: {response.status_code}")
        except Exception as error:
            print(f"请求:{path}, 发生了错误: {error}, 时间: {datetime.now()}")
    def get_kline(self, interval: Interval, start_time=None, end_time=None,max_try_time=10):
        path = "/dapi/v1/klines"

        query_dict = {
            "symbol": self.symbol,
            "interval": interval.value,
            "limit": self.size
        }

        if start_time:
            query_dict['startTime'] = start_time

        if end_time:
            query_dict['endTime'] = end_time

        for i in range(max_try_time):
            data = self.request(RequestMethod.GET, path, query_dict)
            if isinstance(data, list) and len(data):
                return data
    def get_latest_price(self):
        path = "/dapi/v1/ticker/price"
        query_dict = {"symbol": self.symbol}
        return self.request(RequestMethod.GET, path, query_dict)
    def exchangeInfo(self):
        path = '/dapi/v1/exchangeInfo'
        return self.request(req_method=RequestMethod.GET, path=path)
    ########################### the following request is for private data ########################
    def _timestamp(self):
        return int(time.time() * 1000)
    def _sign(self, params):

        requery_string = self.build_parameters(params)
        hexdigest = hmac.new(self.secret.encode('utf8'), requery_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return requery_string + '&signature=' + str(hexdigest)
    def cancel_open_orders(self):
        path = "/dapi/v1/allOpenOrders"
        params = {"timestamp": self._timestamp(),
                  "symbol": self.symbol
                  }
        return self.request(RequestMethod.DELETE, path, params, verify=True)
    def get_position_info(self):
        path = "/dapi/v1/positionRisk"
        params = {"timestamp": self._timestamp()}
        return self.request(RequestMethod.GET, path, params, verify=True)
    def get_balance_info(self):
        path = "/dapi/v1/balance"
        params = {"timestamp": self._timestamp()}
        return self.request(RequestMethod.GET, path, params, verify=True)
    def limit_sell(self, quantity,price):
        path = '/dapi/v1/order'
        params = {
            "symbol": self.symbol,
            "side": OrderSide.SELL.value,
            "positionSide": "SHORT",
            "type": OrderType.LIMIT.value,
            "quantity": quantity,
            "price": price,
            "recvWindow": 50000,
            "timeInForce": "GTC",  # 成交为止, 一直有效
            "timestamp": self._timestamp()
        }
        return self.request(RequestMethod.POST, path=path, requery_dict=params, verify=True)
    def market_buy(self, quantity):
        path = '/dapi/v1/order'
        params = {
            "symbol": self.symbol,
            "side": OrderSide.BUY.value,
            "type": OrderType.MARKET.value,
            "quantity": quantity,
            "timestamp": self._timestamp()
        }
        # print(params)
        return self.request(RequestMethod.POST, path=path, requery_dict=params, verify=True)
    def market_sell(self, quantity):
        path = '/dapi/v1/order'
        params = {
            "symbol": self.symbol,
            "side": OrderSide.SELL.value,
            "type": OrderType.MARKET.value,
            "quantity": quantity,
            "recvWindow": 50000,
            "timestamp": self._timestamp()
        }
        print(params)
        return self.request(RequestMethod.POST, path=path, requery_dict=params, verify=True)
    def all_orders(self):
        path = '/dapi/v1/allOrders'
        params = {
            "symbol": self.symbol,
            "recvWindow": 50000,
            "timestamp": self._timestamp()
        }
        return self.request(RequestMethod.GET, path, params, verify=True)
if __name__ == '__main__':
    key = os.getenv('binancekey')
    secret = os.getenv('binancesecret')
    symbol = 'OPUSD_PERP'
    size = 10
    binance = BinanceFutureHttp(api_key=key, secret=secret, symbol=symbol, size=size)
    a = binance.all_orders()
    for i in a:
        print(i)
    # a = binance.exchangeInfo()['symbols']
    # for i in a:
    #     print(i['symbol'])
    #     if 'THE' in i['symbol']:
    #         print(i)
    # a = binance.get_latest_price()
    # print(a)
    # print(a[0]['price'])
    # binance.market_buy(2)
    # binance.market_sell(2)
    # binance.limit_sell(1,5)
    # binance.cancel_open_orders()
    # position = binance.get_position_info()
    # print(position)
    # for i in position:
    #     if i['symbol'] == symbol:
    #         print(i)
    #         print(i['positionAmt'])
    # while True:
    #     time.sleep(2)
    #     position = binance.get_balance_info()
    #     # print(position)
    #     for i in position:
    #         if i['asset'] == 'APE':
    #             print(i)
    #             availableBalance = i['availableBalance']
    #             availableBalance = float(availableBalance)
    #             balance = i['balance']
    #             balance = float(balance)
    #             crossUnPnl = i['crossUnPnl']
    #             crossUnPnl = float(crossUnPnl)
    #             condition_position_zero = availableBalance == balance and crossUnPnl == 0
    #             print(condition_position_zero)

