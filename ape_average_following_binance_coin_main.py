from binance_coin import BinanceFutureHttp, Interval
from average_following_binance_coin import TestStrategy
from apscheduler.schedulers.background import BackgroundScheduler
import time
import os
import threading

if __name__ == '__main__':
    # 参数
    key = os.getenv('binancekey')
    secret = os.getenv('binancesecret')
    symbol = 'APEUSD_PERP'
    period = Interval.MINUTE_1
    transfer_period = '1'  # 不转化  1  转为为3分钟  3T
    short_num = 5
    long_num = 300
    size = 1500  # 范围1-2000TIC
    # 配置为一倍杠杆张数
    start_size = 20
    # 配置为一倍杠杆的5%
    add_size = 3
    only_buy = False
    only_sell = False
    # 实例化
    binance = BinanceFutureHttp(api_key=key, secret=secret, symbol=symbol, size=size)
    test_strategy = TestStrategy(binance, symbol=symbol, period=period, transfer_period=transfer_period,
                                 short_num=short_num, long_num=long_num, start_size=start_size, add_size=add_size)

    # 策略计算
    scheduler = BackgroundScheduler()
    scheduler.add_job(test_strategy.check, trigger='cron', max_instances=3, second='*/10')
    scheduler.start()

    t1 = threading.Thread(target=test_strategy.thread_get_position)
    t2 = threading.Thread(target=test_strategy.thread_get_ma)
    t3 = threading.Thread(target=test_strategy.thread_get_orders)

    t1.start()
    t2.start()
    t3.start()

    t1.join()
    t2.join()
    t3.join()

    while True:
        time.sleep(3)
