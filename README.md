# CoincheckTryServer
非公式Coincheck過去ログを用いた練習用サーバー

# 環境構築
## Docker build
```
docker build --tag ccheckserver:latest -f ./Dockerfile .
```

# 使い方
## 過去データ格納
* ./opt/dataset/にh5ファイルを格納。以下例：
```
$ ls ./opt/dataset/
	btc_jpy_0.003333_202203.h5
	btc_jpy_0.003333_202204.h5
	etc_jpy_0.003333_202203.h5
	etc_jpy_0.003333_202204.h5
	fct_jpy_0.003333_202203.h5
	fct_jpy_0.003333_202204.h5
	mona_jpy_0.003333_202203.h5
	mona_jpy_0.003333_202204.h5
```
## 起動
```
./run.sh
```
## 全取引履歴取得（Ref：https://coincheck.com/ja/documents/exchange/api#public-trades）
ブラウザ等から「```http://hostname:8880/api/trades?pair=btc_jpy```」へアクセス
## 板情報取得（Ref：https://coincheck.com/ja/documents/exchange/api#order-book）
ブラウザ等から「```http://hostname:8880/api/order_books?pair=btc_jpy```」へアクセス
## Query
* pair : ['btc_jpy','etc_jpy','fct_jpy','mona_jpy','plt_jpy']
* date : '%Y%m%d_%H%M%S'
## Example - 2022/4/1 12:30:00のイーサリアム板情報を取得たい：
```
wget http://localhost:8880/api/order_books?pair=etc_jpy&20220401_123000
```