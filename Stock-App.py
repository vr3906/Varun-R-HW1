import os
import queue
import threading
from datetime import datetime, timedelta, timezone

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import tkinter as tk
from tkinter import ttk

API_KEY = "PK47WZFSYDDZRWJQYDOVKZKA7F"        
SECRET_KEY = "mMoL5vBmsD7PrpA7wt3h78rKQ7WjpgxeekD9vaNHKw4"         

class AlpacaConnector:
    def __init__(self, api_key, secret_key):
        if not api_key or not secret_key:
            raise RuntimeError("Missing API keys. Set ALPACA_API_KEY and "
                               "ALPACA_SECRET_KEY (or paste them in the code).")
        self.hist_client = StockHistoricalDataClient(api_key, secret_key)
        self._api_key = api_key
        self._secret_key = secret_key
        self._stream = None
        self._thread = None

    def get_history(self, symbol):
        end = datetime.now(timezone.utc) - timedelta(minutes=16)
        start = end - timedelta(days=30)
        req = StockBarsRequest(
            symbol_or_symbols=symbol.upper(),
            timeframe=TimeFrame(5, TimeFrameUnit.Minute),
            start=start,
            end=end,
            feed=DataFeed.IEX,
        )
        df = self.hist_client.get_stock_bars(req).df
        if df is None or df.empty:
            return df
        return df.reset_index()


    def start_stream(self, symbol, on_quote, on_trade):
        self.stop_stream()
        stream = StockDataStream(self._api_key, self._secret_key)

        async def _q(q):
            on_quote(q.symbol, q.bid_price, q.ask_price)

        async def _t(t):
            on_trade(t.symbol, t.price)

        stream.subscribe_quotes(_q, symbol.upper())
        stream.subscribe_trades(_t, symbol.upper())
        self._stream = stream
        self._thread = threading.Thread(target=stream.run, daemon=True)
        self._thread.start()

    def stop_stream(self):
        if self._stream is not None:
            try:
                self._stream.stop()
            except Exception:
                pass
        self._stream = None
        self._thread = None


class TerminalApp:
    def __init__(self, root, connector):
        self.root = root
        self.conn = connector
        self.queue = queue.Queue()
        self.current_symbol = None
        root.title("Varun R Homework 1")
        root.geometry("900x650")

        bar = tk.Frame(root)
        bar.pack(fill="x", padx=10, pady=8)
        tk.Label(bar, text="Ticker:").pack(side="left")
        self.symbol_var = tk.StringVar(value="AAPL")
        entry = tk.Entry(bar, textvariable=self.symbol_var, width=10)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda e: self.load())
        tk.Button(bar, text="Load", command=self.load).pack(side="left")

        panel = tk.Frame(root)
        panel.pack(fill="x", padx=10, pady=6)
        self.labels = {}
        for i, name in enumerate(("BID", "ASK", "LAST")):
            col = tk.Frame(panel)
            col.grid(row=0, column=i, padx=30, pady=8)
            tk.Label(col, text=name).pack()
            val = tk.Label(col, text="—", font=("Helvetica", 26, "bold"))
            val.pack()
            self.labels[name] = val

        self.fig = Figure(figsize=(9, 4.2))
        self.ax_price = self.fig.add_axes([0.08, 0.30, 0.88, 0.62])
        self.ax_vol = self.fig.add_axes([0.08, 0.08, 0.88, 0.20],
                                        sharex=self.ax_price)
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True,
                                         padx=10, pady=8)
        self.canvas.draw()

        self.root.after(200, self._drain_queue)

    def load(self):
        symbol = self.symbol_var.get().upper().strip()
        if not symbol:
            return
        self.current_symbol = symbol
        for v in self.labels.values():
            v.config(text="—")
        threading.Thread(target=self._load_worker, args=(symbol,),
                         daemon=True).start()

    def _load_worker(self, symbol):
        try:
            df = self.conn.get_history(symbol)
            self.queue.put(("history", symbol, df))
        except Exception as e:
            self.queue.put(("error", symbol, str(e)))
            return
        self.conn.start_stream(
            symbol,
            on_quote=lambda s, b, a: self.queue.put(("quote", s, b, a)),
            on_trade=lambda s, p: self.queue.put(("trade", s, p)),
        )

    def _drain_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                kind, symbol = msg[0], msg[1]
                if symbol != self.current_symbol:
                    continue
                if kind == "history":
                    self._plot(msg[2], symbol)
                elif kind == "quote":
                    self.labels["BID"].config(text=f"{msg[2]:,.2f}")
                    self.labels["ASK"].config(text=f"{msg[3]:,.2f}")
                elif kind == "trade":
                    self.labels["LAST"].config(text=f"{msg[2]:,.2f}")
                elif kind == "error":
                    print("Error:", msg[2])
        except queue.Empty:
            pass
        self.root.after(200, self._drain_queue)

    def _plot(self, df, symbol):
        self.ax_price.clear()
        self.ax_vol.clear()
        if df is None or df.empty:
            self.canvas.draw()
            return
        o = df["open"].to_numpy()
        h = df["high"].to_numpy()
        low = df["low"].to_numpy()
        c = df["close"].to_numpy()
        v = df["volume"].to_numpy()
        x = np.arange(len(df))
        colors = np.where(c >= o, "green", "red")
        self.ax_price.vlines(x, low, h, color=colors, linewidth=0.7)
        self.ax_price.bar(x, height=np.abs(c - o), bottom=np.minimum(o, c),
                          width=0.7, color=colors)
        self.ax_vol.bar(x, v, width=0.7, color=colors)
        self.ax_price.set_title(f"{symbol} — 30 days, 5-min bars (OHLC)")
        self.ax_vol.set_ylabel("Volume")
        self.canvas.draw()


def main():
    try:
        connector = AlpacaConnector(API_KEY, SECRET_KEY)
    except RuntimeError as e:
        print(e)
        return
    root = tk.Tk()
    TerminalApp(root, connector)
    root.mainloop()


if __name__ == "__main__":
    main()

