#!/usr/bin/env python3
"""Whales Market Monitor - main script

Notes:
- This file intentionally imports configuration from `config.py`.
- Keep your `config.py` out of version control. 
""" 
import requests
import time
import re
import logging
from importlib import import_module

try:
    # config.py must be created from config.example.py by the user
    config = import_module('config')
    BOT_TOKEN = config.BOT_TOKEN
    CHAT_ID = config.CHAT_ID
    TOKENS = getattr(config, 'TOKENS', {})
    LOG_FILE_PATH = getattr(config, 'LOG_FILE_PATH', '/var/log/whales-monitor.log')
except Exception as e:
    raise SystemExit('Missing or invalid config.py. Copy config.example.py to config.py and fill values.') from e

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)

class WhalesMarketMonitor:
    def __init__(self, bot_token, chat_id, tokens, base_url=None):
        self.telegram_bot_token = bot_token
        self.telegram_chat_id = chat_id
        self.seen_order_ids = set()
        self.base_url = base_url or "https://api.whales.market/v2/offers"
        self.tokens = tokens
        self.previous_orders = {}
        self.initial_display_done = False

    def send_telegram_alert(self, message):
        """Send alert to Telegram bot"""
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logging.info("✅ Alert sent to Telegram")
                return True
            else:
                logging.warning(f"Telegram API returned status {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"❌ Telegram error: {e}")
        return False

    def fetch_orders(self, token, order_type):
        """Fetch orders from Whales.Market API"""
        chain_id = self.tokens[token]["chain"]
        params = {
            'type': order_type,
            'category_token': 'pre_market',
            'symbol': token,
            'status': 'open',
            'take': 10,
            'page': 1,
            'sort_price': 'DESC' if order_type == 'buy' else 'ASC',
            'chains': chain_id,
            'order_type': 'normal'
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            return data.get("data", {}).get("list", [])
        except Exception as e:
            logging.error(f"❌ API Error for {token} {order_type}: {e}")
            return []

    def parse_special_price(self, price_str):
        """Parse special price formats like '0.0₃78'"""
        if isinstance(price_str, (int, float)):
            return float(price_str)
        if not isinstance(price_str, str):
            return 0.0
        match = re.match(r'0\.0[₀₁₂₃₄₅₆₇₈₉](\d+)', price_str)
        if match:
            # convert unicode subscript to number of zeros
            subscript_char = price_str[3]
            subscript_map = {'₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
                           '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9'}
            zeros_count = int(subscript_map.get(subscript_char, '0'))
            remaining_digits = match.group(1)
            decimal_str = '0.' + '0' * zeros_count + remaining_digits
            try:
                return float(decimal_str)
            except:
                return 0.0
        try:
            return float(price_str)
        except:
            return 0.0

    def parse_order(self, order, side, token):
        """Parse order data from API response"""
        try:
            raw_price = order.get('price', '0')
            price = self.parse_special_price(raw_price)
            collateral = float(order.get('collateral', 0))
            amount = collateral / price if price > 0 else 0
            return {
                'id': order.get('id'),
                'side': side,
                'price': price,
                'amount': amount,
                'collateral': collateral,
                'token': token
            }
        except Exception as e:
            logging.error(f"❌ Parse error for {token} {side}: {e}")
            return None

    def get_best_order(self, orders, side):
        if not orders:
            return None
        valid = [o for o in orders if o and o['price'] > 0 and o['amount'] > 0]
        if not valid:
            return None
        if side == 'BUY':
            return max(valid, key=lambda x: x['price'])
        else:
            return max(valid, key=lambda x: x['collateral'])

    def has_order_changed(self, current_order, previous_order):
        if not current_order and not previous_order:
            return False
        if not current_order or not previous_order:
            return True
        return (current_order['price'] != previous_order['price'] or
                current_order['amount'] != previous_order['amount'] or
                current_order['collateral'] != previous_order['collateral'])

    def display_orders(self, all_orders, is_new=False):
        if is_new:
            title = "🚨 NEW ORDERS DETECTED 🚨"
        else:
            title = "📊 CURRENT MARKET ORDERS"
        print(f"\n{title}")
        print("=" * 60)
        for token, config in self.tokens.items():
            orders = all_orders.get(token, {})
            if orders.get('buy') or orders.get('sell'):
                print(f"{config.get('emoji','')} {token}")
                if orders.get('buy'):
                    b = orders['buy']
                    print(f"🟢 BUY: ${b['price']:.6f} | {b['amount']:,.0f} tokens | ${b['collateral']:,.0f}")
                if orders.get('sell'):
                    s = orders['sell']
                    print(f"🔴 SELL: ${s['price']:.6f} | {s['amount']:,.0f} tokens | ${s['collateral']:,.0f}")
                print("━━━━━━━━━━━━━━━━━━━━")

    def create_changed_orders_message(self, changed_orders):
        if not changed_orders:
            return None
        telegram_message = "🔄 <b>ORDER UPDATE DETECTED</b> 🔄\n\n"
        for order in changed_orders:
            if order is None:
                continue
            side = "BUY" if order['side'] == 'BUY' else "SELL"
            side_emoji = "🟢" if side == "BUY" else "🔴"
            token_emoji = self.tokens.get(order['token'], {}).get('emoji', '')
            telegram_message += f"{token_emoji} {side_emoji} <b>{order['token']} {side}</b>\n"
            telegram_message += f"💰 Price: ${order['price']:.6f}\n"
            telegram_message += f"📦 Amount: {order['amount']:,.0f} tokens\n"
            telegram_message += f"💵 Collateral: ${order['collateral']:,.0f}\n"
            telegram_message += "━━━━━━━━━━━━━━━━━━━━\n"
        return telegram_message

    def run(self, poll_interval=10):
        logging.info("🚀 Whales Market Monitor Started")
        logging.info(f"📡 Monitoring {', '.join(self.tokens.keys())} tokens every {poll_interval} seconds...")
        startup_msg = f"🤖 <b>Whales Market Monitor Started</b>\n\nMonitoring {', '.join(self.tokens.keys())} tokens every {poll_interval} seconds..."
        self.send_telegram_alert(startup_msg)

        while True:
            try:
                all_orders = {}
                changed_orders = []
                for token in self.tokens.keys():
                    buy_data = self.fetch_orders(token, 'buy')
                    buy_orders = [self.parse_order(o, 'BUY', token) for o in buy_data]
                    buy_orders = [o for o in buy_orders if o and o['price'] > 0 and o['amount'] > 0]
                    best_buy = self.get_best_order(buy_orders, 'BUY')

                    sell_data = self.fetch_orders(token, 'sell')
                    sell_orders = [self.parse_order(o, 'SELL', token) for o in sell_data]
                    sell_orders = [o for o in sell_orders if o and o['price'] > 0 and o['amount'] > 0]
                    best_sell = self.get_best_order(sell_orders, 'SELL')

                    all_orders[token] = {'buy': best_buy, 'sell': best_sell}

                    prev = self.previous_orders.get(token, {})
                    if self.has_order_changed(best_buy, prev.get('buy')):
                        changed_orders.append(best_buy)
                    if self.has_order_changed(best_sell, prev.get('sell')):
                        changed_orders.append(best_sell)

                    if best_buy:
                        self.seen_order_ids.add(best_buy['id'])
                    if best_sell:
                        self.seen_order_ids.add(best_sell['id'])

                self.previous_orders = all_orders.copy()

                if not self.initial_display_done:
                    self.display_orders(all_orders, is_new=False)
                    self.initial_display_done = True
                    print("\n⏰ Monitoring for order changes...")

                if changed_orders:
                    self.display_orders(all_orders, is_new=True)
                    telegram_message = self.create_changed_orders_message(changed_orders)
                    if telegram_message and self.send_telegram_alert(telegram_message):
                        print("✅ Alert sent to Telegram")
                    print("\n⏰ Monitoring for order changes...")

                time.sleep(poll_interval)
            except KeyboardInterrupt:
                logging.info("🛑 Monitor stopped by user!")
                break
            except Exception as e:
                logging.error(f"❌ Monitoring error: {e}")
                time.sleep(10)

if __name__ == '__main__':
    monitor = WhalesMarketMonitor(BOT_TOKEN, CHAT_ID, TOKENS)
    monitor.run()
