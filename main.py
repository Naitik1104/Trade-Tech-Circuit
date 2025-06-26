import logging
import os
from flask import Flask, render_template, request, flash, redirect, url_for
from binance import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    filename='trading_bot.log',
    level=logging.DEBUG,  # Set to DEBUG to capture all levels
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Required for flash messages

# In-memory log storage (cleared on reload, limited to last 50 entries)
live_logs = []
MAX_LOGS = 50

class TradingBot:
    def __init__(self, api_key, api_secret, testnet=True):
        """Initialize the trading bot with Binance API credentials."""
        global live_logs
        live_logs = []  # Clear live logs on app reload
        try:
            self.client = Client(api_key, api_secret, testnet=testnet)
            if testnet:
                self.client.API_URL = 'https://testnet.binancefuture.com'
            self.symbol = 'BTCUSDT'  # Fixed trading pair
            self._validate_api_connection()
            self._validate_symbol()
            add_live_log(f"TradingBot initialized for {self.symbol}")
            logging.info("TradingBot initialized successfully")
        except Exception as e:
            logging.error(f"Initialization failed: {str(e)}")
            add_live_log(f"Initialization failed: {str(e)}")
            raise

    def _validate_api_connection(self):
        """Validate API key and connection by fetching server time."""
        try:
            server_time = self.client.get_server_time()
            logging.info(f"API connection validated: Server time = {server_time}")
            add_live_log(f"API connection validated: Server time = {server_time}")
        except BinanceAPIException as e:
            logging.error(f"API connection failed: {str(e)}")
            add_live_log(f"API connection failed: {str(e)}")
            raise ValueError(f"Invalid API key or connection: {str(e)}")

    def _validate_symbol(self):
        """Verify if the symbol is valid on the exchange."""
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
        """Validate order quantity."""
        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            try:
                info = self.client.get_symbol_info(self.symbol)
                if not info or 'quantityPrecision' not in info:
                    logging.warning(f"Symbol info for {self.symbol} missing quantityPrecision. Using default precision 3.")
                    add_live_log(f"Warning: Using default quantity precision 3 for {self.symbol}")
                    precision = 3  # Fallback for BTCUSDT
                else:
                    precision = info['quantityPrecision']
            except BinanceAPIException as e:
                logging.error(f"API error fetching symbol info: {str(e)}. Using default precision 3.")
                add_live_log(f"Error fetching symbol info: {str(e)}. Using default precision 3")
                precision = 3  # Fallback
            return round(quantity, precision)
        except ValueError as e:
            logging.error(f"Invalid quantity: {str(e)}")
            add_live_log(f"Invalid quantity: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error validating quantity: {str(e)}")
            add_live_log(f"Unexpected error validating quantity: {str(e)}")
            raise

    def place_market_order(self, side, quantity):
        """Place a market order."""
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
            order_id = order.get('orderId', 'N/A')  # Fallback if orderId is missing
            logging.info(f"Market order placed: {side} {quantity} {self.symbol} - Order ID: {order_id}")
            logging.debug(f"Full order response: {order}")  # Log full response for debugging
            add_live_log(f"Market order placed: {side} {quantity} {self.symbol} - Order ID: {order_id}")
            return order
        except BinanceAPIException as e:
            logging.error(f"Market order failed: {str(e)} - Code: {e.code}, Message: {e.message}")
            add_live_log(f"Market order failed: {str(e)}")
            raise
        except ValueError as e:
            logging.error(f"Market order failed: {str(e)}")
            add_live_log(f"Market order failed: {str(e)}")
            raise

    def place_limit_order(self, side, quantity, price):
        """Place a limit order."""
        try:
            quantity = self.validate_quantity(quantity)
            price = float(price)
            if price <= 0:
                raise ValueError("Price must be positive")
            info = self.client.get_symbol_info(self.symbol)
            if not info or 'pricePrecision' not in info:
                logging.warning(f"Symbol info for {self.symbol} missing pricePrecision. Using default precision 2.")
                add_live_log(f"Warning: Using default price precision 2 for {self.symbol}")
                price_precision = 2  # Fallback for BTCUSDT
            else:
                price_precision = info['pricePrecision']
            price = round(price, price_precision)
            order = self.client.create_order(
                symbol=self.symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=price
            )
            order_id = order.get('orderId', 'N/A')  # Fallback if orderId is missing
            logging.info(f"Limit order placed: {side} {quantity} {self.symbol} at {price} - Order ID: {order_id}")
            logging.debug(f"Full order response: {order}")  # Log full response for debugging
            add_live_log(f"Limit order placed: {side} {quantity} {self.symbol} at {price} - Order ID: {order_id}")
            return order
        except BinanceAPIException as e:
            logging.error(f"Limit order failed: {str(e)} - Code: {e.code}, Message: {e.message}")
            add_live_log(f"Limit order failed: {str(e)}")
            raise
        except ValueError as e:
            logging.error(f"Limit order failed: {str(e)}")
            add_live_log(f"Limit order failed: {str(e)}")
            raise

    def place_stop_limit_order(self, side, quantity, stop_price, limit_price):
        """Place a stop-limit order."""
        try:
            quantity = self.validate_quantity(quantity)
            stop_price = float(stop_price)
            limit_price = float(limit_price)
            if stop_price <= 0 or limit_price <= 0:
                raise ValueError("Stop price and limit price must be positive")
            info = self.client.get_symbol_info(self.symbol)
            if not info or 'pricePrecision' not in info:
                logging.warning(f"Symbol info for {self.symbol} missing pricePrecision. Using default precision 2.")
                add_live_log(f"Warning: Using default price precision 2 for {self.symbol}")
                price_precision = 2  # Fallback for BTCUSDT
            else:
                price_precision = info['pricePrecision']
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
            order_id = order.get('orderId', 'N/A')  # Fallback if orderId is missing
            logging.info(f"Stop-limit order placed: {side} {quantity} {self.symbol} "
                         f"stop={stop_price}, limit={limit_price} - Order ID: {order_id}")
            logging.debug(f"Full order response: {order}")  # Log full response for debugging
            add_live_log(f"Stop-limit order placed: {side} {quantity} {self.symbol} "
                         f"stop={stop_price}, limit={limit_price} - Order ID: {order_id}")
            return order
        except BinanceAPIException as e:
            logging.error(f"Stop-limit order failed: {str(e)} - Code: {e.code}, Message: {e.message}")
            add_live_log(f"Stop-limit order failed: {str(e)}")
            raise
        except ValueError as e:
            logging.error(f"Stop-limit order failed: {str(e)}")
            add_live_log(f"Stop-limit order failed: {str(e)}")
            raise

    def get_order_status(self, order_id):
        """Check the status of an order."""
        try:
            order = self.client.get_order(symbol=self.symbol, orderId=order_id)
            logging.info(f"Order status checked: {order['orderId']} - {order['status']}")
            add_live_log(f"Order status checked: {order['orderId']} - {order['status']}")
            return order
        except BinanceAPIException as e:
            logging.error(f"Order status check failed: {str(e)} - Code: {e.code}, Message: {e.message}")
            add_live_log(f"Order status check failed: {str(e)}")
            raise

# Format order details for display with fallback for 'time'
def format_order_details(order):
    details = {
        'order_id': order.get('orderId', 'N/A'),
        'symbol': order.get('symbol', 'N/A'),
        'side': order.get('side', 'N/A'),
        'type': order.get('type', 'N/A'),
        'quantity': order.get('origQty', 'N/A'),
        'status': order.get('status', 'N/A'),
    }
    # Use transactTime as fallback if time is missing
    timestamp = order.get('time') or order.get('transactTime')
    if timestamp:
        details['time'] = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
    else:
        details['time'] = 'N/A'
        logging.warning(f"Order response missing 'time' and 'transactTime': {order}")
        add_live_log(f"Warning: Order response missing timestamp for order {order.get('orderId', 'N/A')}")
    if 'price' in order and order['price'] != '0':
        details['price'] = order['price']
    if 'stopPrice' in order and order['stopPrice'] != '0':
        details['stop_price'] = order['stopPrice']
    return details

# Utility function to add logs to live_logs
def add_live_log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d | %H:%M:%S')  # Gap between date and time
    log_entry = f"{timestamp} - {message}"
    live_logs.append(log_entry)
    if len(live_logs) > MAX_LOGS:
        live_logs.pop(0)  # Keep only the last MAX_LOGS entries

# Initialize TradingBot
try:
    bot = TradingBot(API_KEY, API_SECRET, testnet=True)
except Exception as e:
    logging.error(f"Bot initialization failed: {str(e)}")
    add_live_log(f"Bot initialization failed: {str(e)}")
    print(f"Failed to initialize bot: {str(e)}. Check .env file and API credentials.")
    exit(1)

# Flask Routes
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

@app.route('/live_log')
def live_log():
    return render_template('live_log.html', logs=live_logs)

if __name__ == "__main__":
    app.run(debug=True)
