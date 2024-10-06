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
    montant_usdt = min(100, usdt_solde)
    if montant_usdt <= 0:
        messagebox.showerror("Erreur", "Solde USDT insuffisant.")
        return
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
        'prix_achat': current_price,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'montant_usdt': montant_usdt
    }
    with open(ACHATS_FILE, 'a') as f:
        json.dump(transaction, f)
        f.write('\n')
    # Enregistrement de la position ouverte
    position = {
        'montant_btc': montant_btc,
        'prix_achat': current_price
    }
    enregistrer_position(position)
    transaction_label.config(text=f"Dernière transaction ID: {transaction_id}")
    calculer_gains()


# Fonction pour vendre du BTC
def vendre_btc():
    global usdt_solde, btc_solde
    montant_usdt = min(100, btc_solde * current_price)
    if montant_usdt <= 0:
        messagebox.showerror("Erreur", "Solde BTC insuffisant.")
        return
    montant_btc = montant_usdt / current_price
    if montant_btc > btc_solde:
        montant_btc = btc_solde
    btc_solde -= montant_btc
    usdt_solde += montant_btc * current_price
    # Mise à jour des soldes
    usdt_label.config(text=f"Solde USDT: {usdt_solde:.2f}")
    btc_label.config(text=f"Solde BTC: {btc_solde:.6f}")
    with open(USDT_FILE, 'w') as f:
        json.dump({'solde': usdt_solde}, f)
    with open(BTC_FILE, 'w') as f:
        json.dump({'solde': btc_solde}, f)
    # Enregistrement de la transaction
    transaction_id = str(uuid.uuid4())
    prix_vente = current_price
    transaction = {
        'id': transaction_id,
        'action': 'vente',
        'montant_btc': montant_btc,
        'prix_vente': prix_vente,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'montant_usdt': montant_usdt
    }
    with open(VENTES_FILE, 'a') as f:
        json.dump(transaction, f)
        f.write('\n')
    # Mise à jour des positions ouvertes
    deduire_positions(montant_btc)
    transaction_label.config(text=f"Dernière transaction ID: {transaction_id}")
    calculer_gains()


# Fonction pour afficher le graphique des prix
def afficher_graphique():
    try:
        klines = client.klines('BTCUSDT', '1m', limit=500)
        df = pd.DataFrame(klines)
        df = df.iloc[:, :6]
        df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        df['Date'] = pd.to_datetime(df['Date'], unit='ms')
        df.set_index('Date', inplace=True)
        df = df.astype(float)

        # Calculer les niveaux de Fibonacci
        N = 100
        recent_df = df.tail(N)
        max_price = recent_df['High'].max()
        min_price = recent_df['Low'].min()
        price_diff = max_price - min_price

        levels = {
            'Level 23.6%': max_price - price_diff * 0.236,
            'Level 38.2%': max_price - price_diff * 0.382,
            'Level 50%': max_price - price_diff * 0.5,
            'Level 61.8%': max_price - price_diff * 0.618,
            'Level 78.6%': max_price - price_diff * 0.786
        }

        # Préparer les lignes pour les niveaux de Fibonacci
        addplot = []
        for level in levels.values():
            addplot.append(mpf.make_addplot([level]*len(df), linestyle='--'))

        # Afficher le graphique avec les niveaux de Fibonacci
        mpf.plot(df, type='candle', volume=True, style='binance', addplot=addplot)
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'afficher le graphique: {e}")

# Fonction pour calculer et afficher les gains/pertes
def calculer_gains():
    # Gains réalisés
    try:
        with open('gains_realises.json', 'r') as f:
            gains_realises = json.load(f)
    except FileNotFoundError:
        gains_realises = []
    total_gains_realises = sum(item['gain'] for item in gains_realises)
    # Gains non réalisés
    try:
        with open('positions.json', 'r') as f:
            positions = json.load(f)
    except FileNotFoundError:
        positions = []
    gains_non_realises = sum((current_price - pos['prix_achat']) * pos['montant_btc'] for pos in positions)
    # Total des gains
    total_gains = total_gains_realises + gains_non_realises
    gains_label.config(text=f"Gains/Pertes: {total_gains:.2f} USDT")

# Fonction de trading automatique
def trading_automatique():
    global usdt_solde, btc_solde
    while True:
        try:
            # Récupération des données de marché
            klines = client.klines('BTCUSDT', '1m', limit=500)
            df = pd.DataFrame(klines)
            df = df.iloc[:, :6]
            df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            df['Date'] = pd.to_datetime(df['Date'], unit='ms')
            df.set_index('Date', inplace=True)
            df = df.astype(float)

            # Calculer les indicateurs techniques
            df['EMA200'] = ta.trend.EMAIndicator(df['Close'], window=200).ema_indicator()
            df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()

            # Récupérer les dernières valeurs
            last_row = df.iloc[-1]
            prix = last_row['Close']
            ema200 = last_row['EMA200']
            rsi = last_row['RSI']

            # Afficher les valeurs pour debug
            print(f"RSI: {rsi:.2f}, Prix: {prix:.2f}, EMA200: {ema200:.2f}")

            # Logique d'achat
            if rsi < 30 and prix > ema200 and usdt_solde > 0:
                print("Conditions d'achat remplies, exécution de l'achat.")
                acheter_btc()

            # Logique de vente
            elif rsi > 70 and prix < ema200 and btc_solde > 0:
                print("Conditions de vente remplies, exécution de la vente.")
                vendre_btc()

            else:
                print("Conditions non remplies, aucune action exécutée.")

        except Exception as e:
            print("Erreur dans le trading automatique:", e)
        time.sleep(60)

def realiser_gain(position, montant_btc_vendu):
    gain = (current_price - position['prix_achat']) * montant_btc_vendu
    try:
        with open('gains_realises.json', 'r') as f:
            gains = json.load(f)
    except FileNotFoundError:
        gains = []
    gains.append({
        'montant_btc_vendu': montant_btc_vendu,
        'prix_achat': position['prix_achat'],
        'prix_vente': current_price,
        'gain': gain,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    with open('gains_realises.json', 'w') as f:
        json.dump(gains, f)

def enregistrer_position(position):
    try:
        with open('positions.json', 'r') as f:
            positions = json.load(f)
    except FileNotFoundError:
        positions = []
    positions.append(position)
    with open('positions.json', 'w') as f:
        json.dump(positions, f)


def deduire_positions(montant_btc_vendu):
    try:
        with open('positions.json', 'r') as f:
            positions = json.load(f)
    except FileNotFoundError:
        positions = []
    montant_btc_restante = montant_btc_vendu
    nouvelles_positions = []
    for position in positions:
        if montant_btc_restante >= position['montant_btc']:
            montant_btc_restante -= position['montant_btc']
            # Enregistrer la réalisation de la position
            realiser_gain(position, position['montant_btc'])
        else:
            # Mettre à jour la position restante
            position_restante = {
                'montant_btc': position['montant_btc'] - montant_btc_restante,
                'prix_achat': position['prix_achat']
            }
            nouvelles_positions.append(position_restante)
            # Enregistrer la réalisation partielle
            realiser_gain(position, montant_btc_restante)
            montant_btc_restante = 0
            nouvelles_positions.extend(positions[positions.index(position)+1:])
            break
    with open('positions.json', 'w') as f:
        json.dump(nouvelles_positions, f)


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
