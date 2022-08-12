## coding: UTF-8
import sys
import glob
import datetime
import h5py
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime as dt
import traceback

from urllib.parse import urlparse
from urllib.parse import parse_qs

from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from http import HTTPStatus

PORT = 80
H5_LIST = glob.glob("./dataset/*.h5")
H5_OBJECTS = {}
DATASET = {}
KEY_TABLE = {}
ERROR_RET = {
                "InvalidPair":'{"success":false,"error":"invalid pair"}',
                "Error":'{"success":false,"error":"unknown error"}',
            }
DATETIME = datetime.datetime.strptime("20220401_000000", '%Y%m%d_%H%M%S')

def get_h5_object(path):
    if path not in H5_OBJECTS:
        H5_OBJECTS[path] = h5py.File(path, 'r')
    return H5_OBJECTS[path]

def get_key_table(path):
    if path not in KEY_TABLE:
        _f = get_h5_object(path)
        _df = pd.DataFrame([[_k, datetime.datetime.strptime(_k, '%Y%m%d_%H%M%S')] for _k in _f.keys()], columns=['key','date'])
        _df = _df.set_index('date')
        _df.sort_index(inplace=True)
        KEY_TABLE[path] = _df
    return KEY_TABLE[path]

def get_h5_record(path, date, info):
    _ref_table = get_key_table(path)
    _idx_i = _ref_table.index.get_indexer([date], 'ffill')[0]
    _idx = _ref_table.index[_idx_i]
    if _idx_i <= 0:
        if len(info['before'])<=0:
            _before = 'null'
        else:
            _before = get_key_table(info['before'][0]).index[-1].strftime('%Y%m%d_%H%M%S')
    else:
        _before = _ref_table.index[_idx_i-1].strftime('%Y%m%d_%H%M%S')

    if (_idx_i+1) >= len(_ref_table.index):
        if len(info['next'])<=0:
            _next = 'null'
        else:
            _next = get_key_table(info['next'][0]).index[0].strftime('%Y%m%d_%H%M%S')
    else:
        _next = _ref_table.index[_idx_i+1].strftime('%Y%m%d_%H%M%S')

    return get_h5_object(path)[_idx.strftime('%Y%m%d_%H%M%S')], {'before':_before, 'next':_next, 'now':_idx.strftime('%Y%m%d_%H%M%S')}

def create_dataset_list(pair):
    return [_path for _path in H5_LIST if f'/{pair}' in _path]

def get_record(pair, date=DATETIME):
    h5_list = sorted([_path for _path in DATASET[pair] if _path.endswith(date.strftime('_%Y%m.h5'))], reverse=True)
    if len(h5_list)<=0:
        return {}, {}
    else:
        _info = {
            'before':sorted([_path for _path in DATASET[pair] if _path.endswith((date - relativedelta(months=1)).strftime('_%Y%m.h5'))], reverse=True),
            'next':sorted([_path for _path in DATASET[pair] if _path.endswith((date + relativedelta(months=1)).strftime('_%Y%m.h5'))], reverse=True),
            }
        return get_h5_record(h5_list[0], date, _info)

def int_to_datetime(series):
    return (series * (10 ** 6)).map(pd.Timestamp)

def parse_trades(record, pair, info):
    _trades = record['trades']
    _trades = pd.DataFrame([_v for _k, _v in _trades.items()], index=_trades.keys()).T
    _trades['created_at'] = int_to_datetime(_trades['created_at'])
    _trades['get_at'] = int_to_datetime(_trades['get_at'])
    _ret = '{"success":true,"pagination":{"limit":10,"order":"desc","starting_after":null,"ending_before":null},"dataset":{"now":'+info['now']+',"before":'+info['before']+',"next":'+info['next']+'},"data":['
    _data = []
    for _, _row in _trades.iterrows():
        _order_type = 'sell' if _row.is_sell else 'buy'
        _created_at = _row.created_at.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        _data.append("{" + '"id":{},"amount":"{}","rate":"{}","pair":"{}","order_type":"{}","created_at":"{}"'.format(
            _row.id, _row.amount, _row.rate, pair, _order_type, _created_at
        ) + "}")
    _ret = _ret + ",".join(_data)
    return _ret + ']}'

def parse_order_books(record, pair, info):
    _asks = record['asks']
    _bids = record['bids']
    _asks = pd.DataFrame([_v for _k, _v in _asks.items()], index=_asks.keys()).T
    _bids = pd.DataFrame([_v for _k, _v in _bids.items()], index=_bids.keys()).T
    _ret = '{"asks":['
    _data = []
    for _, _row in _asks.iterrows():
        _data.append('["{}","{}"]'.format(_row.rate, _row.amount))
    _ret = _ret + ",".join(_data) + '],"bids":['
    _data = []
    for _, _row in _bids.iterrows():
        _data.append('["{}","{}"]'.format(_row.rate, _row.amount))
    _ret = _ret + ",".join(_data) + '],"dataset":{"now":'+info['now']+',"before":'+info['before']+',"next":'+info['next']+'}'+'}'
    return _ret

class StubHttpRequestHandler(BaseHTTPRequestHandler):
    server_version = "HTTP Stub/0.1"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = {}
        
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        enc = sys.getfilesystemencoding()
        ret_body = ""
        ret_status = HTTPStatus.OK
        if parsed.path in ['/api/trades','/api/order_books']:
            try:
                if 'pair' not in params:
                    print("'pair' not in params.")
                    ret_body = str(ERROR_RET["InvalidPair"])
                    
                elif params['pair'][0] not in ['btc_jpy','etc_jpy','fct_jpy','mona_jpy','plt_jpy']:
                    print("params['pair'] not in ['btc_jpy','etc_jpy','fct_jpy','mona_jpy','plt_jpy'].")
                    ret_body = str(ERROR_RET["InvalidPair"])
                else:
                    _pair = params['pair'][0]
                    _date = dt.strptime(params['date'][0], '%Y%m%d_%H%M%S') if 'date' in params else DATETIME
                    if _pair not in DATASET:
                        DATASET[_pair] = create_dataset_list(_pair)
                    _record, _info = get_record(_pair, date = _date)
                    if parsed.path == '/api/trades':
                        ret_body = parse_trades(_record, _pair, _info)
                    else:
                        ret_body = parse_order_books(_record, _pair, _info)
            except:
                ret_status = HTTPStatus.BAD_REQUEST
                ret_body = traceback.format_exc()

        encoded = ret_body.encode(enc, 'surrogateescape')
        self.send_response(ret_status)
        self.send_header("Content-type", "text/html; charset=%s" % enc)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

print("Start server.")
handler = StubHttpRequestHandler
httpd = HTTPServer(('',PORT),handler)
httpd.serve_forever()