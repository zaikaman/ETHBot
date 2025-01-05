import imaplib
import email
from email.header import decode_header
import telebot
import asyncio
from metaapi_cloud_sdk import MetaApi

# Telegram bot token and chat ID
TOKEN = '7594762357:AAGCP0Lx-qjZIspsOH4eaC8bcVqwZIivWDo'
CHAT_ID = '-1002277376839'  # Replace with your Telegram chat ID

# MetaApi configuration
METAAPI_TOKEN = 'eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiJjZWRjZmY5MGQ2OGJiMzY0ZDQyMjAwMzI1MDcxYjc2NSIsInBlcm1pc3Npb25zIjpbXSwiYWNjZXNzUnVsZXMiOlt7ImlkIjoidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpIiwibWV0aG9kcyI6WyJ0cmFkaW5nLWFjY291bnQtbWFuYWdlbWVudC1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibWV0YWFwaS1yZXN0LWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibWV0YWFwaS1ycGMtYXBpIiwibWV0aG9kcyI6WyJtZXRhYXBpLWFwaTp3czpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibWV0YWFwaS1yZWFsLXRpbWUtc3RyZWFtaW5nLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6d3M6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFzdGF0cy1hcGkiLCJtZXRob2RzIjpbIm1ldGFzdGF0cy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoicmlzay1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsicmlzay1tYW5hZ2VtZW50LWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJjb3B5ZmFjdG9yeS1hcGkiLCJtZXRob2RzIjpbImNvcHlmYWN0b3J5LWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJtdC1tYW5hZ2VyLWFwaSIsIm1ldGhvZHMiOlsibXQtbWFuYWdlci1hcGk6cmVzdDpkZWFsaW5nOio6KiIsIm10LW1hbmFnZXItYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6ImJpbGxpbmctYXBpIiwibWV0aG9kcyI6WyJiaWxsaW5nLWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19XSwidG9rZW5JZCI6IjIwMjEwMjEzIiwiaW1wZXJzb25hdGVkIjpmYWxzZSwicmVhbFVzZXJJZCI6ImNlZGNmZjkwZDY4YmIzNjRkNDIyMDAzMjUwNzFiNzY1IiwiaWF0IjoxNzI5NTAyNDE1fQ.c7CYGJ9FByWeG1gBujUi_iaqDvyKkqCYwPIlW1SkhvopdzI454e2byl3rc_QmyugKChFnY0NJ2yM2c0_psghefzWv134ZpZzX7wNmLrlh5PDSwMffbTakI079Bw4RxsJgZPyWzgul_RetAc_mwauIwkiqrRu7RWk3sl6cqgmmEFkJuWOaGG_T53X_RUZ32StXMN05naiwq2iMZ0zU0_m97AiHHr_3jXrZpvAuOP9hFJ0ng3Zh5CoPwbH3ivIe-QygEFoScj0fHBguNvusgCbhE5myE5BVvtQVrBtq0swJzkkU9gvOFQWxmasekhVJjFTemh0mSOkXj-jMHWKt7LX8MR_w_F51riOMA4KbcyibgIUhy92aXNFQJoDlLlta2o4gHibJz0OKa7Rjdy0pkRrG5mhyiCl9WfXww3873xQzAaf3Q5ZtcCor2hh9MGmpUVVjumm5QlyB8GRVT2wJ2haq55qnwY0FFG5c6GOMDCbeGbvCkG92ZOvcHxVh6z3OKoG6GlUZhyZXWiByZOnE9LDLLyJjBRTzIgcnuVLnIZg1NS7S1hRkelmjoX1O9buz-U4vOwSee0q83zSUEniaj4YHe1iDZcT1_CXA79HYl7AIIk0fNcpbVBiXZJ4OSs4hZd3Kr-QHavrtRtUbt4Tt0095_dHDmsH0GShuka3ogIPwjs'  # Replace with your MetaApi token
ACCOUNT_ID = '284d1e8c-56d8-4457-80b2-cbe5b00a8d43'  # Replace with your MetaApi account ID

# Gmail Setup
IMAP_SERVER = "imap.gmail.com"
IMAP_USER = "thinhgpt1706@gmail.com"  # Replace with your Gmail account
IMAP_PASS = "xgxn kjcv haqf sjxz"   # Replace with your Gmail app-specific password

# Email checking interval (in seconds)
CHECK_INTERVAL = 1

# Initialize Telegram bot
bot = telebot.TeleBot(TOKEN)

# Async function to check email
async def check_email():
    mail = await asyncio.to_thread(imaplib.IMAP4_SSL, IMAP_SERVER)
    await asyncio.to_thread(mail.login, IMAP_USER, IMAP_PASS)
    await asyncio.to_thread(mail.select, "inbox")
    status, messages = await asyncio.to_thread(mail.search, None, 'UNSEEN')
    email_ids = messages[0].split()

    if not email_ids:
        return

    for email_id in email_ids:
        res, msg = await asyncio.to_thread(mail.fetch, email_id, "(RFC822)")
        for response_part in msg:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding)

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            await process_email(subject, body)
                else:
                    body = msg.get_payload(decode=True).decode()
                    await process_email(subject, body)

async def process_email(subject, body):
    try:
        # Check if the email contains the word "hit"
        if "hit" in body.lower():
            # Send the whole body to the Telegram channel if "hit" is found
            if body.strip():  # Ensure the body is not empty before sending
                bot.send_message(CHAT_ID, body)
            else:
                print("Email body is empty, skipping...")

            return  # Skip further processing if "hit" is found

        # Check if the email contains the word "reversal"
        if "reversal" in body.lower():
            # Send the entire body to the Telegram channel
            if body.strip():  # Ensure the body is not empty before sending
                bot.send_message(CHAT_ID, body)
                # Call place_trade with reversal action
                await place_trade("reversal", None, None, None)
            else:
                print("Email body is empty, skipping...")

            return  # Skip further processing if "reversal" is found

        # Process the email if it contains "#ETHUSD"
        if "#ETHUSD" in body:
            lines = body.strip().split("\n")
            pair = lines[0].split(": ")[1].strip()
            trade_type = lines[1].split(": ")[1].strip().lower()  # buy or sell
            entry_str = lines[2].split(": ")[1].strip()
            stop_loss = float(lines[3].split(": ")[1].strip())  # Increase stop loss by 4
            take_profit = float(lines[4].split(": ")[1].strip())  # Increase take profit by 4
            current_price = float(lines[5].split(": ")[1].strip())  # Current price
            risk_percent = float(lines[6].split(": ")[1].strip().replace("%", ""))  # Extract risk percentage

            # Check if the entry is "now" or a numeric value
            if entry_str.lower() == "now":
                entry = "now"  # Use the current market price later in the trade placement logic
            else:
                entry = float(entry_str)  # Convert the entry to a float if it's a number

            # Log the signal
            message = f"{body.strip()}"

            # Ensure the message is not empty before sending
            if message.strip():  # Check if there's any non-whitespace content
                bot.send_message(CHAT_ID, message)
            else:
                print("Message content is empty, skipping...")

            # Place trade on MetaApi (pass entry as None for now, will use market price)
            await place_trade(trade_type, stop_loss, take_profit, entry, risk_percent)

        else:
            print("Email does not contain #ETHUSD, skipping...")

    except Exception as e:
        print(f"Error processing message: {e}")

async def place_trade(trade_type, stop_loss, take_profit, entry=None, risk_percent=None):
    try:
        # Initialize MetaApi object with your token
        metaapi = MetaApi(METAAPI_TOKEN)

        # Connect to your MetaTrader account
        account = await metaapi.metatrader_account_api.get_account(ACCOUNT_ID)
        if not account:
            raise Exception(f"Failed to find account with ID {ACCOUNT_ID}")

        # Ensure the account is connected and deployed
        if account.state != 'DEPLOYED':
            raise Exception(f"Account is not deployed. Current state: {account.state}")
        await account.wait_connected()

        # Get the connection to the MetaTrader server and connect if necessary
        connection = account.get_rpc_connection()
        await connection.connect()  # Ensure the connection is initialized

        # Wait for the connection to be ready and synchronized
        print("Waiting for connection to be synchronized...")
        await connection.wait_synchronized()

        if trade_type == "reversal":
            # Close all positions for ETHUSD
            await connection.close_positions_by_symbol(symbol='ETHUSD')
            print("Closed all positions for ETHUSD due to reversal signal.")
            return

        # Get account information, including balance
        account_info = await connection.get_account_information()
        balance = account_info['balance']

        # Use the risk percentage from the signal if provided, otherwise use default
        risk_percent = risk_percent if risk_percent is not None else 0.01  # Default to 1% if not provided
        risk_amount = balance * (risk_percent / 100)

        # Get the current market price for ETHUSD
        symbol = 'ETHUSD'
        price_data = await connection.get_symbol_price(symbol)
        
        # If entry is "now", use the current market price
        if entry == "now":
            if trade_type == 'buy':
                entry_price = price_data['ask']
            else:
                entry_price = price_data['bid']
        else:
            entry_price = entry  # Use the provided entry price if it's a float

        # Calculate stop loss distance based on trade type
        if trade_type == 'buy':
            stop_loss_distance = entry_price - stop_loss
        else:
            stop_loss_distance = stop_loss - entry_price

        if stop_loss_distance <= 0:
            raise Exception("Invalid stop loss distance. Please check the stop loss value.")

        # Calculate position size (volume)
        value_per_pip_per_lot = 1  # For ETHUSD, typically $1 per pip for 1 lot
        position_size = risk_amount / (stop_loss_distance * value_per_pip_per_lot)

        # Ensure volume meets minimum requirements
        min_volume = 0.01  # Example minimum volume, this varies by broker and symbol
        if position_size < min_volume:
            position_size = min_volume  # Adjust to the minimum allowed volume

        # Optionally, round volume to nearest valid step (e.g., 0.01 precision)
        position_size = round(position_size, 2)

        # Place the trade without options (comment and clientId)
        if trade_type == 'buy':
            result = await connection.create_market_buy_order(
                symbol=symbol, volume=position_size, stop_loss=stop_loss, take_profit=take_profit
            )
        else:
            result = await connection.create_market_sell_order(
                symbol=symbol, volume=position_size, stop_loss=stop_loss, take_profit=take_profit
            )

        # Check trade result
        print(f"Trade result: {result}")

    except Exception as e:
        # Print full error details for further debugging
        print(f"Error placing trade: {e}")
        if hasattr(e, 'details'):
            print(f"Error details: {e.details}")  # This will provide more information on the invalid fields

# Main email checking loop
async def main():
    global api
    api = MetaApi(token=METAAPI_TOKEN)

    while True:
        try:
            await check_email()
            print("Checked emails, waiting for next interval...")
        except Exception as e:
            print(f"Error checking emails: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)

# Start the Telegram bot polling in a separate thread
if __name__ == "__main__":
    import threading
    telegram_thread = threading.Thread(target=bot.polling, args=(), daemon=True)
    telegram_thread.start()

    # Run the async email checker loop
    asyncio.run(main()) 
