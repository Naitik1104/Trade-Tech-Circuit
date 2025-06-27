# TradeTech-Circuit - Binance Futures Testnet Trading Bot

Welcome to **TradeTech-Circuit**, a Flask-based trading bot designed for the **Binance Futures Testnet**. This project offers a simple yet powerful interface to:

- Place **Market**, **Limit**, and **Stop-Limit** orders  
- Monitor trades in real-time  
- Manage your trading activities through a responsive, finance-style web interface  

Built using Python and Flask, it integrates with the Binance API and provides a clean trading experience, especially useful for testing strategies on the Binance Futures Testnet.

---

## Features

- **Order Types**: Market, Limit, and Stop-Limit order support for `BTCUSDT`
- **Live Log Tab**: View real-time trade logs, reset automatically on reload
- **Robust Design**: Logs all API activity and errors in `trading_bot.log`
- **User Interface**: Responsive, modern UI mimicking trading platforms
- **Binance Testnet Ready**: Preconfigured for testnet usage
- **Symbol Validation**: Prevents invalid trading pairs

---

## Prerequisites

- Python 3.8 or higher
- Binance Futures Testnet API  
  🔗 [Register here](https://testnet.binancefuture.com) or [Authorize with Github](https://testnet.binance.vision/)
- Run ```pip install -r requirements.txt``` to install required dependencies.

---

### Project Structure

| File/Folder            | Description                                              |
|------------------------|----------------------------------------------------------|
| `main.py`       | **Main Flask application logic and Binance API handling**    |
| `templates/`           | HTML templates folder for Flask views                    |
| ├── `index.html`       | Main trading interface (home page)                       |
| ├── `order_result.html`| Displays order confirmation and details                  |
| └── `live_log.html`    | Real-time trading log interface                          |
| `.env.example`         | Example format API credentials (not committed to version control)       |
| `requirements.txt`     | List of required Python packages                         |
| `trading_bot.log`      | Log file storing API activity and errors                 |
| `README.md`            | Project documentation (this file)                        |

**Run main.py and open Flask in localhost:5000**
