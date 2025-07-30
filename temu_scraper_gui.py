"""
Temu Scraper GUI - A user-friendly interface for the Temu Playwright scraper

Features:
- User input for search query, proxy settings, and timing intervals
- Real-time progress and log display
- Step-by-step workflow with user confirmations
- Ability to stop and save results at any time
- All original scraper functionality preserved
"""

import json
import time
import csv
import random
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from datetime import datetime
import queue
import sys

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync


class TemuScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Temu Scraper GUI")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # Variables
        self.scraping_active = False
        self.scraper_thread = None
        self.log_queue = queue.Queue()
        self.products = []
        self.context = None
        self.page = None
        self.stop_requested = False
        
        # Default values
        self.search_query = tk.StringVar(value="menshoes")
        self.min_interval = tk.IntVar(value=2)
        self.max_interval = tk.IntVar(value=5)
        self.cooldown_frequency = tk.IntVar(value=2)
        self.use_proxy = tk.BooleanVar(value=False)
        self.proxy_server = tk.StringVar(value="")
        self.output_file = tk.StringVar(value="products.csv")
        self.save_session = tk.BooleanVar(value=True)
        
        # Session persistence
        self.session_dir = Path(__file__).parent / "temu_session"
        
        self.setup_ui()
        self.start_log_processor()
        
    def setup_ui(self):
        """Create the main UI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Temu Scraper", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Input section
        self.create_input_section(main_frame)
        
        # Control buttons
        self.create_control_section(main_frame)
        
        # Progress section
        self.create_progress_section(main_frame)
        
        # Log section
        self.create_log_section(main_frame)
        
        # Status bar
        self.create_status_bar(main_frame)
        
    def create_input_section(self, parent):
        """Create input configuration section"""
        # Input frame
        input_frame = ttk.LabelFrame(parent, text="Configuration", padding="10")
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        # Search query
        ttk.Label(input_frame, text="Search Query:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        search_entry = ttk.Entry(input_frame, textvariable=self.search_query, width=40)
        search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Interval settings
        interval_frame = ttk.Frame(input_frame)
        interval_frame.grid(row=0, column=2, sticky=tk.W)
        ttk.Label(interval_frame, text="Interval (min):").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Spinbox(interval_frame, from_=2, to=15, textvariable=self.min_interval, width=5).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(interval_frame, text="to").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Spinbox(interval_frame, from_=2, to=15, textvariable=self.max_interval, width=5).pack(side=tk.LEFT)
        
        # Cooldown frequency setting
        cooldown_frame = ttk.Frame(input_frame)
        cooldown_frame.grid(row=0, column=3, sticky=tk.W)
        ttk.Label(cooldown_frame, text="Cooldown every:").pack(side=tk.LEFT, padx=(15, 5))
        ttk.Spinbox(cooldown_frame, from_=1, to=10, textvariable=self.cooldown_frequency, width=5).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(cooldown_frame, text="requests").pack(side=tk.LEFT)
        
        # Proxy settings
        proxy_frame = ttk.Frame(input_frame)
        proxy_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        proxy_frame.columnconfigure(1, weight=1)
        
        ttk.Checkbutton(proxy_frame, text="Use Proxy", variable=self.use_proxy, 
                       command=self.toggle_proxy).grid(row=0, column=0, sticky=tk.W)
        
        self.proxy_entry = ttk.Entry(proxy_frame, textvariable=self.proxy_server, 
                                   state="disabled")
        self.proxy_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 10))
        
        # Session saving option
        ttk.Checkbutton(proxy_frame, text="Save Login Session", variable=self.save_session).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Session management buttons
        session_buttons_frame = ttk.Frame(proxy_frame)
        session_buttons_frame.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        ttk.Button(session_buttons_frame, text="Clear Session", command=self.clear_session, width=12).pack(side=tk.LEFT, padx=(0, 5))
        
        # Session status
        self.session_status_label = ttk.Label(proxy_frame, text="", foreground="gray")
        self.session_status_label.grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        
        # Update session status on startup
        self.update_session_status()
        
        # Output file
        ttk.Label(proxy_frame, text="Output CSV:").grid(row=0, column=2, sticky=tk.W, padx=(10, 5))
        ttk.Entry(proxy_frame, textvariable=self.output_file, width=20).grid(row=0, column=3, sticky=tk.W)
        ttk.Button(proxy_frame, text="Browse", command=self.browse_output_file, width=8).grid(row=0, column=4, padx=(5, 0))
        
    def create_control_section(self, parent):
        """Create control buttons section"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=2, column=0, columnspan=3, pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="Start Scraping", 
                                     command=self.start_scraping, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.ready_button = ttk.Button(control_frame, text="I'm Ready (Continue)", 
                                     command=self.user_ready, state="disabled")
        self.ready_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.captcha_button = ttk.Button(control_frame, text="CAPTCHA Solved", 
                                       command=self.captcha_solved, state="disabled")
        self.captcha_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="Stop & Save", 
                                    command=self.stop_scraping, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_button = ttk.Button(control_frame, text="Clear Logs", 
                                     command=self.clear_logs)
        self.clear_button.pack(side=tk.LEFT)
        
    def create_progress_section(self, parent):
        """Create progress display section"""
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        
        # Progress bar
        ttk.Label(progress_frame, text="Status:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Stats
        self.stats_label = ttk.Label(progress_frame, text="Products scraped: 0 | Status: Ready")
        self.stats_label.grid(row=0, column=2, sticky=tk.E)
        
    def create_log_section(self, parent):
        """Create log display section"""
        log_frame = ttk.LabelFrame(parent, text="Logs", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log text area with scrollbar
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=100, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
    def create_status_bar(self, parent):
        """Create status bar"""
        self.status_var = tk.StringVar(value="Ready to start scraping")
        status_bar = ttk.Label(parent, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def toggle_proxy(self):
        """Toggle proxy input field"""
        if self.use_proxy.get():
            self.proxy_entry.config(state="normal")
        else:
            self.proxy_entry.config(state="disabled")
            
    def browse_output_file(self):
        """Browse for output CSV file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.output_file.set(filename)
            
    def log_message(self, message):
        """Add message to log queue"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}")
        
    def start_log_processor(self):
        """Process log messages from queue"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.root.update_idletasks()
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.start_log_processor)
        
    def clear_logs(self):
        """Clear the log display"""
        self.log_text.delete(1.0, tk.END)
        
    def update_stats(self, products_count, status):
        """Update progress statistics"""
        self.stats_label.config(text=f"Products scraped: {products_count} | Status: {status}")
        self.status_var.set(status)
        
    def start_scraping(self):
        """Start the scraping process"""
        # Validate inputs
        if not self.search_query.get().strip():
            messagebox.showerror("Error", "Please enter a search query")
            return
            
        if self.min_interval.get() > self.max_interval.get():
            messagebox.showerror("Error", "Minimum interval cannot be greater than maximum interval")
            return
            
        if self.use_proxy.get() and not self.proxy_server.get().strip():
            messagebox.showerror("Error", "Please enter proxy server details")
            return
            
        # Reset state
        self.stop_requested = False
        self.products = []
        
        # Update UI
        self.scraping_active = True
        self.start_button.config(state="disabled")
        self.ready_button.config(state="normal")
        self.stop_button.config(state="normal")
        self.progress_bar.start()
        
        # Start scraping thread
        self.scraper_thread = threading.Thread(target=self.run_scraper, daemon=True)
        self.scraper_thread.start()
        
        self.log_message("Scraping started - browser will open for login")
        self.update_stats(0, "Starting browser...")
        
    def user_ready(self):
        """User clicked ready button"""
        self.ready_button.config(state="disabled")
        self.user_ready_event.set()
        
    def captcha_solved(self):
        """User solved CAPTCHA"""
        self.captcha_button.config(state="disabled")
        self.captcha_solved_event.set()
        
    def clear_session(self):
        """Clear saved login session"""
        try:
            session_file = self.session_dir / "session.json"
            if session_file.exists():
                session_file.unlink()
                self.log_message("Login session cleared. You'll need to login again next time.")
                messagebox.showinfo("Session Cleared", "Login session has been cleared.\nYou'll need to login again next time.")
            else:
                self.log_message("No saved session to clear.")
                messagebox.showinfo("No Session", "No saved login session found.")
        except Exception as e:
            self.log_message(f"Error clearing session: {e}")
            messagebox.showerror("Error", f"Could not clear session: {e}")
        finally:
            self.update_session_status()
            
    def update_session_status(self):
        """Update the session status display"""
        session_file = self.session_dir / "session.json"
        if session_file.exists():
            try:
                modified_time = session_file.stat().st_mtime
                from datetime import datetime
                modified_date = datetime.fromtimestamp(modified_time).strftime("%Y-%m-%d %H:%M")
                self.session_status_label.config(text=f"Session saved: {modified_date}")
            except Exception:
                self.session_status_label.config(text="Session file exists")
        else:
            self.session_status_label.config(text="No saved session")
    
    def stop_scraping(self):
        """Stop scraping and save results"""
        self.stop_requested = True
        self.log_message("Stop requested - saving current results...")
        self.update_stats(len(self.products), "Stopping...")
        
        # Save current products
        if self.products:
            self.save_products_to_csv()
            
    def reset_ui(self):
        """Reset UI to initial state"""
        self.scraping_active = False
        self.start_button.config(state="normal")
        self.ready_button.config(state="disabled")
        self.captcha_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.progress_bar.stop()
        
    def save_products_to_csv(self):
        """Save products to CSV file"""
        if not self.products:
            self.log_message("No products to save")
            return
            
        try:
            output_path = Path(self.output_file.get())
            fieldnames = list(self.products[0].keys())
            
            with output_path.open("w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.products)
                
            self.log_message(f"Successfully saved {len(self.products)} products to {output_path.name}")
            
        except Exception as e:
            self.log_message(f"Error saving products: {e}")
            messagebox.showerror("Save Error", f"Failed to save products: {e}")
            
    def run_scraper(self):
        """Main scraper thread - integrates original scraper functionality"""
        try:
            # Initialize threading events
            self.user_ready_event = threading.Event()
            self.captcha_solved_event = threading.Event()
            
            with sync_playwright() as p:
                # Setup browser with user configuration
                proxy_config = None
                if self.use_proxy.get() and self.proxy_server.get().strip():
                    proxy_config = {"server": self.proxy_server.get().strip()}
                    
                browser = p.chromium.launch(
                    headless=False,
                    slow_mo=50,
                    proxy=proxy_config
                )
                
                # Create context with or without persistent session
                context_options = {
                    "locale": "en-US",
                    "timezone_id": "America/New_York",
                    "geolocation": {"longitude": -74.0060, "latitude": 40.7128},
                    "permissions": ["geolocation"],
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                    "extra_http_headers": {
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                    }
                }
                
                # Add persistent storage if session saving is enabled
                if self.save_session.get():
                    self.session_dir.mkdir(exist_ok=True)
                    session_file = self.session_dir / "session.json"
                    if session_file.exists():
                        self.log_message(f"Found existing session file: {session_file}")
                        context_options["storage_state"] = str(session_file)
                        self.log_message("Using saved login session...")
                    else:
                        self.log_message("No existing session found - will create new session...")
                else:
                    self.log_message("Using temporary session (not saved)...")
                    
                try:
                    context = browser.new_context(**context_options)
                except Exception as e:
                    # If session file is corrupted, create new context without it
                    self.log_message(f"Session file issue: {e}. Creating fresh session...")
                    if "storage_state" in context_options:
                        del context_options["storage_state"]
                    context = browser.new_context(**context_options)
                
                # Force English language and US locale
                context.add_cookies([
                    {"name": "language", "value": "en", "domain": ".temu.com", "path": "/"},
                    {"name": "locale", "value": "en_US", "domain": ".temu.com", "path": "/"},
                    {"name": "currency", "value": "USD", "domain": ".temu.com", "path": "/"},
                    {"name": "region", "value": "US", "domain": ".temu.com", "path": "/"},
                ])
                
                page = context.new_page()
                page.set_default_timeout(120000)
                stealth_sync(page)
                
                self.context = context
                self.page = page
                
                # Navigate to Temu
                self.log_message("Opening Temu website...")
                self.update_stats(0, "Loading Temu...")
                page.goto("https://www.temu.com/", wait_until="networkidle")
                
                # Verify proxy connection if used
                if proxy_config:
                    try:
                        self.log_message("Verifying proxy connection...")
                        page.goto("https://api.ipify.org?format=json", wait_until="domcontentloaded")
                        ip_data = json.loads(page.inner_text('body'))
                        self.log_message(f"Your public IP is: {ip_data['ip']}")
                        if proxy_config and ip_data['ip'] not in proxy_config['server']:
                            self.log_message("Warning: The public IP does not match the proxy IP.")
                        page.go_back()
                    except Exception as e:
                        self.log_message(f"Could not verify IP address: {e}")
                
                # Wait for user login
                self.log_message("Please log in or solve any CAPTCHA in the browser window")
                self.log_message("Click 'I'm Ready (Continue)' when you're logged in and ready to proceed")
                self.update_stats(0, "Waiting for login...")
                
                # Wait for user to be ready
                self.user_ready_event.wait()
                
                if self.stop_requested:
                    return
                    
                # Warm up
                self.log_message("Warming up...")
                self.update_stats(0, "Warming up...")
                time.sleep(random.uniform(2, 5))
                page.mouse.move(random.randint(100, 800), random.randint(100, 600))
                time.sleep(random.uniform(1, 3))
                page.mouse.wheel(0, -300)
                time.sleep(random.uniform(2, 4))
                
                # Initial search
                response = None
                initial_retries = 0
                max_initial_retries = 4
                
                while initial_retries < max_initial_retries and not self.stop_requested:
                    self.log_message("Performing search and waiting for API response...")
                    self.update_stats(0, "Searching...")
                    
                    try:
                        with page.expect_response("**/api/poppy/v1/search?scene=search", timeout=120000) as response_info:
                            self.log_message("Simulating user typing and clicking search...")
                            search_input = page.locator('#searchInput')
                            search_input.click(delay=random.uniform(100, 250))
                            time.sleep(random.uniform(0.5, 1.5))
                            search_input.press('Control+A')
                            time.sleep(random.uniform(0.2, 0.5))
                            search_input.press('Backspace')
                            time.sleep(random.uniform(0.5, 1.5))
                            search_input.type(self.search_query.get(), delay=random.uniform(80, 200))
                            search_input.press('Enter')
                            time.sleep(random.uniform(4, 7))
                            search_input.press('Enter')
                        
                        response = response_info.value
                        
                        # Show CAPTCHA dialog
                        self.root.after(0, self.show_captcha_dialog)
                        self.captcha_solved_event.wait()
                        
                        if self.stop_requested:
                            return
                            
                        if response.status == 429:
                            wait_time = (2 ** initial_retries) * 60
                            self.log_message(f"429 Error on initial search. Retrying in {wait_time / 60} minutes...")
                            time.sleep(wait_time)
                            initial_retries += 1
                            page.reload()
                            time.sleep(5)
                            continue
                            
                        if response.ok:
                            break
                            
                    except Exception as e:
                        self.log_message(f"An error occurred during initial search: {e}")
                        break
                        
                if not response or not response.ok:
                    self.log_message(f"Initial search failed after multiple retries. Final status: {response.status if response else 'N/A'}")
                    return
                    
                # Process initial results
                self.log_message("Successfully intercepted API response.")
                body = response.body()
                data = json.loads(body)
                products = list(self.extract_products(data))
                
                if not products:
                    self.log_message("API response did not contain any products.")
                    return
                    
                self.products.extend(products)
                self.save_products_to_csv()
                self.update_stats(len(self.products), "Scraping products...")
                
                # Continue scraping with "See more" clicks
                retries = 0
                max_retries = 4
                see_more_count = 0
                
                while not self.stop_requested:
                    try:
                        # Human-like scrolling and interaction
                        time.sleep(random.uniform(8, 15))
                        page.mouse.move(random.randint(100, 800), random.randint(100, 600))
                        time.sleep(random.uniform(1, 3))
                        scroll_amount = random.randint(500, 900)
                        page.mouse.wheel(0, scroll_amount)
                        time.sleep(random.uniform(3, 6))
                        
                        # Find and click "See more" button
                        see_more_button = page.locator('div[class*="_2ugbvrpI"]:has-text("See more")')
                        see_more_button.scroll_into_view_if_needed()
                        
                        with page.expect_response("**/api/poppy/v1/search?scene=search", timeout=120000) as response_info:
                            see_more_button.click(delay=random.uniform(100, 300))
                            
                        response = response_info.value
                        
                        if response.status == 429:
                            if retries < max_retries:
                                wait_time = (2 ** retries) * 60
                                self.log_message(f"429 Error: Too many requests. Retrying in {wait_time / 60} minutes...")
                                time.sleep(wait_time)
                                retries += 1
                                continue
                            else:
                                self.log_message("Max retries reached. Exiting.")
                                break
                                
                        retries = 0
                        
                        if not response.ok:
                            self.log_message(f"API request failed with status {response.status}")
                            break
                            
                        body = response.body()
                        data = json.loads(body)
                        new_products = list(self.extract_products(data))
                        
                        if not new_products:
                            self.log_message("No more products found.")
                            break
                            
                        # Save new products
                        self.products.extend(new_products)
                        self.save_products_to_csv()
                        see_more_count += 1
                        
                        self.log_message(f"Successfully saved {len(new_products)} more products. Total: {len(self.products)}")
                        self.update_stats(len(self.products), "Scraping products...")
                        
                        # Check if cooldown is needed based on user configuration
                        if see_more_count % self.cooldown_frequency.get() == 0:
                            cooldown_min = self.min_interval.get() * 60
                            cooldown_max = self.max_interval.get() * 60
                            wait_duration = random.uniform(cooldown_min, cooldown_max)
                            self.log_message(f"Cooldown triggered after {self.cooldown_frequency.get()} requests. Pausing for {wait_duration / 60:.2f} minutes...")
                            self.update_stats(len(self.products), f"Cooldown: {wait_duration/60:.1f} min...")
                            
                            for i in range(int(wait_duration)):
                                if self.stop_requested:
                                    break
                                time.sleep(1)
                        
                    except Exception as e:
                        self.log_message(f"An error occurred: {e}")
                        break
                
                # Save session before closing context (while it's still active)
                if self.save_session.get() and hasattr(self, 'context') and self.context:
                    try:
                        self.log_message("Attempting to save login session...")
                        self.session_dir.mkdir(exist_ok=True)
                        storage_state = self.context.storage_state()
                        session_file = self.session_dir / "session.json"
                        
                        with open(session_file, "w") as f:
                            json.dump(storage_state, f, indent=2)
                        
                        # Verify the file was created and has content
                        if session_file.exists() and session_file.stat().st_size > 0:
                            self.log_message(f"✓ Login session saved successfully to {session_file}")
                            self.log_message(f"Session file size: {session_file.stat().st_size} bytes")
                            # Update session status in UI
                            self.root.after(0, self.update_session_status)
                        else:
                            self.log_message("⚠ Session file created but appears empty!")
                            
                    except Exception as e:
                        self.log_message(f"✗ Could not save session: {e}")
                        import traceback
                        self.log_message(f"Session save error details: {traceback.format_exc()}")
                else:
                    if not self.save_session.get():
                        self.log_message("Session saving is disabled")
                    elif not hasattr(self, 'context'):
                        self.log_message("No context available for session saving")
                    elif not self.context:
                        self.log_message("Context is None, cannot save session")
                        
        except Exception as e:
            self.log_message(f"Scraper error: {e}")
            messagebox.showerror("Scraper Error", f"An error occurred: {e}")
            
        # The 'with sync_playwright()' block will automatically close context and browser
        # when it exits, so we don't need manual cleanup
                
            self.root.after(0, self.scraping_finished)
            
    def show_captcha_dialog(self):
        """Show CAPTCHA confirmation dialog"""
        self.captcha_button.config(state="normal")
        self.log_message("Search submitted. If there is a CAPTCHA, please solve it now.")
        self.log_message("Click 'CAPTCHA Solved' when ready to continue...")
        self.update_stats(len(self.products), "Waiting for CAPTCHA...")
        
    def scraping_finished(self):
        """Called when scraping is complete"""
        if self.stop_requested:
            self.log_message("Scraping stopped by user.")
            if self.products:
                self.update_stats(len(self.products), "Stopped - results saved")
                messagebox.showinfo("Stopped", f"Scraping stopped!\n{len(self.products)} products saved to {self.output_file.get()}")
            else:
                self.update_stats(0, "Stopped - no products found")
        else:
            self.log_message("Scraping finished!")
            if self.products:
                self.save_products_to_csv()
                self.update_stats(len(self.products), "Completed successfully")
                messagebox.showinfo("Complete", f"Scraping completed!\n{len(self.products)} products saved to {self.output_file.get()}")
            else:
                self.update_stats(0, "No products found")
                
        self.reset_ui()
        
    def extract_products(self, data):
        """Extract products from API response - same logic as original scraper"""
        try:
            goods_list = data["result"]["data"]["goods_list"]
        except (KeyError, TypeError):
            raise ValueError("Unexpected JSON structure: cannot find goods_list")
            
        for item in goods_list:
            price_info = item.get("price_info", {})
            yield {
                "goods_id": item.get("goods_id", ""),
                "title": item.get("title", ""),
                "price_str": price_info.get("price_str", ""),
                "price": price_info.get("price", ""),
                "currency": price_info.get("currency", ""),
                "sales_num": item.get("sales_num", ""),
                "thumb_url": item.get("thumb_url", ""),
                "link_url": item.get("link_url", ""),
            }
            
            
def main():
    """Launch the GUI application"""
    root = tk.Tk()
    app = TemuScraperGUI(root)
    
    def on_closing():
        if app.scraping_active:
            if messagebox.askokcancel("Quit", "Scraping is in progress. Do you want to stop and quit?"):
                app.stop_scraping()
                root.destroy()
        else:
            root.destroy()
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
    
    
if __name__ == "__main__":
    main()
