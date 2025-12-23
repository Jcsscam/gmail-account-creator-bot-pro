from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import requests
import re
import os
import undetected_chromedriver as uc
from twocaptcha import TwoCaptcha

class GmailBot:
    def __init__(self, accounts, proxies=None, headless=True, delay=2, log_callback=None, captcha_api_key=None, thread_id=None):
        self.accounts = accounts
        self.proxies = proxies or []
        self.headless = headless
        self.delay = delay
        self.log_callback = log_callback
        self.driver = None
        self.is_running = True  # For stop control
        self.current_proxy_index = 0
        self.captcha_api_key = captcha_api_key
        self.solver = None
        self.original_accounts_file = None  # Original file path
        self.thread_id = thread_id  # Thread ID
        
        # File for detailed log
        import datetime
        log_filename = f"bot_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.log_file = open(log_filename, 'w', encoding='utf-8')
        
        # Start the captcha solver
        if self.captcha_api_key:
            try:
                self.solver = TwoCaptcha(self.captcha_api_key)
                self.log("2Captcha solver has been started")
            except Exception as e:
                self.log(f"2Captcha solver could not be started: {str(e)}")
        
    def log(self, message, level="INFO"):
        """Detailed logging mechanism"""
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"
        
        # write File
        if self.log_file:
            self.log_file.write(log_message + '\n')
            self.log_file.flush()
        
        # send Callback
        if self.log_callback:
            self.log_callback(log_message)
        else:
            print(log_message)
    
    def log_error(self, message):
        """error log"""
        self.log(message, level="ERROR")
            
    def setup_driver(self, proxy=None):
        """Chrome driver setup with proxy"""
        chrome_options = Options()
        
        # Basic settings
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Block pop-ups and notifications
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        
        # Disable Chrome profile management
        chrome_options.add_argument("--disable-profile-picker")
        chrome_options.add_argument("--disable-sync")
        
        # Block Chrome sign-in request
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Headless mode - special config for undetected-chromedriver
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        # Proxy settings
        proxy_data = None
        if proxy:
            try:
                proxy_parts = proxy.split(':')
                if len(proxy_parts) == 4:
                    username, password, hostname, port = proxy_parts
                    
                    # Save proxy information
                    proxy_data = {
                        'hostname': hostname,
                        'port': int(port),
                        'username': username,
                        'password': password
                    }
                    
                    self.log(f"✓ Proxy info: {username}@{hostname}:{port}")
                else:
                    self.log(f"✗ Invalid proxy format: {proxy}")
            except Exception as e:
                self.log(f"✗ Proxy setup error: {str(e)}")
                import traceback
                self.log(f"Details: {traceback.format_exc()}")
        
        try:
            # Custom settings if proxy exists
            if proxy_data:
                self.log(f"Starting with proxy: {proxy_data['hostname']}:{proxy_data['port']}")
                
                # Test proxy
                try:
                    proxy_dict = {
                        'http': f"http://{proxy_data['username']}:{proxy_data['password']}@{proxy_data['hostname']}:{proxy_data['port']}",
                        'https': f"http://{proxy_data['username']}:{proxy_data['password']}@{proxy_data['hostname']}:{proxy_data['port']}"
                    }
                    response = requests.get('https://api.ipify.org?format=json', proxies=proxy_dict, timeout=10)
                    proxy_ip = response.json().get('ip')
                    self.log(f"✓ Proxy tested, IP: {proxy_ip}")
                except Exception as e:
                    self.log(f"✗ Proxy test error: {str(e)}")
                
                # Create proxy extension
                proxy_auth_extension = self.create_proxy_auth_extension(
                    proxy_data['username'], 
                    proxy_data['password'], 
                    proxy_data['hostname'], 
                    proxy_data['port']
                )
                chrome_options.add_extension(proxy_auth_extension)
            
            # Stealth mode with undetected-chromedriver
            self.log("Starting ChromeDriver in stealth mode...")
            
            # Close old drivers
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            try:
                self.driver = uc.Chrome(
                    options=chrome_options,
                    use_subprocess=True,
                    version_main=None,
                    driver_executable_path=None,
                    headless=self.headless
                )
            except Exception as e:
                # Retry if file lock error
                if "WinError 32" in str(e) or "being used by another process" in str(e):
                    self.log("ChromeDriver file is locked, waiting 1 second...")
                    time.sleep(1)
                    self.driver = uc.Chrome(
                        options=chrome_options,
                        use_subprocess=True,
                        version_main=None,
                        driver_executable_path=None,
                        headless=self.headless
                    )
                else:
                    raise e
            
            # Automation detection bypass
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })
            
            # Remove Chrome infobar
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    window.chrome = {
                        runtime: {}
                    };
                '''
            })
            
            # Permissions bypass
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                '''
            })
            
            self.driver.implicitly_wait(2)
            self.log("✓ ChromeDriver started in stealth mode")
            return True
                
        except Exception as e:
            self.log(f"Driver setup error: {str(e)}")
            import traceback
            self.log(f"Details: {traceback.format_exc()}")
            
            # Alternative method: Standard selenium
            try:
                self.log("Trying alternative method...")
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.implicitly_wait(2)
                self.log("Alternative method successful")
                return True
            except Exception as e2:
                self.log(f"Alternative method also failed: {str(e2)}")
                return False
    
    def find_chrome_binary(self):
        """Find Chrome installation directory"""
        import os
        import platform
        
        if platform.system() == "Windows":
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            ]
        elif platform.system() == "Darwin":  # macOS
            possible_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]
        else:  # Linux
            possible_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
            ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None

    def create_proxy_auth_extension(self, username, password, hostname, port): 
        """Create Chrome extension for proxy authentication"""
        import zipfile
        
        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy Auth",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            },
            "minimum_chrome_version":"22.0.0"
        }
        """
        
        background_js = f"""
        var config = {{
            mode: "fixed_servers",
            rules: {{
                singleProxy: {{
                    scheme: "http",
                    host: "{hostname}",
                    port: parseInt({port})
                }},
                bypassList: ["localhost", "127.0.0.1"]
            }}
        }};

        chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{
            console.log("Proxy configured:", config);
        }});

        function callbackFn(details) {{
            console.log("Proxy auth required for:", details.url);
            return {{
                authCredentials: {{
                    username: "{username}",
                    password: "{password}"
                }}
            }};
        }}

        chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {{urls: ["<all_urls>"]}},
            ['blocking']
        );

        chrome.proxy.onProxyError.addListener(function(details) {{
            console.error("Proxy error:", details);
        }});
        
        console.log("Proxy extension loaded for {hostname}:{port}");
        
        chrome.proxy.settings.get({{}}, function(config) {{
            console.log("Current proxy config:", config);
        }});
        """
        
        # Create temporary file - unique name
        import uuid
        pluginfile = f'proxy_auth_plugin_{uuid.uuid4().hex[:8]}.zip'
        
        with zipfile.ZipFile(pluginfile, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)
            
        return pluginfile
      
    def get_next_proxy(self):
        """Get the next proxy"""
        if not self.proxies:
            return None
        
        # If thread ID exists, select proxy specific to that thread
        if self.thread_id is not None:
            proxy = self.proxies[self.current_proxy_index % len(self.proxies)]
            self.current_proxy_index += 1
        else:
            # Normal mode: Round-robin
            proxy = self.proxies[self.current_proxy_index % len(self.proxies)]
            self.current_proxy_index += 1
        
        return proxy

    def check_proxy_ip(self): 
        """Check and display proxy IP"""
        try:
            if self.driver:
                # Check current URL
                current_url = self.driver.current_url
                self.log(f"Page for IP check: {current_url}")
                
                # Try multiple IP check services
                ip_services = [
                    "https://api.ipify.org?format=json",
                    "https://httpbin.org/ip",
                    "https://ipinfo.io/json"
                ]
                
                for service_url in ip_services:
                    try:
                        self.log(f"Trying IP check: {service_url}")
                        self.driver.get(service_url)
                        time.sleep(0.5)  # Minimum delay
                        
                        # Get IP response
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        ip_text = body.text
                        
                        self.log(f"Service response: {ip_text[:100]}")  # First 100 chars
                        
                        # Parse JSON
                        import json
                        ip_data = json.loads(ip_text)
                        ip = ip_data.get('ip') or ip_data.get('origin')
                        
                        if ip:
                            self.log(f"✓ IP Address: {ip}")
                            return ip
                    except Exception as e:
                        self.log(f"IP check service error: {str(e)}")
                        continue
                
                self.log("✗ IP check failed")
                return None
        except Exception as e:
            self.log(f"IP check error: {str(e)}")
            return None
     
    def is_valid_captcha_solution(self, text):
        """Advanced captcha solution quality check"""
        if not text:
            return False
        
        # Cleaning and basic checks
        text = text.strip().lower()
        
        # Length check - Google captcha is usually 5-8 characters
        if len(text) < 4 or len(text) > 12:
            self.log(f"Length check failed: {len(text)} characters", level="CAPTCHA")
            return False
        
        # Must contain only letters and numbers (excluding space)
        clean_text = text.replace(' ', '')
        if not clean_text.isalnum():
            self.log(f"Character check failed: {text}", level="CAPTCHA")
            return False
        
        # Digit ratio check - too many numbers is suspicious
        digit_count = sum(1 for c in clean_text if c.isdigit())
        if digit_count > len(clean_text) * 0.6:  # More than 60% digits
            self.log(f"Too many digits: {text} ({digit_count}/{len(clean_text)})", level="CAPTCHA")
            return False
        
        # Too few letters check
        letter_count = sum(1 for c in clean_text if c.isalpha())
        if letter_count < 3:  # At least 3 letters required
            self.log(f"Too few letters: {text} ({letter_count} letters)", level="CAPTCHA")
            return False
        
        # Repeating characters check
        for i in range(len(clean_text) - 2):
            if clean_text[i] == clean_text[i+1] == clean_text[i+2]:
                self.log(f"Repeated character sequence: {text}", level="CAPTCHA")
                return False
        
        # Common suspicious captcha patterns
        suspicious_patterns = ['aaa', 'bbb', 'ccc', 'ddd', 'eee', 'fff', 'ggg', 'hhh', 'iii', 'jjj', 'kkk', 'lll',
                            'mmm', 'nnn', 'ooo', 'ppp', 'qqq', 'rrr', 'sss', 'ttt', 'uuu', 'vvv', 'www', 'xxx',
                            'yyy', 'zzz']
        if any(pattern in clean_text for pattern in suspicious_patterns):
            self.log(f"Suspicious pattern: {text}", level="CAPTCHA")
            return False
        
        # Very short word check
        words = text.split()
        if any(len(word) < 2 for word in words if word.isalpha()):
            self.log(f"Very short word: {text}", level="CAPTCHA")
            return False
        
        self.log(f"✓ Solution quality approved: {text}", level="CAPTCHA")
        return True

    def solve_captcha_with_multiple_apis(self, captcha_data): 
        """Captcha solving with multiple attempts"""
        solutions = []
        
        # Try 3 times
        for attempt in range(1, 4):  # 1, 2, 3
            if self.solver:
                try:
                    self.log(f"2Captcha attempt {attempt}/3", level="CAPTCHA")
                    result = self.solver.normal(captcha_data)
                    if result and 'code' in result:
                        solutions.append(('2captcha', result['code']))
                        self.log(f"2Captcha solution (attempt {attempt}): {result['code']}", level="CAPTCHA")
                        
                        # Check if solution is valid
                        if self.is_valid_captcha_solution(result['code']):
                            self.log(f"✓ Valid solution found (attempt {attempt})", level="SUCCESS")
                            return solutions
                        else:
                            self.log(f"✗ Invalid solution (attempt {attempt}), will retry", level="CAPTCHA")
                            solutions = []  # Clear invalid solution
                            
                except Exception as e:
                    self.log(f"2Captcha error (attempt {attempt}): {str(e)}", level="CAPTCHA")
            
            # Short wait between attempts
            if attempt < 3:
                time.sleep(1)
        
        self.log_error("✗ No valid solution found after 3 attempts!")
        return solutions

    def find_best_captcha_solution(self, solutions):
        """Find the best captcha solution"""
        if not solutions:
            return None
        
        # Analyze solutions
        scored_solutions = []
        for api, solution in solutions:
            score = self.score_captcha_solution(solution)
            scored_solutions.append((api, solution, score))
            self.log(f"Solution score: {solution} -> {score}", level="CAPTCHA")
        
        # Select the highest scoring solution
        best_solution = max(scored_solutions, key=lambda x: x[2])
        self.log(
            f"Best solution selected: {best_solution[1]} (API: {best_solution[0]}, Score: {best_solution[2]})",
            level="SUCCESS"
        )
        return best_solution[1]

    def score_captcha_solution(self, text): 
        """Score captcha solution"""
        if not text:
            return 0
        
        score = 0
        text = text.strip().lower()
        
        # Length score (5-8 characters ideal)
        if 5 <= len(text) <= 8:
            score += 10
        elif 4 <= len(text) <= 9:
            score += 5
        
        # Letter/digit ratio score
        clean_text = text.replace(' ', '')
        letter_count = sum(1 for c in clean_text if c.isalpha())
        digit_count = sum(1 for c in clean_text if c.isdigit())
        
        if letter_count >= 3:  # At least 3 letters
            score += 5
        if digit_count <= len(clean_text) * 0.4:  # Less than 40% digits
            score += 5
        
        # Repeated character penalty
        for i in range(len(clean_text) - 2):
            if clean_text[i] == clean_text[i+1] == clean_text[i+2]:
                score -= 10
        
        # Suspicious pattern penalty
        suspicious_patterns = [
            'aaa', 'bbb', 'ccc', 'ddd', 'eee', 'fff', 'ggg', 'hhh', 'iii', 'jjj',
            'kkk', 'lll', 'mmm', 'nnn', 'ooo', 'ppp', 'qqq', 'rrr', 'sss', 'ttt',
            'uuu', 'vvv', 'www', 'xxx', 'yyy', 'zzz'
        ]
        if any(pattern in clean_text for pattern in suspicious_patterns):
            score -= 15
        
        # Common captcha words bonus
        common_captcha_words = ['captcha', 'verify', 'confirm', 'enter', 'type', 'text', 'code', 'word']
        if any(word in text for word in common_captcha_words):
            score += 3
        
        return score

    def solve_captcha(self):
        """Captcha solving system with multiple attempts"""
        if not self.solver:
            self.log_error("Captcha solver not available")
            return False
        
        # FIRST: Check if we are on the password page
        if self.is_password_page():
            self.log("✓ On password page, captcha solving will not be performed", level="SUCCESS")
            return True  # Considered successful because password page is reached
        
        # Check solved flag - prevent unnecessary captcha checks
        if hasattr(self, 'captcha_solved') and self.captcha_solved:
            self.log("✓ Captcha already solved, no further solving needed", level="SUCCESS")
            return True
            
        # Try solving captcha 3 times
        for attempt in range(1, 4):  # 1, 2, 3
            try:
                self.log(f"Captcha solving attempt {attempt}/3", level="CAPTCHA")
                
                # Get a fresh captcha image each attempt
                captcha_data = self.get_captcha_image()
                if not captcha_data:
                    self.log_error(f"Failed to retrieve captcha image (attempt {attempt})")
                    continue
                
                # Solve using multiple APIs
                solutions = self.solve_captcha_with_multiple_apis(captcha_data)
                
                if not solutions:
                    self.log_error(f"No solution received from any API (attempt {attempt})")
                    continue
                
                # Select the best solution
                captcha_text = self.find_best_captcha_solution(solutions)
                
                if not captcha_text:
                    self.log_error(f"No valid solution found (attempt {attempt})")
                    continue
                
                self.log(f"✓ Solution found (attempt {attempt}): {captcha_text}", level="SUCCESS")
                
                # Enter the solution and test
                if self.enter_captcha_solution(captcha_text):
                    self.log(f"✓ Captcha successfully solved (attempt {attempt})", level="SUCCESS")
                    # Set solved flag
                    self.captcha_solved = True
                    return True
                else:
                    self.log_error(f"✗ Captcha solution failed (attempt {attempt})")
                    
            except Exception as e:
                self.log_error(f"Captcha solve error (attempt {attempt}): {str(e)}")
            
            # Wait before next attempt
            if attempt < 3:
                self.log("Waiting for new captcha...", level="CAPTCHA")
                time.sleep(2)
        
        self.log_error("✗ Failed to solve captcha after 3 attempts!")
        return False

    def get_captcha_image(self):
        """Retrieve captcha image"""
        try:
            # FIRST: Check if we are on the password page
            if self.is_password_page():
                self.log("✓ On password page, captcha image will not be searched", level="SUCCESS")
                return None
            
            # Find captcha image
            captcha_image = None
            
            # Look for captcha under "Forgot your email address?" text
            try:
                forgot_email_element = self.driver.find_element(
                    By.XPATH, 
                    "//a[contains(text(), 'E-posta adresinizi mi unuttunuz') or contains(text(), 'e-posta adresinizi mi unuttunuz')]"
                )
                captcha_image = forgot_email_element.find_element(
                    By.XPATH, "./following-sibling::*//img | ./following::img[1]"
                )
                self.log("✓ Captcha image found under 'Forgot your email address?'", level="CAPTCHA")
            except:
                pass
            
            # If not found, scan all images
            if not captcha_image:
                all_images = self.driver.find_elements(By.TAG_NAME, "img")
                self.log(f"{len(all_images)} images found on page", level="CAPTCHA")
                
                for i, img in enumerate(all_images):
                    try:
                        if not img.is_displayed():
                            continue
                        
                        src = img.get_attribute('src') or ''
                        alt = img.get_attribute('alt') or ''
                        size = img.size
                        width = size['width']
                        height = size['height']
                        
                        # Check captcha characteristics
                        is_captcha = False
                        
                        if 'captcha' in src.lower() or 'captcha' in alt.lower():
                            is_captcha = True
                        elif (180 < width < 220 and 60 < height < 80) or (50 < width < 600 and 20 < height < 200):
                            is_captcha = True
                        elif 'data:image' in src.lower() or 'base64' in src.lower():
                            is_captcha = True
                        elif 'google.com' in src.lower() and ('captcha' in src.lower() or 'challenge' in src.lower()):
                            is_captcha = True
                        
                        if is_captcha:
                            captcha_image = img
                            self.log(f"✓ Captcha image found! Size: {width}x{height}", level="CAPTCHA")
                            break
                            
                    except Exception as e:
                        continue
            
            # If captcha image not found, use page screenshot
            if not captcha_image:
                self.log("Captcha image not found, using page screenshot...", level="CAPTCHA")
                import base64
                page_screenshot = self.driver.get_screenshot_as_base64()
                return page_screenshot
            else:
                # Retrieve captcha image
                import base64
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", 
                        captcha_image
                    )
                    time.sleep(0.3)
                    
                    captcha_data = captcha_image.screenshot_as_base64
                    self.log(f"Captcha image retrieved, size: {len(captcha_data)} bytes", level="CAPTCHA")
                    
                    # Quick preprocessing
                    try:
                        import io
                        from PIL import Image, ImageEnhance
                        
                        image_data = base64.b64decode(captcha_data)
                        image = Image.open(io.BytesIO(image_data))
                        
                        enhancer = ImageEnhance.Contrast(image)
                        image = enhancer.enhance(1.5)
                        
                        buffered = io.BytesIO()
                        image.save(buffered, format="PNG")
                        captcha_data = base64.b64encode(buffered.getvalue()).decode()
                        
                        self.log("✓ Captcha image preprocessed", level="CAPTCHA")
                        
                    except Exception as preprocess_e:
                        self.log(f"Preprocessing error (continuing): {str(preprocess_e)}", level="CAPTCHA")
                    
                    return captcha_data
                        
                except Exception as e:
                    self.log_error(f"Captcha image retrieval error: {str(e)}")
                    # Fallback: page screenshot
                    self.log("Fallback: Using page screenshot...", level="CAPTCHA")
                    page_screenshot = self.driver.get_screenshot_as_base64()
                    return page_screenshot
                    
        except Exception as e:
            self.log_error(f"General error retrieving captcha image: {str(e)}")
            return None

    def enter_captcha_solution(self, captcha_text):
        """Enter and test captcha solution"""
        try:
            # Find captcha input field
            captcha_selectors = [
                "input[type='text']",
                "input[placeholder*='duyduğunuz']",
                "input[placeholder*='gördüğünüz']",
                "input[aria-label*='duyduğunuz']",
                "input[aria-label*='gördüğünüz']",
                "input[name='captcha']",
                "input[id*='captcha']",
                "input[placeholder*='captcha']"
            ]
            
            captcha_input = None
            for selector in captcha_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            captcha_input = elem
                            break
                    if captcha_input:
                        break
                except Exception:
                    continue
            
            if not captcha_input:
                self.log_error("Captcha input field not found")
                return False
            
            # Enter the solution
            try:
                self.driver.execute_script("arguments[0].value = arguments[1];", captcha_input, captcha_text)
                time.sleep(0.2)
                
                entered_value = self.driver.execute_script("return arguments[0].value;", captcha_input)
                if entered_value == captcha_text:
                    self.log(f"✓ Solution entered correctly: {entered_value}", level="CAPTCHA")
                else:
                    self.log_error(f"✗ Solution entered incorrectly! Expected: {captcha_text}, Entered: {entered_value}")
                    return False
                    
            except Exception as e:
                self.log_error(f"Error entering solution: {str(e)}")
                return False
            
            # Click the next button - DETAILED AND RELIABLE
            try:
                # Debug: URL before click
                url_before_click = self.driver.current_url
                self.log(f"🔍 DEBUG: URL before clicking next: {url_before_click}", level="CAPTCHA")
                
                # Find and click next button
                next_button = self.driver.find_element(By.ID, "identifierNext")
                self.log("🔍 DEBUG: Next button found, clicking...", level="CAPTCHA")
                
                # Click using JavaScript (more reliable)
                self.driver.execute_script("arguments[0].click();", next_button)
                self.log("🔍 DEBUG: Next button clicked via JavaScript", level="CAPTCHA")
                
                # Wait for page load
                time.sleep(3)
                self.log("🔍 DEBUG: Waited 3 seconds", level="CAPTCHA")
                
                # Debug: URL after click
                url_after_click = self.driver.current_url
                self.log(f"🔍 DEBUG: URL after clicking next: {url_after_click}", level="CAPTCHA")
                
                # Check if URL changed
                if url_before_click != url_after_click:
                    self.log("✅ DEBUG: URL changed! Captcha solved", level="SUCCESS")
                    return True
                
                # Check success based on page
                current_url = self.driver.current_url.lower()
                page_source = self.driver.page_source.lower()
                
                self.log(f"🔍 DEBUG: Current URL: {current_url}", level="CAPTCHA")
                self.log(f"🔍 DEBUG: Page source length: {len(page_source)}", level="CAPTCHA")
                
                # Still on captcha page
                if 'captcha' in current_url or ('duyduğunuz' in page_source and 'gördüğünüz' in page_source):
                    self.log_error("✗ Captcha solution failed, still on captcha page")
                    return False
                
                # Reached password page
                if 'password' in current_url or 'signin/v2/challenge/pwd' in current_url:
                    self.log("✓ Captcha solved, navigated to password page", level="SUCCESS")
                    return True
                
                # On identifier page without captcha
                if 'identifier' in current_url and 'captcha' not in current_url:
                    self.log("✓ Captcha solved, on identifier page", level="SUCCESS")
                    return True
                
                # If page changed, consider captcha solved
                self.log("✓ Captcha solved, page changed", level="SUCCESS")
                return True
                
            except Exception as e:
                self.log_error(f"Next button not found: {str(e)}")
                return False
                
        except Exception as e:
            self.log_error(f"Error entering captcha solution: {str(e)}")
            return False
     
    def solve_recaptcha(self):
        """Solve reCAPTCHA"""
        if not self.solver:
            return False
            
        try:
            self.log("Solving reCAPTCHA...")
            
            # Find reCAPTCHA sitekey and page URL
            sitekey = None
            pageurl = self.driver.current_url
            
            # Try to find sitekey
            try:
                # Get sitekey from reCAPTCHA iframe
                iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
                if iframes:
                    for iframe in iframes:
                        src = iframe.get_attribute('src')
                        if 'sitekey' in src:
                            match = re.search(r'sitekey=([^&]+)', src)
                            if match:
                                sitekey = match.group(1)
                                break
            except:
                pass
            
            if not sitekey:
                # Alternative method: data-sitekey attribute
                try:
                    sitekey_elem = self.driver.find_element(By.CSS_SELECTOR, "[data-sitekey]")
                    sitekey = sitekey_elem.get_attribute('data-sitekey')
                except:
                    pass
            
            if sitekey:
                self.log(f"reCAPTCHA sitekey found: {sitekey[:20]}...")
                
                # Solve reCAPTCHA using 2Captcha
                result = self.solver.recaptcha(sitekey=sitekey, url=pageurl)
                
                if result and 'code' in result:
                    token = result['code']
                    self.log("reCAPTCHA token received")
                    
                    # Inject token into textarea
                    try:
                        self.driver.execute_script("""
                            document.getElementById('g-recaptcha-response').innerHTML='arguments[0]';
                        """, token)
                        
                        # Call callback
                        self.driver.execute_script("___grecaptcha_cfg.clients[0].callback(arguments[0]);", token)
                        self.log("reCAPTCHA solved")
                        return True
                    except Exception as e:
                        self.log(f"reCAPTCHA callback error: {str(e)}")
                        return False
                else:
                    self.log("Failed to get reCAPTCHA token")
                    return False
            else:
                self.log("reCAPTCHA sitekey not found")
                return False
                
        except Exception as e:
            self.log(f"Error solving reCAPTCHA: {str(e)}")
            return False
    
    def is_password_page(self):
        """Check if on password entry page - RELIABLE DETECTION"""
        try:
            current_url = self.driver.current_url.lower()
            
            # URL check
            if 'password' in current_url or 'signin/v2/challenge/pwd' in current_url:
                return True
            
            # Page source check
            page_source = self.driver.page_source.lower()
            
            # Turkish password page indicators
            turkish_indicators = [
                'hoş geldiniz',
                'şifrenizi girin',
                'şifreyi göster',
                'şifrenizi mi unuttunuz',
                'sonraki'
            ]
            
            # English password page indicators
            english_indicators = [
                'welcome',
                'enter your password',
                'show password',
                'forgot password',
                'next'
            ]
            
            # At least 3 Turkish indicators present?
            turkish_count = sum(1 for indicator in turkish_indicators if indicator in page_source)
            if turkish_count >= 3:
                self.log(f"✓ Turkish password page detected ({turkish_count}/5 indicators)", level="SUCCESS")
                return True
            
            # At least 3 English indicators present?
            english_count = sum(1 for indicator in english_indicators if indicator in page_source)
            if english_count >= 3:
                self.log(f"✓ English password page detected ({english_count}/5 indicators)", level="SUCCESS")
                return True
            
            # Check password input field
            try:
                password_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                visible_password_inputs = [inp for inp in password_inputs if inp.is_displayed()]
                if visible_password_inputs:
                    self.log("✓ Password input field detected", level="SUCCESS")
                    return True
            except:
                pass
            
            # Check "Next" button
            try:
                next_buttons = self.driver.find_elements(
                    By.XPATH, "//button[contains(text(), 'Sonraki') or contains(text(), 'Next')]"
                )
                if next_buttons:
                    self.log("✓ Next button detected", level="SUCCESS")
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            self.log_error(f"Password page check error: {str(e)}")
            return False

    def check_and_solve_captcha(self):
        """Check if captcha exists on page and solve it"""
        try:
            # FIRST: Check if on password page
            if self.is_password_page():
                self.log("✓ Detected on password page, captcha check skipped", level="SUCCESS")
                return False  # No captcha, success
            
            # Not on password page, perform captcha check
            self.log("Not on password page, checking for captcha...", level="CAPTCHA")
            
            # First, check captcha input field (most reliable)
            captcha_input_selectors = [
                "input[placeholder*='duyduğunuz']",
                "input[placeholder*='gördüğünüz']",
                "input[aria-label*='duyduğunuz']",
                "input[aria-label*='gördüğünüz']"
            ]
            
            captcha_input_found = False
            for selector in captcha_input_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            captcha_input_found = True
                            break
                    if captcha_input_found:
                        break
                except:
                    continue
            
            # If captcha input exists, solve it
            if captcha_input_found:
                self.log("Captcha input field found, solving...")
                return self.solve_captcha()
            
            # Check for captcha images/elements
            captcha_indicators = [
                "img[alt*='captcha']",
                "img[src*='captcha']",
                "div[class*='captcha']",
                "iframe[src*='bframe']",
                "iframe[src*='recaptcha']",
                "div[id*='recaptcha']"
            ]
            
            captcha_found = False
            captcha_type = None
            
            for indicator in captcha_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                    visible_elements = [elem for elem in elements if elem.is_displayed()]
                    if visible_elements:
                        self.log("Captcha detected")
                        captcha_found = True
                        
                        if 'recaptcha' in indicator.lower():
                            captcha_type = 'recaptcha'
                        else:
                            captcha_type = 'normal'
                        break
                except:
                    continue
            
            if captcha_found:
                if captcha_type == 'recaptcha':
                    return self.solve_recaptcha()
                else:
                    return self.solve_captcha()
                    
            return False
        except Exception as e:
            self.log(f"Captcha check error: {str(e)}")
            return False

    def login_to_gmail(self, email, password):
        """Sign in to Gmail"""
        try:
            # Reset the Captcha solved flag
            self.captcha_solved = False
            
            # Go to the Gmail login page
            self.driver.get("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2F&dsh=S1761938102%3A1761337695356685&ifkv=AfYwgwXR_3NPrD8alBlf7EgW8wdIvHNc9IwAQ1QahWh7mMsSjHxrU-B83ELP1lLjtgadvgNYESmdYw&rip=1&sacu=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin")
            
            # Find and fill in the email field - VERY FAST
            email_input = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.ID, "identifierId"))
            )
            email_input.clear()
            email_input.send_keys(email)
            
            # Click the Next button
            next_button = self.driver.find_element(By.ID, "identifierNext")
            next_button.click()
            
            # Perform a captcha check after the email has been sent
            self.log("Email sent, captcha verification in progress...", level="CAPTCHA")
            time.sleep(1)  # Please wait for the page to load
            
            # Captcha check - PASSWORD PAGE CHECK FIRST
            captcha_detected = False
            try:
                # Check the current URL
                current_url = self.driver.current_url.lower()
                self.log(f"URL: {current_url}", level="CAPTCHA")
                
                # FIRST: Check if we are on the password page
                if self.is_password_page():
                    self.log("✓ The password page has been accessed, captcha verification will not be performed", level="SUCCESS")
                    captcha_detected = False
                else:
                    # If we are not on the password page, perform a captcha check
                    self.log("We are not on the password page, a captcha check is being performed...", level="CAPTCHA")
                    
                    # Check if the text ‘What you hear or see’ is present in the page source code.
                    page_source = self.driver.page_source.lower()
                    if 'what you hear' in page_source and 'what you see' in page_source:
                        captcha_detected = True
                        self.log("✓ Captcha text detected in page source!", level="CAPTCHA")
                    
                    # Captcha input check - "what you hear or see" text
                    if not captcha_detected:
                        captcha_inputs = self.driver.find_elements(By.CSS_SELECTOR, 
                            "input[placeholder*='what you hear'], input[placeholder*='what you see'], "
                            "input[aria-label*='what you hear'], input[aria-label*='what you see'], "
                            "input[placeholder*='captcha'], input[name*='captcha'], input[id*='captcha']")
                        
                        if captcha_inputs:
                            for cap_input in captcha_inputs:
                                if cap_input.is_displayed():
                                    captcha_detected = True
                                    self.log("✓ Captcha INPUT detected!", level="CAPTCHA")
                                    break
                    
                    # Captcha image check
                    if not captcha_detected:
                        captcha_images = self.driver.find_elements(By.CSS_SELECTOR, 
                            "img[src*='captcha'], img[alt*='captcha'], div[class*='captcha']")
                        if captcha_images:
                            for img in captcha_images:
                                if img.is_displayed():
                                    captcha_detected = True
                                    self.log("✓ Captcha IMAGE detected!", level="CAPTCHA")
                                    break
                    
                    # URL check
                    if not captcha_detected:
                        if 'captcha' in current_url or 'challenge' in current_url:
                            captcha_detected = True
                            self.log("✓ Captcha detected in URL!", level="CAPTCHA")
                            
            except Exception as e:
                self.log_error(f"Captcha check error: {str(e)}")
            
            # Solve captcha if detected - ONLY ON EMAIL PAGE
            if captcha_detected and self.solver:
                self.log("Solving captcha...", level="CAPTCHA")
                try:
                    # Save URL before solving captcha
                    url_before_captcha = self.driver.current_url
                    self.log(f"URL before captcha solving: {url_before_captcha}", level="CAPTCHA")
                    
                    captcha_solved = self.solve_captcha()
                    if not captcha_solved:
                        self.log_error("Captcha could not be solved - closing browser")
                        self.add_failed_login(f"{email}:{password}", "Captcha could not be solved")
                        # Close browser and move to next account
                        try:
                            self.driver.quit()
                        except:
                            pass
                        return False
                    
                    # Wait for transition to password page after solving captcha
                    self.log("Captcha solved, waiting for transition to password page...", level="CAPTCHA")
                    time.sleep(3)  # Wait for page to load
                    
                    # Verify transition to password page - ROBUST AND DETAILED
                    password_page_reached = False
                    max_wait_attempts = 10  # 10 attempts
                    
                    for attempt in range(1, max_wait_attempts + 1):
                        current_url = self.driver.current_url.lower()
                        page_source = self.driver.page_source.lower()
                        
                        self.log(f"Password page check {attempt}/{max_wait_attempts}: {current_url}", level="CAPTCHA")
                        
                        # Check if navigated to password page
                        if 'password' in current_url or 'signin/v2/challenge/pwd' in current_url:
                            password_page_reached = True
                            self.log("✓ Successfully reached password page!", level="SUCCESS")
                            break
                        
                        # Check if password input field is present
                        try:
                            password_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                            visible_password_inputs = [inp for inp in password_inputs if inp.is_displayed()]
                            if visible_password_inputs:
                                password_page_reached = True
                                self.log("✓ Password input field found!", level="SUCCESS")
                                break
                        except:
                            pass
                        
                        # If captcha is still present, fail
                        if 'captcha' in current_url or ('what you hear' in page_source and 'what you see' in page_source):
                            self.log_error(f"Captcha still present (attempt {attempt})")
                            if attempt == max_wait_attempts:
                                self.log_error("Captcha could not be solved; still on captcha page")
                                self.add_failed_login(f"{email}:{password}", "Captcha could not be solved - still on captcha page")
                                try:
                                    self.driver.quit()
                                except:
                                    pass
                                return False
                        
                        # Wait and retry
                        if attempt < max_wait_attempts:
                            time.sleep(1)
                    
                    if not password_page_reached:
                        self.log_error("Failed to reach password page")
                        self.add_failed_login(f"{email}:{password}", "Failed to reach password page")
                        try:
                            self.driver.quit()
                        except:
                            pass
                        return False
                    
                    # Captcha solved — skip further captcha checks
                    captcha_detected = False
                    self.log("✓ Captcha solved; no further captcha checks will be performed", level="SUCCESS")
                    
                except Exception as e:
                    self.log_error(f"Error while solving captcha: {str(e)}")
                    self.add_failed_login(f"{email}:{password}", f"Captcha solving error: {str(e)}")
                    # Close browser and move to next account
                    try:
                        self.driver.quit()
                    except:
                        pass
                    return False
            elif captcha_detected and not self.solver:
                self.log_error("Captcha detected but no solver available!")
                self.add_failed_login(f"{email}:{password}", "Captcha detected but no solver available")
                # Close browser and move to next account
                try:
                    self.driver.quit()
                except:
                    pass
                return False
            
            # IMPORTANT: Re-verify that we are on the password page
            current_url_after_captcha = self.driver.current_url.lower()
            if 'password' in current_url_after_captcha or 'signin/v2/challenge/pwd' in current_url_after_captcha:
                self.log("✓ Confirmed we are on the password page; captcha check will be skipped", level="SUCCESS")
                captcha_detected = False
            
            # Locate password field - OPTIMIZED AND FAST
            self.log("Looking for password field...")
            password_input = None

            # Short wait - for page to load
            time.sleep(2)

            # Check current URL
            current_url = self.driver.current_url.lower()
            self.log(f"Current URL: {current_url}")

            # Verify we are on the password page - ROBUST DETECTION
            if not self.is_password_page():
                self.log_error("Not on the password page!")
                self.add_failed_login(f"{email}:{password}", "Not on password page")
                return False

            self.log("✓ Confirmed we are on the password page", level="SUCCESS")

            # Find password field - PRIORITY SELECTORS
            password_selectors = [
                "input[type='password']",  # Most common
                "input[name='password']",
                "input[id*='password']",
                "input[placeholder*='password']",
                "input[placeholder*='şifre']",
                "input[placeholder*='Şifre']",
                "input[aria-label*='password']",
                "input[aria-label*='şifre']",
                "input[aria-label*='Şifre']"
            ]

            for selector in password_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            password_input = elem
                            self.log(f"✓ Password field found: {selector}")
                            break
                    if password_input:
                        break
                except Exception as e:
                    continue

            # If password field was not found, raise error
            if not password_input:
                self.log_error("Password field not found!")
                
                # Debug info
                try:
                    all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    self.log(f"Found {len(all_inputs)} input elements on the page")
                    
                    for i, inp in enumerate(all_inputs[:5]):  # Inspect first 5 inputs
                        try:
                            input_type = inp.get_attribute('type')
                            input_name = inp.get_attribute('name')
                            input_id = inp.get_attribute('id')
                            is_displayed = inp.is_displayed()
                            self.log(f"Input {i+1}: type='{input_type}', name='{input_name}', id='{input_id}', displayed={is_displayed}")
                        except:
                            pass
                except:
                    pass
                
                self.add_failed_login(f"{email}:{password}", "Password field not found")
                return False
            
            # Log password field details
            try:
                self.log(f"✓ Password field found - visible: {password_input.is_displayed()}, enabled: {password_input.is_enabled()}")
            except:
                pass

            # Fill password field - OPTIMIZED AND FAST
            self.log("Filling password field...")
            password_entered = False

            # Password length info
            self.log(f"Password length to enter: {len(password)} characters")

            # Method 1: Direct Selenium (Fastest and most reliable)
            try:
                self.log("Method 1: Trying direct Selenium...")
                from selenium.webdriver.common.keys import Keys
                
                # Scroll password field into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", password_input)
                time.sleep(0.3)
                
                # Focus on password field
                password_input.click()
                time.sleep(0.3)
                
                # Clear field
                password_input.clear()
                time.sleep(0.2)
                
                # Enter password
                password_input.send_keys(password)
                time.sleep(0.3)
                
                # Verify entered password
                entered_password = password_input.get_attribute('value')
                self.log(f"Entered password length: {len(entered_password)}")
                
                if entered_password:
                    password_entered = True
                    self.log("✓ Method 1 successful: Password entered")
                    
                    # Submit with ENTER key
                    password_input.send_keys(Keys.RETURN)
                    self.log("✓ Submitted with ENTER key")
                else:
                    self.log("✗ Method 1 failed: Password not entered")
                    
            except Exception as e:
                self.log_error(f"Method 1 error: {str(e)}")

            # Method 2: Direct value assignment via JavaScript
            if not password_entered:
                try:
                    self.log("Method 2: Trying JavaScript value assignment...")
                    
                    # Set value using JavaScript
                    self.driver.execute_script("arguments[0].value = arguments[1];", password_input, password)
                    time.sleep(0.3)
                    
                    # Trigger input events
                    self.driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                    """, password_input)
                    time.sleep(0.3)
                    
                    # Verify entered password
                    entered_password = self.driver.execute_script("return arguments[0].value;", password_input)
                    
                    if entered_password:
                        password_entered = True
                        self.log("✓ Method 2 successful: Password entered")
                        
                        # Submit with ENTER key
                        password_input.send_keys(Keys.RETURN)
                        self.log("✓ Submitted with ENTER key")
                    else:
                        self.log("✗ Method 2 failed: Password not entered")
                        
                except Exception as e:
                    self.log_error(f"Method 2 error: {str(e)}")
            
            # Method 3: Using ActionChains
            if not password_entered:
                try:
                    self.log("Method 3: Trying ActionChains...")
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    # Click and enter password using ActionChains
                    actions = ActionChains(self.driver)
                    actions.click(password_input)
                    actions.send_keys(password)
                    actions.perform()
                    time.sleep(0.3)
                    
                    # Verify entered password
                    entered_password = password_input.get_attribute('value')
                    
                    if entered_password:
                        password_entered = True
                        self.log("✓ Method 3 successful: Password entered")
                        
                        # Submit with ENTER key
                        password_input.send_keys(Keys.RETURN)
                        self.log("✓ Submitted with ENTER key")
                    else:
                        self.log("✗ Method 3 failed: Password not entered")
                        
                except Exception as e:
                    self.log_error(f"Method 3 error: {str(e)}")

            # If all methods failed, raise error
            if not password_entered:
                self.log_error("✗ All password entry methods failed!")
                self.add_failed_login(f"{email}:{password}", "All password entry methods failed")
                return False

            # Check if login was successful - OPTIMIZED AND FAST
            self.log("Checking if login was successful...")
            
            try:
                # Wait for page to load after password submission
                time.sleep(3)
                
                # Check current URL
                current_url = self.driver.current_url
                self.log(f"URL after password submission: {current_url}")
                
                # Check if redirected to Gmail or Google Account homepage
                if "mail.google.com" in current_url or "myaccount.google.com" in current_url:
                    self.log(f"✓ Login successful: {email}")
                    
                    # Handle post-login pop-ups
                    self.handle_post_login_popup()
                    
                    self.add_successful_login(f"{email}:{password}")
                    return True
                
                # Additional checks: Are we still on a captcha or error page?
                current_url_lower = current_url.lower()
                page_source = self.driver.page_source.lower()
                
                # If captcha is still present, login failed
                if 'captcha' in current_url_lower or ('what you hear' in page_source and 'what you see' in page_source):
                    self.log_error(f"✗ Captcha not solved; still on captcha page: {email}")
                    self.add_failed_login(f"{email}:{password}", "Captcha not solved - still on captcha page")
                    return False
                
                # If an error message is present, login failed
                try:
                    error_element = self.driver.find_element(By.CSS_SELECTOR, "[data-alert]")
                    if error_element.is_displayed():
                        error_text = error_element.text
                        self.log_error(f"✗ Login error ({email}): {error_text}")
                        self.add_failed_login(f"{email}:{password}", error_text)
                        return False
                except NoSuchElementException:
                    pass  # No error message found; continue
                
                # If still on password page, login failed
                if 'password' in current_url_lower or 'signin/v2/challenge/pwd' in current_url_lower:
                    self.log_error(f"✗ Still on password page; login failed: {email}")
                    self.add_failed_login(f"{email}:{password}", "Still on password page - login failed")
                    return False
                
                # For other cases, wait with WebDriverWait for successful redirect
                try:
                    WebDriverWait(self.driver, 5).until(
                        lambda driver: "mail.google.com" in driver.current_url or "myaccount.google.com" in driver.current_url
                    )
                    self.log(f"✓ Login successful: {email}")
                    
                    # Handle post-login pop-ups
                    self.handle_post_login_popup()
                    
                    self.add_successful_login(f"{email}:{password}")
                    return True
                except TimeoutException:
                    self.log_error(f"✗ Timeout - Login failed: {email}")
                    self.add_failed_login(f"{email}:{password}", "Timeout - Login failed")
                    return False

            except Exception as e:
                self.log_error(f"✗ Login verification error: {str(e)}")
                self.add_failed_login(f"{email}:{password}", f"Login verification error: {str(e)}")
                return False
        except Exception as e:
            error_message = f"Input error: {str(e)}"
            self.log(f"✗ Login error ({email}): {str(e)}")
            self.add_failed_login(f"{email}:{password}", error_message)
            return False
            
    def handle_post_login_popup(self):
        """Handle post-login pop-ups"""
        try:
            self.log("Post-login pop-up check is being performed...")
            
            # Check the pop-ups - wait 3 seconds
            time.sleep(3)
            
            # FIRST: Check the 'Welcome to your new account' screen
            if self.is_welcome_screen():
                self.log("✓ The 'Welcome to your new account' screen has been detected.", level="SUCCESS")
                return self.handle_welcome_screen()
            
            # Various selectors for the "I understand" button
            understood_selectors = [
                "//button[contains(text(), 'Anladım')]",
                "//button[contains(text(), 'Tamam')]", 
                "//button[contains(text(), 'OK')]",
                "//button[contains(text(), 'Got it')]",
                "//button[contains(text(), 'Understood')]",
                "//button[contains(text(), 'Continue')]",
                "//button[contains(text(), 'Devam')]",
                "//span[contains(text(), 'Anladım')]",
                "//span[contains(text(), 'Tamam')]",
                "//div[contains(text(), 'Anladım')]",
                "//div[contains(text(), 'Tamam')]",
                "[data-action='dismiss']",
                "[aria-label*='Anladım']",
                "[aria-label*='Tamam']",
                "[aria-label*='OK']",
                ".popup-close",
                ".modal-close",
                ".dialog-close"
            ]
            
            popup_found = False
            
            for selector in understood_selectors:
                try:
                    if selector.startswith("//") or selector.startswith("//"):
                        # XPath selector
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        # CSS selector
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            try:
                                self.log(f"✓ Pop-up button found: {selector}")
                                element.click()
                                self.log("✓ Pop-up closed")
                                popup_found = True
                                time.sleep(1)  # Wait for the pop-up to close
                                break
                            except Exception as e:
                                self.log(f"Pop-up button click error: {str(e)}")
                                continue
                    
                    if popup_found:
                        break
                        
                except Exception as e:
                    continue
            
            # If the pop-up cannot be found, log
            if not popup_found:
                self.log("Pop-up not found or already closed")
            
            return popup_found
            
        except Exception as e:
            self.log_error(f"Pop-up handle error: {str(e)}")
            return False

    def is_welcome_screen(self):
        """Check if we are on the 'Welcome to your new account' screen"""
        try:
            page_source = self.driver.page_source.lower()
            
            # Characteristic indicators of this screen
            welcome_indicators = [
                'welcome to your new account',
                'google workspace for education',
                'this account is managed by your school',
                'google services you can access with your account',
                'google workspace services',
                'google workspace additional services',
                'this notice or the information shared above',
                'from your school, parent, or guardian'
            ]
            
            # Check if at least 4 indicators are present
            found_indicators = sum(1 for indicator in welcome_indicators if indicator in page_source)
            
            if found_indicators >= 4:
                self.log(f"✓ Welcome screen detected ({found_indicators}/8 indicators)", level="SUCCESS")
                return True
            
            return False
            
        except Exception as e:
            self.log_error(f"Error checking for welcome screen: {str(e)}")
            return False

    def handle_welcome_screen(self):
        """Handle the 'Welcome to your new account' screen"""
        try:
            self.log("Processing 'Welcome to your new account' screen...")

            # MOST RELIABLE METHOD: Find the 'Got it' button based on specific HTML structure
            self.log("MOST RELIABLE METHOD: Looking for 'Got it' button using specific HTML structure...")
            try:
                # First, scroll to the bottom of the page
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

                # Specific selectors
                specific_selectors = [
                    "input[value='Got it']",
                    "input[type='submit'][value='Got it']",
                    "input[name='confirm'][value='Got it']",
                    "input[id='confirm']",
                    "input.jsname='M2UYVd'",
                    "input[class*='MK9CEd']",
                    "input[class*='MVpUfe']"
                ]

                button_found = False

                for selector in specific_selectors:
                    try:
                        self.log(f"Trying specific selector: {selector}")
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                        self.log(f"Found {len(elements)} element(s) with selector '{selector}'")

                        for j, element in enumerate(elements):
                            try:
                                element_value = element.get_attribute('value')
                                element_type = element.get_attribute('type')
                                is_displayed = element.is_displayed()
                                is_enabled = element.is_enabled()

                                self.log(f"Element {j+1}: value='{element_value}', type='{element_type}', displayed={is_displayed}, enabled={is_enabled}")

                                if is_displayed and is_enabled and element_value == 'Got it':
                                    try:
                                        self.log(f"✓ 'Got it' button found: {selector} - Element {j+1}")

                                        # Scroll to element
                                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                                        time.sleep(0.5)

                                        # Click via JavaScript
                                        self.driver.execute_script("arguments[0].click();", element)
                                        self.log("✓ 'Got it' button clicked via JavaScript")

                                        # Try normal click
                                        try:
                                            element.click()
                                            self.log("✓ 'Got it' button clicked with normal click")
                                        except:
                                            pass

                                        # Submit form if possible
                                        try:
                                            form = element.find_element(By.XPATH, "./ancestor::form")
                                            form.submit()
                                            self.log("✓ Form submitted")
                                        except:
                                            pass

                                        button_found = True
                                        break

                                    except Exception as e:
                                        self.log_error(f"Error clicking 'Got it' button: {str(e)}")
                                        continue
                            except Exception as e:
                                self.log_error(f"Error checking element {j+1}: {str(e)}")
                                continue

                        if button_found:
                            break

                    except Exception as e:
                        self.log_error(f"Error with selector '{selector}': {str(e)}")
                        continue

                if button_found:
                    self.log("✓ MOST RELIABLE METHOD: Specific HTML click successful!")
                    return True
                else:
                    self.log_error("✗ MOST RELIABLE METHOD: 'Got it' button not found using specific HTML!")

            except Exception as e:
                self.log_error(f"MOST RELIABLE METHOD error: {str(e)}")
            # LAST RESORT: Coordinate-based click
            self.log("LAST RESORT: Performing coordinate-based click...")
            try:
                # Scroll to the bottom of the page
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                # Perform a coordinate-based click near the bottom of the page
                self.driver.execute_script("""
                    // Click at the bottom part of the page
                    var clickEvent = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: window.innerWidth / 2,
                        clientY: window.innerHeight - 100
                    });
                    
                    document.elementFromPoint(window.innerWidth / 2, window.innerHeight - 100).dispatchEvent(clickEvent);
                    console.log('Coordinate-based click performed');
                """)
                
                self.log("✓ LAST RESORT: Coordinate-based click performed")
                return True
                
            except Exception as e:
                self.log_error(f"LAST RESORT error: {str(e)}")
            # SECOND METHOD: Find "Got it" in page source and click directly
            self.log("SECOND METHOD: Searching for 'Got it' in page source...")
            try:
                page_source = self.driver.page_source
                if 'got it' in page_source.lower():
                    self.log("✓ 'Got it' text found in page source")

                    # Click directly using JavaScript
                    self.driver.execute_script("""
                        var elements = document.querySelectorAll('button, span, div, a');
                        for (var i = 0; i < elements.length; i++) {
                            var element = elements[i];
                            if (element.textContent && element.textContent.includes('Got it')) {
                                element.scrollIntoView();
                                element.click();
                                console.log('Got it clicked');
                                break;
                            }
                        }
                    """)
                    self.log("✓ SECOND METHOD: JavaScript click performed")

                    # Consider successful immediately (no need to wait)
                    self.log("✓ Welcome screen successfully handled")
                    return True
                else:
                    self.log_error("✗ SECOND METHOD: 'Got it' text not found in page source!")

            except Exception as e:
                self.log_error(f"SECOND METHOD error: {str(e)}")
            
            
            # THIRD METHOD: Scroll to bottom of page and try again
            self.log("THIRD METHOD: Scrolling to bottom of page...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Check page source
            page_source = self.driver.page_source
            self.log(f"Page source length: {len(page_source)} characters")

            # Check if "Got it" text exists
            if 'got it' in page_source.lower():
                self.log("✓ 'Got it' text found in page source")
            else:
                self.log_error("✗ 'Got it' text not found in page source!")

            # List all buttons
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            self.log(f"Found {len(all_buttons)} button elements on the page")

            for i, button in enumerate(all_buttons):
                try:
                    button_text = button.text.strip()
                    is_displayed = button.is_displayed()
                    is_enabled = button.is_enabled()
                    self.log(f"Button {i+1}: text='{button_text}', displayed={is_displayed}, enabled={is_enabled}")
                except:
                    pass

            # FIRST: Use JavaScript to find and scroll to the "Got it" button
            self.log("Searching for 'Got it' button via JavaScript...")
            button_element = self.driver.execute_script("""
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    var button = buttons[i];
                    var text = button.textContent || button.innerText || '';
                    
                    if (text.trim() === 'Got it' || text.includes('Got it')) {
                        console.log('Got it button found:', button);
                        
                        // Scroll into view
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        
                        // Click after a short delay
                        setTimeout(function() {
                            console.log('Clicking Got it button...');
                            button.click();
                            console.log('Got it button clicked');
                        }, 1000);
                        
                        return button;
                    }
                }
                return null;
            """)

            if button_element:
                self.log("✓ 'Got it' button found and clicked via JavaScript")
                time.sleep(3)  # Wait for page to load

                # Check URL change
                current_url = self.driver.current_url
                self.log(f"URL after click: {current_url}")

                if 'mail.google.com' in current_url or 'myaccount.google.com' in current_url:
                    self.log("✓ URL changed; JavaScript click successful!")
                    return True

            # Find and click "Got it" button - ROBUST AND DETAILED
            understood_selectors = [
                "//button[contains(text(), 'Got it')]",
                "//button[contains(text(), 'Understood')]",
                "//span[contains(text(), 'Got it')]",
                "//div[contains(text(), 'Got it')]",
                "//*[contains(text(), 'Got it')]",  # Any element
                "[aria-label*='Got it']",
                "button[type='button']",  # Generic button
                ".button",  # CSS class
                "[role='button']",  # Role attribute
                "button"  # All buttons
            ]
            
            button_found = False
            for selector in understood_selectors:
                try:
                    self.log(f"Trying selector: {selector}")
                    
                    if selector.startswith("//"):
                        # XPath selector
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        # CSS selector
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    self.log(f"Found {len(elements)} element(s) with selector '{selector}'")
                    
                    for j, element in enumerate(elements):
                        try:
                            element_text = element.text.strip()
                            is_displayed = element.is_displayed()
                            is_enabled = element.is_enabled()
                            
                            self.log(f"Element {j+1}: text='{element_text}', displayed={is_displayed}, enabled={is_enabled}")
                            
                            if is_displayed and is_enabled:
                                # Check element text
                                if 'got it' in element_text.lower() or 'understood' in element_text.lower():
                                    try:
                                        self.log(f"✓ 'Got it' button found: {selector} - Element {j+1}")
                                        
                                        # Log element position
                                        location = element.location
                                        size = element.size
                                        self.log(f"Element position: x={location['x']}, y={location['y']}")
                                        self.log(f"Element size: width={size['width']}, height={size['height']}")
                                        
                                        # Scroll to element
                                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                                        time.sleep(1)
                                        
                                        # METHOD 1: JavaScript click
                                        try:
                                            self.driver.execute_script("arguments[0].click();", element)
                                            self.log("✓ Method 1: JavaScript click successful")
                                        except Exception as e:
                                            self.log_error(f"Method 1 error: {str(e)}")
                                        
                                        # METHOD 2: Normal click
                                        try:
                                            element.click()
                                            self.log("✓ Method 2: Normal click successful")
                                        except Exception as e:
                                            self.log_error(f"Method 2 error: {str(e)}")
                                        
                                        # METHOD 3: ActionChains click
                                        try:
                                            from selenium.webdriver.common.action_chains import ActionChains
                                            actions = ActionChains(self.driver)
                                            actions.move_to_element(element).click().perform()
                                            self.log("✓ Method 3: ActionChains click successful")
                                        except Exception as e:
                                            self.log_error(f"Method 3 error: {str(e)}")
                                        
                                        # METHOD 4: Coordinate-based click
                                        try:
                                            # Get center coordinates of the element
                                            center_x = location['x'] + size['width'] // 2
                                            center_y = location['y'] + size['height'] // 2
                                            
                                            # Perform coordinate-based click
                                            self.driver.execute_script(f"document.elementFromPoint({center_x}, {center_y}).click();")
                                            self.log(f"✓ Method 4: Coordinate click successful ({center_x}, {center_y})")
                                        except Exception as e:
                                            self.log_error(f"Method 4 error: {str(e)}")
                                        
                                        # METHOD 5: Enter key
                                        try:
                                            from selenium.webdriver.common.keys import Keys
                                            element.send_keys(Keys.RETURN)
                                            self.log("✓ Method 5: Enter key successful")
                                        except Exception as e:
                                            self.log_error(f"Method 5 error: {str(e)}")
                                        
                                        # METHOD 6: Space key
                                        try:
                                            element.send_keys(Keys.SPACE)
                                            self.log("✓ Method 6: Space key successful")
                                        except Exception as e:
                                            self.log_error(f"Method 6 error: {str(e)}")
                                        
                                        # METHOD 7: Mouse event simulation
                                        try:
                                            self.driver.execute_script("""
                                                var element = arguments[0];
                                                var event = new MouseEvent('click', {
                                                    view: window,
                                                    bubbles: true,
                                                    cancelable: true
                                                });
                                                element.dispatchEvent(event);
                                            """, element)
                                            self.log("✓ Method 7: Mouse event simulation successful")
                                        except Exception as e:
                                            self.log_error(f"Method 7 error: {str(e)}")
                                        
                                        # METHOD 8: Form submit (if inside a form)
                                        try:
                                            form = element.find_element(By.XPATH, "./ancestor::form")
                                            if form:
                                                form.submit()
                                                self.log("✓ Method 8: Form submit successful")
                                        except:
                                            pass
                                        
                                        # Wait for page to load
                                        time.sleep(3)
                                        
                                        button_found = True
                                        break
                                    except Exception as e:
                                        self.log_error(f"'Got it' button click error: {str(e)}")
                                        continue
                        except Exception as e:
                            self.log_error(f"Error checking element {j+1}: {str(e)}")
                            continue
                    
                    if button_found:
                        break
                        
                except Exception as e:
                    self.log_error(f"Error with selector '{selector}': {str(e)}")
                    continue
            
            if not button_found:
                self.log_error("'Got it' button could not be found by any method!")

                # LAST RESORT: Direct JavaScript click
                self.log("LAST RESORT: Searching for 'Got it' button via JavaScript...")
                try:
                    # Find elements containing "Got it" text in page source
                    self.driver.execute_script("""
                        var elements = document.querySelectorAll('*');
                        for (var i = 0; i < elements.length; i++) {
                            var element = elements[i];
                            if (element.textContent && element.textContent.includes('Got it')) {
                                console.log('Got it text found:', element);
                                element.click();
                                console.log('Got it button clicked');
                                break;
                            }
                        }
                    """)
                    self.log("✓ LAST RESORT: Direct JavaScript click performed")
                    button_found = True
                except Exception as e:
                    self.log_error(f"LAST RESORT error: {str(e)}")

                # Debug: Show a preview of page source
                self.log("Page source preview:")
                page_preview = page_source[:2000] if len(page_source) > 2000 else page_source
                self.log(f"Page source: {page_preview}")

                if not button_found:
                    # FINAL ATTEMPT: Analyze HTML source to locate element directly
                    self.log("FINAL ATTEMPT: Analyzing page source to locate HTML element...")
                    try:
                        # Find HTML elements containing "Got it" in page source
                        import re

                        # Regex to match HTML elements containing "Got it"
                        gotit_pattern = r'<[^>]*>[^<]*Got it[^<]*</[^>]*>'
                        matches = re.findall(gotit_pattern, page_source, re.IGNORECASE)

                        self.log(f"Found {len(matches)} 'Got it' elements in HTML")
                        for i, match in enumerate(matches):
                            self.log(f"HTML Element {i+1}: {match}")

                        # Use JavaScript to scan all elements and find "Got it"
                        result = self.driver.execute_script("""
                            var elements = document.querySelectorAll('*');
                            var foundElements = [];

                            for (var i = 0; i < elements.length; i++) {
                                var element = elements[i];
                                var text = element.textContent || element.innerText || '';

                                if (text.trim() === 'Got it' || text.includes('Got it')) {
                                    foundElements.push({
                                        tagName: element.tagName,
                                        text: text.trim(),
                                        className: element.className,
                                        id: element.id,
                                        element: element
                                    });
                                }
                            }

                            return foundElements;
                        """)

                        self.log(f"JavaScript found {len(result)} 'Got it' elements")
                        for i, elem in enumerate(result):
                            self.log(f"Element {i+1}: {elem['tagName']} - '{elem['text']}' - class='{elem['className']}' - id='{elem['id']}'")

                        # Click each found element
                        if result:
                            for i, elem in enumerate(result):
                                try:
                                    # Re-locate the element
                                    element = None
                                    if elem['id']:
                                        element = self.driver.find_element(By.ID, elem['id'])
                                    elif elem['className']:
                                        # Handle multiple classes
                                        class_selector = "." + elem['className'].replace(" ", ".")
                                        element = self.driver.find_element(By.CSS_SELECTOR, class_selector)
                                    else:
                                        # Fallback: find by tag and text
                                        elements = self.driver.find_elements(By.TAG_NAME, elem['tagName'])
                                        for el in elements:
                                            if el.text.strip() == 'Got it':
                                                element = el
                                                break

                                    if element:
                                        self.log(f"Clicking element {i+1}...")

                                        # Scroll into view
                                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                        time.sleep(0.5)

                                        # Multiple click methods
                                        try:
                                            element.click()
                                            self.log(f"✓ Element {i+1}: Normal click successful")
                                        except:
                                            pass

                                        try:
                                            self.driver.execute_script("arguments[0].click();", element)
                                            self.log(f"✓ Element {i+1}: JavaScript click successful")
                                        except:
                                            pass

                                        try:
                                            from selenium.webdriver.common.action_chains import ActionChains
                                            ActionChains(self.driver).move_to_element(element).click().perform()
                                            self.log(f"✓ Element {i+1}: ActionChains click successful")
                                        except:
                                            pass

                                        # Check for URL change
                                        time.sleep(2)
                                        current_url = self.driver.current_url
                                        self.log(f"URL after click: {current_url}")

                                        if 'mail.google.com' in current_url or 'myaccount.google.com' in current_url:
                                            self.log("✓ URL changed; click successful!")
                                            button_found = True
                                            break

                                except Exception as e:
                                    self.log_error(f"Error clicking element {i+1}: {str(e)}")
                                    continue

                        if not button_found:
                            # FINAL TRY: Coordinate-based click in bottom area
                            self.log("FINAL TRY: Performing coordinate-based click in bottom area...")
                            try:
                                # Look for "Got it" button in lower portion of page
                                clicked = self.driver.execute_script("""
                                    var buttons = document.querySelectorAll('button');
                                    for (var i = 0; i < buttons.length; i++) {
                                        var button = buttons[i];
                                        var rect = button.getBoundingClientRect();

                                        // Check if button is in bottom 30% and visible
                                        if (rect.top > window.innerHeight * 0.7 && 
                                            rect.bottom < window.innerHeight && 
                                            button.offsetParent !== null) {

                                            var text = button.textContent || button.innerText || '';
                                            if (text.includes('Got it') || text.includes('Understood')) {
                                                console.log('Got it button found in bottom area:', button);
                                                button.click();
                                                console.log('Got it button clicked in bottom area');
                                                return true;
                                            }
                                        }
                                    }
                                    return false;
                                """)
                                if clicked:
                                    self.log("✓ FINAL TRY: Coordinate-based click successful")
                                    button_found = True
                                else:
                                    self.log("✗ FINAL TRY: No 'Got it' button found in bottom area")
                            except Exception as e:
                                self.log_error(f"FINAL TRY error: {str(e)}")

                    except Exception as e:
                        self.log_error(f"FINAL ATTEMPT error: {str(e)}")

                    if not button_found:
                        return False

            self.log("✓ Welcome screen successfully handled", level="SUCCESS")
            return True
            
        except Exception as e:
            self.log_error(f"HWelcome screen processing error: {str(e)}")
            import traceback
            self.log_error(f"Traceback: {traceback.format_exc()}")
            return False

    def handle_tos_page(self):
        """Find and click the 'Got it' button on the Google Terms of Service page"""
        try:
            self.log("Looking for 'Got it' button on Google Terms of Service page...")

            # Check page source
            page_source = self.driver.page_source.lower()

            # Check if "Got it" text exists
            if 'got it' in page_source:
                self.log("✓ 'Got it' text found in page source")
            else:
                self.log_error("✗ 'Got it' text not found in page source!")

            # Find and click the "Got it" button
            understood_selectors = [
                "//button[contains(text(), 'Got it')]",
                "//button[contains(text(), 'Understood')]",
                "//span[contains(text(), 'Got it')]",
                "//div[contains(text(), 'Got it')]",
                "//*[contains(text(), 'Got it')]",  # Any element
                "[aria-label*='Got it']",
                "button[type='button']",  # Generic button
                ".button",  # CSS class
                "[role='button']",  # Role attribute
                "button"  # All buttons
            ]

            button_found = False

            for selector in understood_selectors:
                try:
                    self.log(f"Trying selector: {selector}")

                    if selector.startswith("//"):
                        # XPath selector
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        # CSS selector
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    self.log(f"Found {len(elements)} element(s) with selector '{selector}'")

                    for j, element in enumerate(elements):
                        try:
                            element_text = element.text.strip()
                            is_displayed = element.is_displayed()
                            is_enabled = element.is_enabled()

                            self.log(f"Element {j+1}: text='{element_text}', displayed={is_displayed}, enabled={is_enabled}")

                            if is_displayed and is_enabled:
                                # Check element text
                                if 'got it' in element_text.lower() or 'understood' in element_text.lower():
                                    try:
                                        self.log(f"✓ 'Got it' button found: {selector} - Element {j+1}")

                                        # Scroll to element
                                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)

                                        # Click via JavaScript
                                        self.driver.execute_script("arguments[0].click();", element)
                                        self.log("✓ 'Got it' button clicked via JavaScript")

                                        # Try normal click
                                        try:
                                            element.click()
                                            self.log("✓ 'Got it' button clicked with normal click")
                                        except:
                                            pass

                                        # Consider successful immediately (no need to wait)
                                        self.log("✓ Terms of Service page successfully handled")
                                        button_found = True
                                        break

                                    except Exception as e:
                                        self.log_error(f"'Got it' button click error: {str(e)}")
                                        continue
                        except Exception as e:
                            self.log_error(f"Error checking element {j+1}: {str(e)}")
                            continue

                    if button_found:
                        break

                except Exception as e:
                    self.log_error(f"Error with selector '{selector}': {str(e)}")
                    continue

            if not button_found:
                self.log_error("'Got it' button could not be found by any method!")
                return False

            self.log("✓ Terms of Service page successfully handled", level="SUCCESS")
            return True

        except Exception as e:
            self.log_error(f"Error handling Terms of Service page: {str(e)}")
            return False

    def logout_from_gmail(self):
        """Log out from Gmail - FAST"""
        try:
            # Open account menu
            account_button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-ogsr-up]"))
            )
            account_button.click()
            
            # Find and click the "Sign out" button (supports both English and Turkish)
            logout_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign out') or contains(text(), 'Çıkış yap')]"))
            )
            logout_button.click()
            
            return True
            
        except Exception as e:
            return False
            
    def process_account(self, account_line):
        """Process a single account"""
        try:
            # Stop check
            if not self.is_running:
                return False
                
            # Parse mail:password format
            parts = account_line.strip().split(':')
            if len(parts) < 2:
                self.log(f"✗ Invalid format: {account_line.strip()}")
                return False
                
            email = parts[0]
            password = ':'.join(parts[1:])  # Password may contain ':' characters
            
            # Get proxy
            proxy = self.get_next_proxy()
            
            # Set up driver
            if not self.setup_driver(proxy):
                return False
                
            # Log proxy usage info
            if proxy:
                proxy_host = proxy.split(':')[2]
                self.log(f"Using proxy: {proxy_host}")
            else:
                self.log("No proxy used")
                
            try:
                # Perform login
                login_success = self.login_to_gmail(email, password)
                
                if login_success:
                    # Successful login is already logged in login_to_gmail
                    
                    # Short delay
                    time.sleep(random.uniform(1, 2))
                    
                    # Log out
                    self.logout_from_gmail()
                    
                    # Delay between accounts
                    time.sleep(self.delay)
                else:
                    # Failed login is already logged in login_to_gmail
                    pass
                    
                return login_success
                
            finally:
                # Cleanly close the driver
                if self.driver:
                    try:
                        self.driver.quit()
                        time.sleep(0.3)  # Wait for shutdown
                    except Exception as e:
                        self.log(f"Driver shutdown error: {str(e)}")
                    finally:
                        self.driver = None
                
                # Clean up temporary proxy files
                try:
                    for file in os.listdir('.'):
                        if file.startswith('proxy_auth_plugin_') and file.endswith('.zip'):
                            os.remove(file)
                except:
                    pass
                        
        except Exception as e:
            self.log(f"✗ Account processing error: {str(e)}")
            # Also log as failed login on error
            if 'email' in locals():
                self.add_failed_login(email, f"Account processing error: {str(e)}")
            return False
            
    def stop(self):
        """Stop the bot"""
        self.is_running = False
        if self.driver:
            try:
                # Close Chrome cleanly
                self.driver.quit()
                time.sleep(0.5)  # Wait for shutdown
            except Exception as e:
                self.log(f"Driver shutdown error: {str(e)}")
            finally:
                self.driver = None
        self.log("Bot stopped!")

    def run(self):
        """Run the bot"""
        self.log(f"Thread started - {len(self.accounts)} accounts to process")
        
        success_count = 0
        total_count = len(self.accounts)
        
        for i, account_line in enumerate(self.accounts, 1):
            # Stop check
            if not self.is_running:
                self.log("Bot stopped!")
                break
                
            if not account_line.strip():
                continue
                
            self.log(f"[{i}/{total_count}] Processing: {account_line.strip().split(':')[0]}")
            
            # Process each account
            try:
                if self.process_account(account_line):
                    success_count += 1
            except Exception as e:
                self.log(f"Account processing error: {str(e)}")
            
            # Stop check
            if not self.is_running:
                self.log("Bot stopped!")
                break
                
            # Random delay between threads
            time.sleep(random.uniform(0.5, 1.5))
            
        self.log(f"Thread completed - {success_count}/{total_count} successful")
        
        # Close log file
        if self.log_file:
            self.log_file.close()
            
    def add_failed_login(self, account, error_message):
        self.save_failed_login_to_file(account, error_message)
        
    def save_failed_login_to_file(self, account, error_message):
        """Save the failed entry to the file immediately"""
        try:
            with open("failed_logins.txt", 'a', encoding='utf-8') as f:
                f.write(f"{account}\n")
                f.write(f"Sebep: {error_message}\n")
                f.write("-" * 30 + "\n")
            self.log(f"✓ Başarısız giriş kaydedildi: {account.split(':')[0]}")
        except Exception as e:
            self.log_error(f"Failed dosyasına kaydetme hatası: {str(e)}")
        
    def remove_successful_account_from_file(self, email):
        """Remove successful account from the original file"""
        if not self.original_accounts_file:
            return
            
        try:
            # Read the file
            with open(self.original_accounts_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find and remove the successful account
            remaining_lines = []
            for line in lines:
                if line.strip() and not line.strip().startswith(email + ':'):
                    remaining_lines.append(line)
            
            # Update the file
            with open(self.original_accounts_file, 'w', encoding='utf-8') as f:
                f.writelines(remaining_lines)
            
            self.log(f"✓ Successful account removed from file: {email}")
            
        except Exception as e:
            self.log_error(f"Error removing account from file: {str(e)}")

    def save_to_success_file(self, account):
        """Save successful account to success file"""
        try:
            with open("successful_logins.txt", 'a', encoding='utf-8') as f:
                f.write(account + '\n')
            self.log(f"✓ Successful account saved: {account.split(':')[0]}")
        except Exception as e:
            self.log_error(f"Error saving to success file: {str(e)}")

    def add_successful_login(self, account):
        """Record a successful login"""
        # Remove successful account from the original file
        email = account.split(':')[0] if ':' in account else account
        self.remove_successful_account_from_file(email)
        
        # Add to success file
        self.save_to_success_file(account)
        
    def save_failed_logins(self):
        """Save failed login attempts to file"""
        try:
            # Save only to failed_logins.txt
            filename = "failed_logins.txt"
            
            with open(filename, 'a', encoding='utf-8') as f:
                for failed_login in self.failed_logins:
                    f.write(f"{failed_login['account']}\n")
                    f.write(f"Reason: {failed_login['error']}\n")
                    f.write("-" * 30 + "\n")
                    
            self.log(f"✓ Failed logins saved: {filename}")
            
        except Exception as e:
            self.log(f"✗ Error saving failed logins: {str(e)}")
            
