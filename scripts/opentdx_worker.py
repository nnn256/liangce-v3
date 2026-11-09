"""Optional Python3.12 process adapter for acb6104/opentdx; JSON stdout only."""
import contextlib,json,sys

def main():
    from opentdx.tdxClient import TdxClient
    from opentdx.const import MARKET,PERIOD,ADJUST
    code,period=sys.argv[1:3]
    mapping={'1m':PERIOD.MIN_1,'5m':PERIOD.MIN_5,'15m':PERIOD.MIN_15,'30m':PERIOD.MIN_30,'60m':PERIOD.MIN_60,
             'day':PERIOD.DAILY,'week':PERIOD.WEEKLY,'month':PERIOD.MONTHLY,'quarter':PERIOD.QUARTERLY,'year':PERIOD.YEARLY,'5d':PERIOD.DAILY}
    client=TdxClient()
    try:
        with contextlib.redirect_stdout(sys.stderr):
            rows=client.stock_kline(getattr(MARKET,code[:2].upper()),code[2:],mapping[period],count=30000,adjust=ADJUST.NONE)
        result=[{'time':str(row['datetime']),'open':row['open'],'high':row['high'],'low':row['low'],'close':row['close'],'volume':row['vol']} for row in rows]
        print(json.dumps({'source':'acb6104/opentdx','bars':result},ensure_ascii=False,allow_nan=False))
    finally:
        for inner in [client.quotation_client,client.ex_quotation_client]:
            if inner.connected:inner.disconnect()

if __name__=='__main__':main()
