import tkinter as tk
from tkinter import messagebox
from binance.um_futures import UMFutures
import threading
import time
import json
import pandas as pd
import ta
import mplfinance as mpf
from datetime import datetime
import uuid

# Initialisation du client Binance
client = UMFutures()

# Chemins des fichiers JSON
USDT_FILE = 'USDT.json'
BTC_FILE = 'BTC.json'
ACHATS_FILE = 'achats.json'
VENTES_FILE = 'ventes.json'

# Initialisation des soldes
def init_soldes():
    try:
        with open(USDT_FILE, 'r') as f:
            usdt_solde = json.load(f)['solde']
    except FileNotFoundError:
        usdt_solde = 1000  # Solde initial par défaut
        with open(USDT_FILE, 'w') as f:
            json.dump({'solde': usdt_solde}, f)

    try:
        with open(BTC_FILE, 'r') as f:
            btc_solde = json.load(f)['solde']
    except FileNotFoundError:
        btc_solde = 0
        with open(BTC_FILE, 'w') as f:
            json.dump({'solde': btc_solde}, f)
    return usdt_solde, btc_solde

usdt_solde, btc_solde = init_soldes()

# Fonction pour récupérer le prix actuel du BTC/USDT
def get_current_price():
    ticker = client.ticker_price('BTCUSDT')
    return float(ticker['price'])

# Mise à jour du prix toutes les 30 secondes
def update_price():
    global current_price
    while True:
        try:
            price = get_current_price()
            current_price = price
            price_label.config(text=f"Prix actuel du BTC: {price:.2f} USDT")
        except Exception as e:
            print("Erreur lors de la récupération du prix:", e)
        time.sleep(30)

# Fonction pour ajouter du solde USDT
def add_usdt():
    global usdt_solde
    try:
        amount = float(usdt_entry.get())
        usdt_solde += amount
        usdt_label.config(text=f"Solde USDT: {usdt_solde:.2f}")
        with open(USDT_FILE, 'w') as f:
            json.dump({'solde': usdt_solde}, f)
        usdt_entry.delete(0, tk.END)
    except ValueError:
        messagebox.showerror("Erreur", "Veuillez entrer un montant valide.")

# Fonction pour acheter du BTC
def acheter_btc():
    global usdt_solde, btc_solde
    if usdt_solde <= 0:
        messagebox.showerror("Erreur", "Solde USDT insuffisant.")
        return
    montant_usdt = usdt_solde
    montant_btc = montant_usdt / current_price
    usdt_solde -= montant_usdt
    btc_solde += montant_btc
    # Mise à jour des soldes
    usdt_label.config(text=f"Solde USDT: {usdt_solde:.2f}")
    btc_label.config(text=f"Solde BTC: {btc_solde:.6f}")
    with open(USDT_FILE, 'w') as f:
        json.dump({'solde': usdt_solde}, f)
    with open(BTC_FILE, 'w') as f:
        json.dump({'solde': btc_solde}, f)
    # Enregistrement de la transaction
    transaction_id = str(uuid.uuid4())
    transaction = {
        'id': transaction_id,
        'action': 'achat',
        'montant_btc': montant_btc,
        'prix': current_price,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'montant_usdt': montant_usdt
    }
    with open(ACHATS_FILE, 'a') as f:
        json.dump(transaction, f)
        f.write('\n')
    transaction_label.config(text=f"Dernière transaction ID: {transaction_id}")
    # Mise à jour des gains/pertes
    calculer_gains()

# Fonction pour vendre du BTC
def vendre_btc():
    global usdt_solde, btc_solde
    if btc_solde <= 0:
        messagebox.showerror("Erreur", "Solde BTC insuffisant.")
        return
    montant_btc = btc_solde
    montant_usdt = montant_btc * current_price
    btc_solde -= montant_btc
    usdt_solde += montant_usdt
    # Mise à jour des soldes
    usdt_label.config(text=f"Solde USDT: {usdt_solde:.2f}")
    btc_label.config(text=f"Solde BTC: {btc_solde:.6f}")
    with open(USDT_FILE, 'w') as f:
        json.dump({'solde': usdt_solde}, f)
    with open(BTC_FILE, 'w') as f:
        json.dump({'solde': btc_solde}, f)
    # Enregistrement de la transaction
    transaction_id = str(uuid.uuid4())
    transaction = {
        'id': transaction_id,
        'action': 'vente',
        'montant_btc': montant_btc,
        'prix': current_price,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'montant_usdt': montant_usdt
    }
    with open(VENTES_FILE, 'a') as f:
        json.dump(transaction, f)
        f.write('\n')
    transaction_label.config(text=f"Dernière transaction ID: {transaction_id}")
    # Mise à jour des gains/pertes
    calculer_gains()

# Fonction pour afficher le graphique des prix
def afficher_graphique():
    try:
        klines = client.klines('BTCUSDT', '1m', limit=200)
        df = pd.DataFrame(klines)
        df = df.iloc[:, :6]
        df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        df['Date'] = pd.to_datetime(df['Date'], unit='ms')
        df.set_index('Date', inplace=True)
        df = df.astype(float)
        mpf.plot(df, type='candle', volume=True, style='binance')
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'afficher le graphique: {e}")

# Fonction pour calculer et afficher les gains/pertes
def calculer_gains():
    gain = 0
    try:
        with open(ACHATS_FILE, 'r') as f:
            achats = [json.loads(line) for line in f]
    except FileNotFoundError:
        achats = []
    try:
        with open(VENTES_FILE, 'r') as f:
            ventes = [json.loads(line) for line in f]
    except FileNotFoundError:
        ventes = []
    for achat in achats:
        gain -= achat['montant_usdt']
    for vente in ventes:
        gain += vente['montant_usdt']
    gains_label.config(text=f"Gains/Pertes: {gain:.2f} USDT")

# Fonction de trading automatique
def trading_automatique():
    global usdt_solde, btc_solde
    while True:
        try:
            # Récupération des données pour les indicateurs
            klines = client.klines('BTCUSDT', '1m', limit=500)
            df = pd.DataFrame(klines)
            df = df.iloc[:, :6]
            df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            df['Date'] = pd.to_datetime(df['Date'], unit='ms')
            df.set_index('Date', inplace=True)
            df = df.astype(float)
            df['EMA200'] = ta.trend.EMAIndicator(df['Close'], window=200).ema_indicator()
            df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
            last_row = df.iloc[-1]
            prix = last_row['Close']
            ema200 = last_row['EMA200']
            rsi = last_row['RSI']
            # Logique d'achat
            if rsi < 30 and prix > ema200 and usdt_solde > 0:
                montant_usdt = usdt_solde
                montant_btc = montant_usdt / prix
                usdt_solde -= montant_usdt
                btc_solde += montant_btc
                # Mise à jour des soldes
                usdt_label.config(text=f"Solde USDT: {usdt_solde:.2f}")
                btc_label.config(text=f"Solde BTC: {btc_solde:.6f}")
                with open(USDT_FILE, 'w') as f:
                    json.dump({'solde': usdt_solde}, f)
                with open(BTC_FILE, 'w') as f:
                    json.dump({'solde': btc_solde}, f)
                # Enregistrement de la transaction
                transaction_id = str(uuid.uuid4())
                transaction = {
                    'id': transaction_id,
                    'action': 'achat',
                    'montant_btc': montant_btc,
                    'prix': prix,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'montant_usdt': montant_usdt
                }
                with open(ACHATS_FILE, 'a') as f:
                    json.dump(transaction, f)
                    f.write('\n')
                transaction_label.config(text=f"Dernière transaction ID: {transaction_id}")
                calculer_gains()
            # Logique de vente
            elif rsi > 70 and prix < ema200 and btc_solde > 0:
                montant_btc = btc_solde
                montant_usdt = montant_btc * prix
                btc_solde -= montant_btc
                usdt_solde += montant_usdt
                # Mise à jour des soldes
                usdt_label.config(text=f"Solde USDT: {usdt_solde:.2f}")
                btc_label.config(text=f"Solde BTC: {btc_solde:.6f}")
                with open(USDT_FILE, 'w') as f:
                    json.dump({'solde': usdt_solde}, f)
                with open(BTC_FILE, 'w') as f:
                    json.dump({'solde': btc_solde}, f)
                # Enregistrement de la transaction
                transaction_id = str(uuid.uuid4())
                transaction = {
                    'id': transaction_id,
                    'action': 'vente',
                    'montant_btc': montant_btc,
                    'prix': prix,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'montant_usdt': montant_usdt
                }
                with open(VENTES_FILE, 'a') as f:
                    json.dump(transaction, f)
                    f.write('\n')
                transaction_label.config(text=f"Dernière transaction ID: {transaction_id}")
                calculer_gains()
        except Exception as e:
            print("Erreur dans le trading automatique:", e)
        time.sleep(60)

# Création de la fenêtre principale
root = tk.Tk()
root.title("Cours du Bitcoin")
root.geometry("800x800")

# Affichage du prix actuel
price_label = tk.Label(root, text="Prix actuel du BTC: Chargement...", font=("Helvetica", 16))
price_label.pack(pady=10)

# Bouton pour afficher le graphique
graph_button = tk.Button(root, text="Afficher le graphique", command=afficher_graphique)
graph_button.pack(pady=10)

# Affichage des soldes
usdt_label = tk.Label(root, text=f"Solde USDT: {usdt_solde:.2f}", font=("Helvetica", 14))
usdt_label.pack(pady=5)

btc_label = tk.Label(root, text=f"Solde BTC: {btc_solde:.6f}", font=("Helvetica", 14))
btc_label.pack(pady=5)

# Ajout de solde USDT
usdt_entry = tk.Entry(root)
usdt_entry.pack(pady=5)
add_usdt_button = tk.Button(root, text="Ajouter USDT", command=add_usdt)
add_usdt_button.pack(pady=5)

# Boutons d'achat et de vente
buy_button = tk.Button(root, text="Acheter BTC", command=acheter_btc)
buy_button.pack(pady=10)

sell_button = tk.Button(root, text="Vendre BTC", command=vendre_btc)
sell_button.pack(pady=10)

# Affichage des gains/pertes
gains_label = tk.Label(root, text="Gains/Pertes: 0.00 USDT", font=("Helvetica", 14))
gains_label.pack(pady=5)

# Affichage du numéro de transaction
transaction_label = tk.Label(root, text="Dernière transaction ID: Aucun", font=("Helvetica", 12))
transaction_label.pack(pady=5)

# Lancement du thread de mise à jour du prix
price_thread = threading.Thread(target=update_price, daemon=True)
price_thread.start()

# Lancement du trading automatique dans un thread séparé
trading_thread = threading.Thread(target=trading_automatique, daemon=True)
trading_thread.start()

# Lancement de l'application
root.mainloop()
