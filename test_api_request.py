import tkinter as tk
from tkinter import ttk
import pandas as pd
from binance.um_futures import UMFutures
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import json
import os
import numpy as np
import ta
from time import sleep
from binance.error import ClientError
from datetime import datetime

client = UMFutures()  # Utilisez ce client pour accéder aux USDT-M Futures

# Configuration du levier et des seuils de trading
tp = 0.012  # Take profit à +1.2%
sl = 0.009  # Stop loss à -0.9%
volume = 10  # Volume pour une position (en fonction du levier)
leverage = 10
margin_type = 'ISOLATED'  # Type de marge ('ISOLATED' ou 'CROSS')

class BTCApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cours du Bitcoin")
        self.geometry("800x800")

        # Charger le solde actuel depuis le fichier JSON
        self.usdt_balance = self.load_balance("USDT.json")
        self.btc_balance = self.load_balance("BTC.json")

        # Titre
        title_label = tk.Label(self, text="Cours du Bitcoin", font=("Helvetica", 16))
        title_label.pack(pady=10)

        # Label pour afficher le prix en temps réel
        self.price_label = tk.Label(self, text="Prix du BTC : Chargement...", font=("Helvetica", 14))
        self.price_label.pack(pady=10)

        # Texte d'explication
        info_label = tk.Label(self, text="Cliquez sur le bouton ci-dessous pour afficher le graphique en bougies :")
        info_label.pack(pady=10)

        # Bouton pour afficher le graphique
        display_button = tk.Button(self, text="Afficher le graphique en bougies", command=self.display_candlestick)
        display_button.pack(pady=10)

        # Cadre pour le graphique
        self.chart_frame = tk.Frame(self)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

        # Solde USDT
        balance_frame = tk.Frame(self)
        balance_frame.pack(pady=20)

        self.balance_label = tk.Label(balance_frame, text=f"Solde USDT : {self.usdt_balance:.2f} USDT", font=("Helvetica", 14))
        self.balance_label.pack(side=tk.LEFT, padx=10)

        self.amount_entry = tk.Entry(balance_frame)
        self.amount_entry.pack(side=tk.LEFT, padx=10)

        add_balance_button = tk.Button(balance_frame, text="Ajouter solde USDT", command=self.add_balance)
        add_balance_button.pack(side=tk.LEFT, padx=10)

        # Cadre pour les actions de trading
        trading_frame = tk.Frame(self)
        trading_frame.pack(pady=20)

        self.btc_balance_label = tk.Label(trading_frame, text=f"Solde BTC : {self.btc_balance:.6f} BTC", font=("Helvetica", 14))
        self.btc_balance_label.pack(side=tk.LEFT, padx=10)

        buy_button = tk.Button(trading_frame, text="Acheter BTC", command=self.buy_btc)
        buy_button.pack(side=tk.LEFT, padx=10)

        sell_button = tk.Button(trading_frame, text="Vendre BTC", command=self.sell_btc)
        sell_button.pack(side=tk.LEFT, padx=10)

        # Démarrer la mise à jour en temps réel du prix du BTC
        self.update_price()

        # Démarrer le trading automatique en permanence
        self.start_auto_trading()

    def load_balance(self, filename):
        # Charger le solde depuis le fichier JSON
        if os.path.exists(filename):
            with open(filename, "r") as f:
                data = json.load(f)
                return data.get("balance", 0.0)
        return 0.0

    def save_balance(self, filename, balance):
        # Sauvegarder le solde dans le fichier JSON
        with open(filename, "w") as f:
            json.dump({"balance": balance}, f)

    def add_balance(self):
        # Ajouter le montant saisie au solde actuel
        try:
            amount = float(self.amount_entry.get())
            if amount > 0:
                self.usdt_balance += amount
                self.balance_label.config(text=f"Solde USDT : {self.usdt_balance:.2f} USDT")
                self.save_balance("USDT.json", self.usdt_balance)
                self.amount_entry.delete(0, tk.END)
            else:
                print("Veuillez entrer un montant positif.")
        except ValueError:
            print("Veuillez entrer un montant valide.")

    def get_btc_data(self):
        try:
            # Récupérer les données de marché futures pour BTCUSDT (données horaires)
            response = client.klines(
                symbol="BTCUSDT",
                interval="1h",
                limit=50
            )

            # Transformer la réponse en DataFrame
            df = pd.DataFrame(response, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])

            # Convertir les colonnes nécessaires
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)

            return df

        except Exception as e:
            print(f"Erreur lors de la récupération des données: {e}")
            return None

    def get_btc_price(self):
        try:
            # Récupérer le prix actuel du BTC/USDT
            ticker = client.ticker_price(symbol="BTCUSDT")
            price = float(ticker['price'])
            return price
        except Exception as e:
            print(f"Erreur lors de la récupération du prix : {e}")
            return None

    def display_candlestick(self):
        # Récupérer les données du Bitcoin
        df = self.get_btc_data()
        if df is None:
            print("Impossible d'afficher les données, veuillez réessayer.")
            return

        # Créer la figure pour le graphique
        fig, axlist = mpf.plot(df, type='candle', style='charles', volume=True, title="Cours du Bitcoin",
                               ylabel='Prix (USDT)', ylabel_lower='Volume', figratio=(6, 3), returnfig=True)

        # Afficher le graphique dans une nouvelle fenêtre
        new_window = tk.Toplevel(self)
        new_window.title("Graphique en bougies du Bitcoin")
        canvas = FigureCanvasTkAgg(fig, master=new_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_price(self):
        # Récupérer le prix du Bitcoin
        price = self.get_btc_price()
        if price is not None:
            self.price_label.config(text=f"Prix du BTC : {price:.2f} USDT")
            # Afficher le prix en console
            print(f"[Flux de données] Prix du BTC : {price:.2f} USDT")

        # Planifier la prochaine mise à jour du prix dans 5 secondes
        self.after(5000, self.update_price)

    def buy_btc(self):
        # Acheter du BTC avec tout le solde USDT disponible
        price = self.get_btc_price()
        if price is not None and self.usdt_balance > 0:
            amount_to_buy = self.usdt_balance / price
            usdt_spent = self.usdt_balance
            self.btc_balance += amount_to_buy
            self.usdt_balance = 0.0
            self.update_balance_labels()
            self.save_balance("USDT.json", self.usdt_balance)
            self.save_balance("BTC.json", self.btc_balance)
            transaction_id = self.generate_transaction_id()
            self.log_transaction("achats.json", "Achat", amount_to_buy, price, usdt_spent, transaction_id)
            print(f"Achat de {amount_to_buy:.6f} BTC au prix de {price:.2f} USDT")
        else:
            print("Solde insuffisant ou prix non disponible pour acheter du BTC.")

    def sell_btc(self):
        # Vendre tout le BTC disponible
        price = self.get_btc_price()
        if price is not None and self.btc_balance > 0:
            amount_to_sell = self.btc_balance
            usdt_received = amount_to_sell * price
            self.btc_balance = 0.0
            self.usdt_balance += usdt_received
            self.update_balance_labels()
            self.save_balance("USDT.json", self.usdt_balance)
            self.save_balance("BTC.json", self.btc_balance)
            transaction_id = self.generate_transaction_id()
            self.log_transaction("ventes.json", "Vente", amount_to_sell, price, usdt_received, transaction_id)
            print(f"Vente de {amount_to_sell:.6f} BTC au prix de {price:.2f} USDT")
        else:
            print("Solde BTC insuffisant ou prix non disponible pour vendre.")

    def update_balance_labels(self):
        # Mettre à jour les labels de solde
        self.balance_label.config(text=f"Solde USDT : {self.usdt_balance:.2f} USDT")
        self.btc_balance_label.config(text=f"Solde BTC : {self.btc_balance:.6f} BTC")

    def log_transaction(self, filename, action, amount, price, usdt_amount, transaction_id):
        # Enregistrer la transaction dans un fichier JSON
        transaction = {
            "transaction_id": transaction_id,
            "action": action,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "price": price,
            "amount": amount,
            "usdt_amount": usdt_amount
        }
        if os.path.exists(filename):
            with open(filename, "r") as f:
                data = json.load(f)
        else:
            data = []
        data.append(transaction)
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    def generate_transaction_id(self):
        return int(datetime.now().timestamp() * 1000)

    def start_auto_trading(self):
        # Activer le trading automatique basé sur une stratégie utilisant des indicateurs techniques
        df = self.get_btc_data()
        if df is None:
            print("Impossible de récupérer les données pour le trading automatique.")
            return

        # Calculer des indicateurs techniques (RSI et EMA)
        df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        df['EMA200'] = ta.trend.ema_indicator(df['close'], window=200)

        latest_price = df['close'].iloc[-1]
        latest_rsi = df['RSI'].iloc[-1]
        latest_ema = df['EMA200'].iloc[-1]

        # Stratégie : acheter si le RSI est inférieur à 30 et le prix est au-dessus de l'EMA200, vendre si le RSI est supérieur à 70
        if latest_rsi < 30 and latest_price > latest_ema and self.usdt_balance > 0:
            self.buy_btc()
        elif latest_rsi > 70 and self.btc_balance > 0:
            self.sell_btc()

        # Planifier la prochaine vérification dans 15 minutes
        self.after(900000, self.start_auto_trading)

if __name__ == "__main__":
    app = BTCApp()
    app.mainloop()