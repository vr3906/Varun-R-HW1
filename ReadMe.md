\
\
1. Go to terminal\
2. Install the required packages: using pip install alpaca-py matplotlib numpy\
3. Go to Alpaca to get your api keys\
4. Once you have your keys run this in terminal:\
export API_KEY="YOUR KEY"\
export SECRET_KEY="YOUR "KEY

\
5. Run python3 stock-app.py\
\
Features:\
- Connects to Alpaca using API keys from your environment\
- Downloads 30 days of 5-minute OHLCV bars for any ticker

\- Shows the bars as a candlestick chart with a volume subplot\
\
- Streams live bid, ask, and last trade price over a websocket\
\
- Type a ticker and the quote panel updates automatically as new data arrives
