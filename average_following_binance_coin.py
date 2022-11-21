from binance_coin import BinanceFutureHttp
import pandas as pd
import time
import datetime
import requests
import json

pd.set_option("expand_frame_repr", False)


# 币安均线跟随交易
class TestStrategy(object):
    def __init__(self, http_client: BinanceFutureHttp,
                 symbol=None,
                 period=None,
                 transfer_period=None,
                 short_num=None,
                 long_num=None,
                 start_size=None,
                 add_size=None,
                 only_buy=False,
                 only_sell=False):
        # about init
        self.http_client = http_client
        self.symbol = symbol
        self.period = period
        self.strategy_status = False  # false 初始化参数  ture参数初始化完成
        # about account 变动
        self.position_value = 100000
        self.earning_status = False
        self.ma_short = 0
        self.ma_long = 0
        self.stop_amount = 0
        # 调优
        self.short_num = short_num
        self.long_num = long_num
        self.transfer_period = transfer_period
        self.start_size = start_size
        self.add_size = add_size
        self.only_buy = only_buy
        self.only_sell = only_sell
    def init_acount(self):
        self.msg('账户初始化#########')
        # 初始化参数
        self.strategy_status = False
        self.position_value = 100000
        self.earning_status = False
        self.stop_amount = 0
        self.init_data()

    def init_data(self):
        condition_position_ok = self.position_value < 100000
        condition_ma_ok = self.ma_short > 0 and self.ma_short > 0
        if not condition_ma_ok:
            self.get_ma()
        if not condition_position_ok:
            self.get_position()
        if condition_ma_ok and condition_position_ok:
            print("数据已就绪")
            self.strategy_status = True
            self.log_debug()
        else:
            self.strategy_status = False
            time.sleep(2)

    # about account
    def get_position(self):
        try:
            pos_list = self.http_client.get_position_info()
        except Exception as e:
            print(f"【异常信息】【获取账户仓位信息异常】：{e}")
        else:
            self.formart_position(pos_list)

    def formart_position(self, pos_list):
        try:
            if isinstance(pos_list, list):
                for i in pos_list:
                    if i['symbol'] == self.symbol:
                        position_value = i['positionAmt']
                        position_value = int(position_value)
                        self.position_value = position_value
                        entryPrice = float(i['entryPrice'])
                        markPrice = float(i['markPrice'])
                        if position_value > 0:
                            if markPrice > entryPrice:
                                self.earning_status = True
                            else:
                                self.earning_status = False
                        elif position_value < 0:
                            if markPrice < entryPrice:
                                self.earning_status = True
                            else:
                                self.earning_status = False
                        else:
                            self.earning_status = False
        except Exception as e:
            print(f"【异常信息】【解析账户仓位信息异常】：{e}")

    # market
    def get_kline(self, period=None):
        try:
            kline = self.http_client.get_kline(period)
        except Exception as e:
            print(f"【异常信息】【获取K线数据异常】：{e}")
            time.sleep(2)
        else:
            return kline
    # 将数据转换为其他周期的数据
    def transfer_to_period_data(self, df, num):
        period_df = df.resample(rule=num, on='open_time', label='left', closed='left').agg(
            {'open': 'first',
             'high': 'max',
             'low': 'min',
             'close': 'last',
             })
        period_df.dropna(subset=['open'], inplace=True)
        period_df.reset_index(inplace=True)
        return period_df

    def get_ma(self):
        try:
            # 转化成df
            df = pd.DataFrame(self.get_kline(self.period))
            df.rename(columns={0: 'id', 1: 'open', 2: 'high', 3: 'low', 4: 'close'}, inplace=True)
            # 删除最后一行  不然在反手的时候 信号太频繁了
            df.drop(len(df) - 1, inplace=True)
            df['id'] = pd.to_datetime(df['id'], unit='ms') + pd.Timedelta(hours=8)
            df.rename(columns={"id": "open_time"}, inplace=True)
            if 'T' in self.transfer_period:
                df = self.transfer_to_period_data(df, self.transfer_period)
            # 计算df
            df['ma_short'] = df['close'].rolling(self.short_num).mean()
            self.ma_short = df.loc[len(df) - 1]['ma_short']
            self.ma_short = round(self.ma_short, 4)

            df['ma_long'] = df['close'].rolling(self.long_num).mean()
            self.ma_long = df.loc[len(df) - 1]['ma_long']
            self.ma_long = round(self.ma_long, 4)
        except Exception as e:
            print(f"【异常信息】【转化ma数据异常】：{e}")
            time.sleep(2)

    def get_orders(self):
        try:
            orders = self.http_client.all_orders()
            if isinstance(orders, list):
                trade_num = 0
                for i in orders:
                    # 只处理完全成交的单子
                    if i['status'] == 'FILLED':
                        # 某笔成交为3张  表示人工干预  作为计算起始
                        if int(i['executedQty']) == 3:
                            # 多个3  以最后一次3作为起始计算
                            trade_num = 0
                        if int(i['executedQty']) > 0:
                            trade_num = trade_num + 1
                # 3不算  所以减1
                res = trade_num - 1
                res = max(0,res)
                res = min(res,30)
                self.stop_amount = res // 2
        except Exception as e:
            print(f"【异常信息】【获取历史订单数据异常】：{e}")
            time.sleep(2)

    # about trade
    def market_buy(self, value):
        if value > 0:
            try:
                self.http_client.market_buy(value)
            except Exception as e:
                print(f"【异常信息】【买入异常】：{e}")
            else:
                self.msg(f"market_buy  {value}")
                time.sleep(5)
        else:
            print(f"【异常信息】【买入量异常,不执行买入】：{value}")
            pass

    def market_sell(self, value):
        if value > 0:
            try:
                self.http_client.market_sell(value)
            except Exception as e:
                print(f"【异常信息】【卖出异常】：{e}")
            else:
                self.msg(f"market_sell  {value}")
                time.sleep(5)
        else:
            print(f"【异常信息】【卖出量异常,不执行卖出】：{value}")
            pass

    def zero_account(self):
        if self.position_value > 0:
            self.market_sell(self.position_value)
        else:
            self.market_buy(abs(self.position_value))

    # about  check
    def check(self):
        self.log_debug()
        if not self.strategy_status:
            print(f'策略初始化中，暂不策略计算。')
            self.init_data()
            return
        if self.earning_status:
            print(f'盈利状态，暂不策略计算。')
            return
        condition_zero_buy = self.position_value > 0 and self.ma_short < self.ma_long
        condition_zero_sell = self.position_value < 0 and self.ma_short >= self.ma_long
        if condition_zero_buy or condition_zero_sell:
            self.zero_account()
        else:
            expect_value = self.position_value
            # 根据行情计算仓位
            if self.ma_short >= self.ma_long:
                expect_value = self.stop_amount * self.add_size + 2 * self.start_size
                if self.only_sell:
                    expect_value = 0
            else:
                expect_value = -1 * (self.stop_amount * self.add_size + 3 * self.start_size)
                if self.only_buy:
                    expect_value = 0
            self.trade(expect_value)
    def trade(self, expect_value):
        try:
            if self.position_value > expect_value:
                # 5  1    sell   4 = 5-1
                # 5  -1  sell 6 = 5-(-1)
                # -1  -3   sell 2 = -1-(-3)
                print(f"实际：{self.position_value}   预期：{expect_value} 卖出: {self.position_value - expect_value}")
                self.market_sell(int(self.position_value - expect_value))
            elif self.position_value == expect_value:
                print(f"实际：{self.position_value}   预期：{expect_value} 仓位无需调整")
                pass
            elif self.position_value < expect_value:
                # 1 < 5   buy  4 = 5-1
                # -5 < -1   buy  4 = -1-(-5)
                # -5 < 5  buy 10 = 5-(-5)
                print(f"实际：{self.position_value}   预期：{expect_value} 买入: {expect_value - self.position_value}")
                self.market_buy(int(expect_value - self.position_value))
        except Exception as e:
            print(f"【异常信息】【卖出异常】：{e}")

    # about thread
    def thread_get_ma(self):
        while True:
            time.sleep(30)
            self.get_ma()

    def thread_get_position(self):
        while True:
            time.sleep(3)
            self.get_position()

    def thread_get_orders(self):
        while True:
            time.sleep(10)
            self.get_orders()

    # 调试实时日志
    def log_debug(self):
        try:
            print(20 * '*')
            print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            print(f"策略状态：{self.strategy_status}")
            print(f"only_buy：{self.only_buy}")
            print(f"only_sell：{self.only_sell}")
            print(f"交易品种：{self.symbol}")
            print(f"earning_status：{self.earning_status}")
            print(20 * '-')
            print(f'mashort：{self.ma_short} ')
            print(f'malong：{self.ma_long} ')
            print(f'position：{self.position_value} ')
            print(f'止损次数：{self.stop_amount} ')
            print(20 * '*')
            print('\n')
        except Exception as e:
            print(f"【异常信息】【打印调试数据异常】：{e}")

    def msg(self, message):
        print(message)


# if __name__ == '__main__':
#     import os
#     from binance_coin import BinanceFutureHttp, Interval
#     # 参数
#     key = os.getenv('binancekey')
#     secret = os.getenv('binancesecret')
#     symbol = 'OPUSD_PERP'
#     period = Interval.MINUTE_1
#     transfer_period = '1'  # 不转化  1  转为为3分钟  3T
#     short_num = 5
#     long_num = 10
#     size = 1500  # 范围1-2000TIC
#     start_size = 5
#     add_size = 5
#     # 实例化
#     binance = BinanceFutureHttp(api_key=key, secret=secret, symbol=symbol, size=size)
#     test_strategy = TestStrategy(binance, symbol=symbol, period=period, transfer_period=transfer_period,
#                                  short_num=short_num, long_num=long_num, start_size=start_size, add_size=add_size)
    # test_strategy.get_ma()
    # while True:
    #     test_strategy.get_position()
    #     test_strategy.get_ma()
    #     time.sleep(2)
