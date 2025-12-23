# Gmail Bot Pro - Automated Login System

A Python automation tool with a modern GUI interface, offering powerful and feature-rich capabilities for Gmail account management. This bot enables automated account creation verification for multiple Gmail accounts, featuring proxy rotation, CAPTCHA solving, multi-threading, and comprehensive logging support.

## Features

- **Automated Gmail Login**: Batch process multiple Gmail accounts with automated login verification
- **Modern GUI Interface**: User-friendly Tkinter-based graphical interface with real-time statistics
- **Multi-Threading Support**: Process multiple accounts simultaneously (configurable thread count, max 20)
- **Proxy Support**: Full proxy integration with authentication support (username:password:hostname:port format)
- **Proxy Rotation**: Automatic proxy rotation and IP verification
- **CAPTCHA Solving**: Integrated 2Captcha API support for automated CAPTCHA resolution
- **Stealth Mode**: Uses undetected-chromedriver to bypass bot detection
- **Headless Mode**: Run without browser window for server deployments
- **Comprehensive Logging**: Detailed logs with timestamps, success/failure tracking, and file-based logging
- **Real-time Statistics**: Live updates on total accounts, successful logins, and failed attempts
- **Account Management**: Automatic removal of successful accounts from input file
- **Error Handling**: Robust error handling with detailed error messages
- **IP Verification**: Built-in proxy IP checking and validation
- **Configurable Delays**: Customizable delay between login attempts to avoid rate limiting
- **Session Management**: Proper browser session cleanup and resource management

## Requirements

- Python 3.10+
- Google Chrome browser installed
- 2Captcha API key (optional, for CAPTCHA solving)

## Installation

- Clone or download the Repository

- Install Dependencies

```bash
pip install -r requirements.txt
```

- Configure the Application

1. Create a `config.txt` file (or edit the existing one):
```txt
CAPTCHA_API_KEY=your_2captcha_api_key_here
```

2. Prepare your account file (`accounts.txt`):
```txt
email1@gmail.com:password1
email2@gmail.com:password2
email3@gmail.com:password3
```

3. Prepare your proxy file (`proxies.txt`) - Optional:
```txt
username1:password1:proxy1.example.com:8080
username2:password2:proxy2.example.com:8080
```

## Usage

### GUI Mode (Recommended)

1. Run the application:
```bash
python main.py
```

2. Configure settings in the GUI:
   - **Mail File**: Select your accounts file (format: `email:password`)
   - **Proxy File**: Select your proxies file (optional, format: `username:password:hostname:port`)
   - **Number of Threads**: Set concurrent processing threads (1-20 recommended)
   - **Waiting Period**: Delay between logins in seconds (1-60)
   - **Headless Mode**: Enable/disable browser visibility
   - **2Captcha API Key**: Enter your API key for CAPTCHA solving

3. Click **🚀 Start** to begin processing

4. Monitor progress in the log panel and statistics footer

5. Click **⏹️ Stop** to halt processing at any time

### Programmatic Usage

```python
from gmail_bot import GmailBot

# Prepare accounts and proxies
accounts = [
    "email1@gmail.com:password1",
    "email2@gmail.com:password2"
]

proxies = [
    "username:password:proxy.example.com:8080"
]

# Create bot instance
bot = GmailBot(
    accounts=accounts,
    proxies=proxies,
    headless=True,
    delay=2,
    captcha_api_key="your_2captcha_api_key"
)

# Run the bot
bot.run()
```

## File Structure

```
gmail-bot-pro/
├── main.py                 # GUI application entry point
├── gmail_bot.py            # Core bot logic and automation
├── requirements.txt        # Python dependencies
├── config.txt             # Configuration file (API keys)
├── accounts.txt           # Input file for Gmail accounts
├── proxies.txt            # Input file for proxy servers
├── successful_logins.txt  # Output file for successful logins
├── failed_logins.txt      # Output file for failed logins
└── bot_log_*.txt         # Detailed log files (auto-generated)
```

## Configuration

### Account File Format

Each line should contain an email and password separated by a colon:
```
email@gmail.com:password123
```

### Proxy File Format

Each line should contain proxy credentials in the format:
```
username:password:hostname:port
```

Example:
```
user123:pass456:proxy.example.com:8080
```

### Configuration Options

- **Thread Count**: Recommended 5-10 for optimal performance. Maximum 20 threads.
- **Delay**: 2-5 seconds recommended to avoid rate limiting
- **Headless Mode**: Enable for server environments or when you don't need to see the browser
- **CAPTCHA API Key**: Required for automated CAPTCHA solving. Get your key from [2Captcha](https://2captcha.com/)

## Output Files

### successful_logins.txt
Contains all successfully logged-in accounts in `email:password` format.

### failed_logins.txt
Contains failed login attempts with error reasons:
```
email@gmail.com:password
Reason: Invalid credentials
------------------------------
```

### bot_log_YYYYMMDD_HHMMSS.txt
Detailed timestamped logs for each bot instance with comprehensive debugging information.

## Security & Privacy

- **Local Processing**: All operations run locally on your machine
- **No Data Transmission**: Account credentials are never sent to external servers (except 2Captcha for CAPTCHA solving)
- **Proxy Support**: Use proxies to protect your IP address during operations

## Important Notes

1. **Rate Limiting**: Google may temporarily block accounts if too many attempts are made to create accounts. Use appropriate delays and proxy rotation.

2. **Proxy Quality**: 
   - Use high-quality, reliable proxies for best results
   - Test proxies before use with the built-in proxy tester
   - Residential proxies are recommended over datacenter proxies

## Technical Details

### Architecture

- **GUI Layer**: Tkinter-based interface with modern dark theme
- **Bot Engine**: Selenium WebDriver with undetected-chromedriver for stealth automation
- **Threading**: Multi-threaded architecture for concurrent account processing
- **Logging**: Multi-level logging system with file and callback support

### Browser Automation

- Uses `undetected-chromedriver` to bypass bot detection
- Implements CDP (Chrome DevTools Protocol) commands to hide automation signatures
- Custom user agent and browser fingerprinting mitigation
- Automatic ChromeDriver version management

### CAPTCHA Solving

- Integrated 2Captcha API for automated CAPTCHA resolution
- Automatic CAPTCHA detection and solving
- Fallback mechanisms for CAPTCHA failures

## Troubleshooting

### Common Issues

**Issue**: ChromeDriver version mismatch
- **Solution**: The application automatically manages ChromeDriver versions. Ensure Chrome browser is up to date.

**Issue**: Proxy connection failed
- **Solution**: Verify proxy format and credentials. Use the built-in proxy tester before running the bot.

**Issue**: CAPTCHA not solving
- **Solution**: Verify your 2Captcha API key and account balance. Check the log files for detailed error messages.

**Issue**: Accounts getting blocked
- **Solution**: Increase delay between logins, use more proxies, and reduce thread count.

**Issue**: GUI not responding
- **Solution**: Ensure you're running the application with proper permissions and that all dependencies are installed.

## Code Examples

### Basic Usage Example

```python
from gmail_bot import GmailBot

# Simple bot without proxies
bot = GmailBot(
    accounts=["user@gmail.com:password"],
    headless=False,
    delay=3
)
bot.run()
```

### Advanced Usage with Custom Logging

```python
from gmail_bot import GmailBot

def custom_log_callback(message):
    print(f"[CUSTOM LOG] {message}")

bot = GmailBot(
    accounts=["user1@gmail.com:pass1", "user2@gmail.com:pass2"],
    proxies=["user:pass:proxy.com:8080"],
    headless=True,
    delay=2,
    log_callback=custom_log_callback,
    captcha_api_key="your_key"
)
bot.run()
```

### Multi-Threading Example

```python
import threading
from gmail_bot import GmailBot

accounts = [f"user{i}@gmail.com:pass{i}" for i in range(100)]
proxies = ["user:pass:proxy.com:8080"]

# Split accounts for multiple threads
threads = []
accounts_per_thread = len(accounts) // 5

for i in range(5):
    start = i * accounts_per_thread
    end = start + accounts_per_thread
    thread_accounts = accounts[start:end]
    
    bot = GmailBot(accounts=thread_accounts, proxies=proxies)
    thread = threading.Thread(target=bot.run)
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


## Disclaimer

This tool is for educational and legitimate account management purposes only. Users are responsible for ensuring compliance with Google's Terms of Service and applicable laws. The developers are not responsible for any misuse of this software.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.



