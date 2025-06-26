import logging
import os
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from binance import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException
from datetime import datetime
from dotenv import load_dotenv
import difflib

logging.basicConfig(
    filename='trading_bot.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

load_dotenv()
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

app = Flask(__name__)
app.secret_key = 'super_secret_key'

live_logs = []
MAX_LOGS = 50

def add_live_log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d | %H:%M:%S')
    log_entry = f"{timestamp} - {message}"
    live_logs.append(log_entry)
    if len(live_logs) > MAX_LOGS:
        live_logs.pop(0)

class TradingBot:
    def __init__(self, api_key, api_secret, testnet=True):
        global live_logs
        live_logs = []
        self.client = Client(api_key, api_secret, testnet=testnet)
        if testnet:
            self.client.API_URL = 'https://testnet.binancefuture.com'
        self.symbol = 'BTCUSDT'
        self._validate_api_connection()
        self._validate_symbol()
        add_live_log(f"TradeTech-Circuit Bot initialized for {self.symbol}")
        logging.info("TradeTech-Circuit Bot initialized successfully")

    def _validate_api_connection(self):
        try:
            server_time = self.client.get_server_time()
            logging.info(f"API connection validated: Server time = {server_time}")
            add_live_log(f"API connection validated: Server time = {server_time}")
        except BinanceAPIException as e:
            logging.error(f"API connection failed: {str(e)}")
            add_live_log(f"API connection failed: {str(e)}")
            raise ValueError(f"Invalid API key or connection: {str(e)}")

    def _validate_symbol(self):
        try:
            info = self.client.get_symbol_info(self.symbol)
            if not info:
                raise ValueError(f"Symbol {self.symbol} not found on the exchange")
            logging.info(f"Symbol {self.symbol} validated: {info}")
            add_live_log(f"Symbol {self.symbol} validated")
        except BinanceAPIException as e:
            logging.error(f"Failed to validate symbol {self.symbol}: {str(e)}")
            add_live_log(f"Failed to validate symbol {self.symbol}: {str(e)}")
            raise

    def validate_quantity(self, quantity):
        quantity = float(quantity)
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        try:
            info = self.client.get_symbol_info(self.symbol)
            precision = info.get('quantityPrecision', 3) if info else 3
        except BinanceAPIException as e:
            logging.error(f"API error fetching symbol info: {str(e)}. Using default precision 3.")
            add_live_log(f"Error fetching symbol info: {str(e)}. Using default precision 3")
            precision = 3
        return round(quantity, precision)

    def place_market_order(self, side, quantity):
        try:
            quantity = self.validate_quantity(quantity)
            logging.info(f"Attempting market order: side={side}, quantity={quantity}, symbol={self.symbol}")
            add_live_log(f"Attempting market order: {side} {quantity} {self.symbol}")
            order = self.client.create_order(
                symbol=self.symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            order_id = order.get('orderId', 'N/A')
            logging.info(f"Market order placed: {side} {quantity} {self.symbol} - Order ID: {order_id}")
            add_live_log(f"Market order placed: {side} {quantity} {self.symbol} - Order ID: {order_id}")
            return order
        except BinanceAPIException as e:
            logging.error(f"Market order failed: {str(e)}")
            add_live_log(f"Market order failed: {str(e)}")
            raise

    def place_limit_order(self, side, quantity, price):
        try:
            quantity = self.validate_quantity(quantity)
            price = float(price)
            if price <= 0:
                raise ValueError("Price must be positive")
            info = self.client.get_symbol_info(self.symbol)
            price_precision = info.get('pricePrecision', 2) if info else 2
            price = round(price, price_precision)
            order = self.client.create_order(
                symbol=self.symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=price
            )
            order_id = order.get('orderId', 'N/A')
            logging.info(f"Limit order placed: {side} {quantity} {self.symbol} at {price} - Order ID: {order_id}")
            add_live_log(f"Limit order placed: {side} {quantity} {self.symbol} at {price} - Order ID: {order_id}")
            return order
        except BinanceAPIException as e:
            logging.error(f"Limit order failed: {str(e)}")
            add_live_log(f"Limit order failed: {str(e)}")
            raise

    def place_stop_limit_order(self, side, quantity, stop_price, limit_price):
        try:
            quantity = self.validate_quantity(quantity)
            stop_price = float(stop_price)
            limit_price = float(limit_price)
            if stop_price <= 0 or limit_price <= 0:
                raise ValueError("Stop price and limit price must be positive")
            info = self.client.get_symbol_info(self.symbol)
            price_precision = info.get('pricePrecision', 2) if info else 2
            stop_price = round(stop_price, price_precision)
            limit_price = round(limit_price, price_precision)
            order = self.client.create_order(
                symbol=self.symbol,
                side=side,
                type=ORDER_TYPE_STOP,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                stopPrice=stop_price,
                price=limit_price
            )
            order_id = order.get('orderId', 'N/A')
            logging.info(f"Stop-limit order placed: {side} {quantity} {self.symbol} stop={stop_price}, limit={limit_price} - Order ID: {order_id}")
            add_live_log(f"Stop-limit order placed: {side} {quantity} {self.symbol} stop={stop_price}, limit={limit_price} - Order ID: {order_id}")
            return order
        except BinanceAPIException as e:
            logging.error(f"Stop-limit order failed: {str(e)}")
            add_live_log(f"Stop-limit order failed: {str(e)}")
            raise

    def get_order_status(self, order_id):
        try:
            order = self.client.get_order(symbol=self.symbol, orderId=order_id)
            logging.info(f"Order status checked: {order['orderId']} - {order['status']}")
            add_live_log(f"Order status checked: {order['orderId']} - {order['status']}")
            return order
        except BinanceAPIException as e:
            logging.error(f"Order status check failed: {str(e)}")
            add_live_log(f"Order status check failed: {str(e)}")
            raise

    def get_account_balance(self):
        try:
            account = self.client.get_account()
            balance = next((b for b in account['balances'] if float(b['free']) > 0), None)
            if balance:
                return f"Current Testnet balance:\n- Asset: {balance['asset']}\n- Free: {balance['free']}"
            return "No available balance found on Testnet."
        except BinanceAPIException as e:
            logging.error(f"Balance check failed: {str(e)}")
            add_live_log(f"Balance check failed: {str(e)}")
            return f"Error fetching balance: {str(e)}"

    def cancel_order(self, order_id):
        try:
            self.client.cancel_order(symbol=self.symbol, orderId=order_id)
            logging.info(f"Order cancelled: {order_id}")
            add_live_log(f"Order cancelled: {order_id}")
            return f"Order {order_id} cancelled on Testnet."
        except BinanceAPIException as e:
            logging.error(f"Order cancellation failed: {str(e)}")
            add_live_log(f"Order cancellation failed: {str(e)}")
            return f"Failed to cancel order {order_id}: {str(e)}"

def format_order_details(order):
    details = {
        'order_id': order.get('orderId', 'N/A'),
        'symbol': order.get('symbol', 'N/A'),
        'side': order.get('side', 'N/A'),
        'type': order.get('type', 'N/A'),
        'quantity': order.get('origQty', 'N/A'),
        'status': order.get('status', 'N/A'),
    }
    timestamp = order.get('time') or order.get('transactTime')
    if timestamp:
        details['time'] = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
    else:
        details['time'] = 'N/A'
    if 'price' in order and order['price'] != '0':
        details['price'] = order['price']
    if 'stopPrice' in order and order['stopPrice'] != '0':
        details['stop_price'] = order['stopPrice']
    return details

def parse_command(command, bot):
    parts = command.lower().strip().split()
    if not parts:
        return "Type a command or type 'help' for sample commands."

    action = parts[0]
    available_commands = ['buy', 'sell', 'limit', 'stop_limit', 'status', 'balance', 'cancel', 'live_log', 'help', 'about_app', 'features', 'how_to_use', 'supported_markets', 'trading_tips', 'faq']  
    all_commands = available_commands + ['hi', 'hello', 'thank_you']  

    if action not in all_commands:
        suggestions = difflib.get_close_matches(action, all_commands, n=1, cutoff=0.6)
        if suggestions:
            action = suggestions[0]
        else:
            return "Command not recognized. Type 'help' for available commands."

    try:
        if action == 'help':
            return ("Available commands:\n"
                    "- `buy <quantity>`: Place a market buy order (e.g., 'buy 0.001')\n"
                    "- `sell <quantity>`: Place a market sell order (e.g., 'sell 0.001')\n"
                    "- `limit <buy/sell> <quantity> <price>`: Place a limit order (e.g., 'limit buy 0.001 30000')\n"
                    "- `stop_limit <buy/sell> <quantity> <stop_price> <limit_price>`: Place a stop-limit order (e.g., 'stop_limit buy 0.001 29000 29500')\n"
                    "- `status <order_id>`: Check order status (e.g., 'status 123456')\n"
                    "- `balance`: Check your Testnet account balance\n"
                    "- `cancel <order_id>`: Cancel an order (e.g., 'cancel 123456')\n"
                    "- `live_log`: View recent trading activities\n"
                    "- `about_app`: Learn about TradeTech-Circuit\n"
                    "- `features`: Discover app features\n"
                    "- `how_to_use`: Get usage instructions\n"
                    "- `supported_markets`: See supported markets\n"
                    "- `trading_tips`: Get trading advice\n"
                    "- `faq`: View frequently asked questions\n"
                    "Ready to explore? Pick a command!")

        elif action == 'live log' or action == 'display live log':
            if live_logs:
                return "Recent trading activities:\n" + "\n".join(f"- {log}" for log in live_logs[-5:])
            return "No trading activities yet. Start trading to see logs!"

        elif action == 'about app' or 'What does this app do':
            return ("About TradeTech-Circuit:\n"
                    "- A powerful trading assistant for Binance Futures Testnet\n"
                    "- Designed to simplify trading with real-time control\n"
                    "- Built by xAI for educational and testing purposes")

        elif action == 'features':
            return ("Key features:\n"
                    "- Execute market, limit, and stop-limit orders\n"
                    "- Monitor order status and account balance\n"
                    "- View live trading logs\n"
                    "- Access detailed app info and tips")

        elif action == 'how to use':
            return ("How to use TradeTech-Circuit:\n"
                    "- Click the 💬 icon to open the chat\n"
                    "- Type commands like 'buy 0.001' or 'help'\n"
                    "- Use the web forms for manual trading\n"
                    "- Check logs via 'live_log' command")

        elif action == 'supported markets':
            return ("Supported markets (Testnet):\n"
                    "- Currently supports BTCUSDT\n"
                    "- More markets may be added in future updates")

        elif action == 'trading tips':
            return ("Trading tips:\n"
                    "- Start with small quantities on Testnet\n"
                    "- Use limit orders to control prices\n"
                    "- Monitor logs for order success\n"
                    "- Practice before using real funds")

        elif action == 'faq':
            return ("Frequently Asked Questions:\n"
                    "- Q: Is this real money? A: No, it’s Testnet only\n"
                    "- Q: How do I get API keys? A: Sign up on Binance Testnet\n"
                    "- Q: Can I trade other coins? A: Currently BTCUSDT only")

        elif action == 'hi' or action == 'hello':
            return "Hello! Welcome to TradeTech-Circuit. How can I assist you today?"

        elif action == 'thank you':
            return "You're welcome! Happy trading with TradeTech-Circuit."

        elif action == 'buy' or action == 'sell':
            if len(parts) < 2:
                return "Please provide a quantity (e.g., 'buy 0.001')."
            quantity = parts[1]
            side = 'BUY' if action == 'buy' else 'SELL'
            order = bot.place_market_order(side, quantity)
            return f"Market order placed on Testnet:\n- Side: {side}\n- Quantity: {quantity} {bot.symbol}\n- Order ID: {order.get('orderId', 'N/A')}"

        elif action == 'limit':
            if len(parts) < 4 or parts[1] not in ['buy', 'sell']:
                return "Use 'limit <buy/sell> <quantity> <price>' (e.g., 'limit buy 0.001 30000')."
            side = 'BUY' if parts[1] == 'buy' else 'SELL'
            quantity = parts[2]
            price = parts[3]
            order = bot.place_limit_order(side, quantity, price)
            return f"Limit order placed on Testnet:\n- Side: {side}\n- Quantity: {quantity} {bot.symbol}\n- Price: {price}\n- Order ID: {order.get('orderId', 'N/A')}"

        elif action == 'stop limit':
            if len(parts) < 5 or parts[1] not in ['buy', 'sell']:
                return "Use 'stop_limit <buy/sell> <quantity> <stop_price> <limit_price>' (e.g., 'stop_limit buy 0.001 29000 29500')."
            side = 'BUY' if parts[1] == 'buy' else 'SELL'
            quantity = parts[2]
            stop_price = parts[3]
            limit_price = parts[4]
            order = bot.place_stop_limit_order(side, quantity, stop_price, limit_price)
            return f"Stop-limit order placed on Testnet:\n- Side: {side}\n- Quantity: {quantity} {bot.symbol}\n- Stop Price: {stop_price}\n- Limit Price: {limit_price}\n- Order ID: {order.get('orderId', 'N/A')}"

        elif action == 'status':
            if len(parts) < 2:
                return "Please provide an order ID (e.g., 'status 123456')."
            order_id = int(parts[1]) 
            order = bot.get_order_status(order_id)
            return f"Order status on Testnet:\n- Order ID: {order['orderId']}\n- Status: {order['status']}\n- Quantity: {order.get('origQty', 'N/A')} {bot.symbol}"

        elif action == 'balance':
            return bot.get_account_balance()

        elif action == 'cancel':
            if len(parts) < 2:
                return "Please provide an order ID (e.g., 'cancel 123456')."
            order_id = int(parts[1])  
            return bot.cancel_order(order_id)

        else:
            return "Command not recognized. Type 'help' for available commands."

    except (ValueError, BinanceAPIException) as e:
        logging.error(f"Command execution failed: {str(e)}")
        add_live_log(f"Command failed: {str(e)}")
        return f"Error: {str(e)}. Try again or type 'help'."
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        add_live_log(f"Unexpected error: {str(e)}")
        return f"Unexpected error occurred: {str(e)}. Contact support or type 'help'."

try:
    bot = TradingBot(API_KEY, API_SECRET, testnet=True)
except Exception as e:
    logging.error(f"Bot initialization failed: {str(e)}")
    add_live_log(f"Bot initialization failed: {str(e)}")
    print(f"Failed to initialize bot: {str(e)}. Check .env file and API credentials.")
    exit(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/place_order', methods=['POST'])
def place_order():
    order_type = request.form.get('order_type')
    side = request.form.get('side')
    quantity = request.form.get('quantity')
    try:
        if order_type == 'market':
            order = bot.place_market_order(side, quantity)
        elif order_type == 'limit':
            price = request.form.get('price')
            order = bot.place_limit_order(side, quantity, price)
        elif order_type == 'stop_limit':
            stop_price = request.form.get('stop_price')
            limit_price = request.form.get('limit_price')
            order = bot.place_stop_limit_order(side, quantity, stop_price, limit_price)
        else:
            flash("Invalid order type", "error")
            return redirect(url_for('index'))
        
        flash("Order placed successfully!", "success")
        return render_template('order_result.html', order=format_order_details(order))
    except Exception as e:
        flash(f"Error placing order: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/check_status', methods=['POST'])
def check_status():
    order_id = request.form.get('order_id')
    try:
        order = bot.get_order_status(order_id)
        flash("Order status retrieved successfully!", "success")
        return render_template('order_result.html', order=format_order_details(order))
    except Exception as e:
        flash(f"Error checking order status: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/process_command', methods=['POST'])
def process_command():
    command = request.form.get('command', '').strip()
    response = parse_command(command, bot)
    return jsonify({'response': response, 'command': command})

@app.route('/live_log')
def live_log():
    return render_template('live_log.html', logs=live_logs)

if __name__ == "__main__":
    app.run(debug=True)
