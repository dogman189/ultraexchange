import customtkinter as ctk
import threading
import json
import ssl
import urllib.parse
import urllib.request
import certifi
import time
import statistics
import os
from collections import deque

# --- LIQUID GLASS / FROST THEME ---
# Faking glassmorphism using deep backgrounds and elevated, thinly bordered panels
COLORS = {
    "bg": "#0B0F19",             # Deep abyss blue/black
    "glass_panel": "#141C2F",    # "Frosted" panel color
    "glass_highlight": "#263553",# Specular highlight border
    "text_main": "#F8FAFC",      # Ice white
    "text_dim": "#64748B",       # Muted slate
    "accent_primary": "#38BDF8", # Liquid cyan/blue
    "accent_glow": "#7DD3FC",    # Lighter blue for pulsing
    "success": "#10B981",        # Emerald
    "danger": "#F43F5E",         # Rose
}

UI_FONT_BOLD = ("SF Pro Display", 15, "bold")
UI_FONT_REGULAR = ("SF Pro Text", 13)
UI_FONT_LARGE = ("SF Pro Display", 44, "bold")
LOG_FONT = ("SF Mono", 11)

ctk.set_appearance_mode("Dark")

class TradingBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ultraexchange")
        self.geometry("1150x750")
        self.configure(fg_color=COLORS["bg"])

        self.is_running = False
        self.active_api_key = ""
        self.symbol = "BTC"
        self.window_size = 20
        self.price_history = deque(maxlen=self.window_size)
        self.portfolio = {"USD": 10000.00, "holdings": {}}
        
        # Animation variables
        self.pulse_state = 0
        self.pulse_direction = 1
        
        self.setup_ui()
        self.load_config()
        self.animate_pulse() # Start the subtle background animation loop

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR (Glass Panel) ---
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=20, 
                                    fg_color=COLORS["glass_panel"], 
                                    border_width=1, border_color=COLORS["glass_highlight"])
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="ultraexchange", font=("SF Pro Display", 26, "bold"), text_color=COLORS["text_main"])
        self.logo_label.pack(pady=(35, 5), padx=20)
       
        # Input Grouping
        self.create_sidebar_input("API KEY", "entry_api_key", "", is_password=True)
        self.create_sidebar_input("SYMBOL", "entry_symbol", "BTC")
        self.create_sidebar_input("INTERVAL (S)", "entry_interval", "300")
        self.create_sidebar_input("TRADE AMT ($)", "entry_trade", "500")
        self.create_sidebar_input("WALLET ($)", "entry_usd", "10000")

        # Buttons with softer, rounded aesthetics
        self.btn_start = ctk.CTkButton(self.sidebar, text="Initialize Sync", 
                                       fg_color=COLORS["accent_primary"], text_color="#000000", 
                                       hover_color=COLORS["accent_glow"], font=UI_FONT_BOLD, 
                                       height=45, corner_radius=25, command=self.start_bot)
        self.btn_start.pack(pady=(40, 10), padx=25, fill="x")
        
        self.btn_stop = ctk.CTkButton(self.sidebar, text="Terminate", 
                                      fg_color="transparent", border_width=1, border_color=COLORS["danger"],
                                      text_color=COLORS["danger"], hover_color="#2A0B14", font=UI_FONT_BOLD, 
                                      height=45, corner_radius=25, command=self.stop_bot, state="disabled")
        self.btn_stop.pack(pady=10, padx=25, fill="x")

        # --- MAIN PANEL ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.main_container.grid_columnconfigure((0, 1), weight=1)

        # Market Analysis Card (Glass Panel)
        self.market_card = ctk.CTkFrame(self.main_container, fg_color=COLORS["glass_panel"], 
                                        border_width=1, border_color=COLORS["glass_highlight"], corner_radius=20)
        self.market_card.grid(row=0, column=0, padx=10, pady=(0, 10), sticky="nsew")
        ctk.CTkLabel(self.market_card, text="Market Index", font=UI_FONT_REGULAR, text_color=COLORS["text_dim"]).pack(pady=(25, 5))
        
        self.price_val = ctk.CTkLabel(self.market_card, text="$0.00", font=UI_FONT_LARGE, text_color=COLORS["text_main"])
        self.price_val.pack(pady=10)
        
        stats_frame = ctk.CTkFrame(self.market_card, fg_color="transparent")
        stats_frame.pack(pady=(0, 25))
        self.sma_val = ctk.CTkLabel(stats_frame, text="SMA: --", font=UI_FONT_REGULAR, text_color=COLORS["text_dim"])
        self.sma_val.pack()
        self.upper_val = ctk.CTkLabel(stats_frame, text="UPPER: --", font=UI_FONT_REGULAR, text_color=COLORS["text_dim"])
        self.upper_val.pack()
        self.lower_val = ctk.CTkLabel(stats_frame, text="LOWER: --", font=UI_FONT_REGULAR, text_color=COLORS["text_dim"])
        self.lower_val.pack()

        # Portfolio Card (Glass Panel)
        self.port_card = ctk.CTkFrame(self.main_container, fg_color=COLORS["glass_panel"], 
                                      border_width=1, border_color=COLORS["glass_highlight"], corner_radius=20)
        self.port_card.grid(row=0, column=1, padx=10, pady=(0, 10), sticky="nsew")
        ctk.CTkLabel(self.port_card, text="Available Liquidity", font=UI_FONT_REGULAR, text_color=COLORS["text_dim"]).pack(pady=(25, 5))
        
        self.usd_val = ctk.CTkLabel(self.port_card, text="$0.00", font=("SF Pro Display", 28, "bold"), text_color=COLORS["text_main"])
        self.usd_val.pack(pady=10)
        
        self.crypto_val = ctk.CTkLabel(self.port_card, text="0.000000 UNITS", font=("SF Pro Display", 16), text_color=COLORS["accent_primary"])
        self.crypto_val.pack(pady=5)
        
        self.status_val = ctk.CTkLabel(self.port_card, text="● Suspended", font=("SF Pro Text", 12), text_color=COLORS["text_dim"])
        self.status_val.pack(side="bottom", pady=25)

        # Log Terminal (Clean look)
        self.textbox = ctk.CTkTextbox(self.main_container, fg_color=COLORS["bg"], text_color=COLORS["text_dim"], 
                                      font=LOG_FONT, corner_radius=20, border_width=1, border_color=COLORS["glass_highlight"])
        self.textbox.grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="nsew")
        self.main_container.grid_rowconfigure(1, weight=1)

    def create_sidebar_input(self, label, attr, default, is_password=False):
        lbl = ctk.CTkLabel(self.sidebar, text=label, font=("SF Pro Text", 10, "bold"), text_color=COLORS["text_dim"])
        lbl.pack(pady=(12, 0), padx=25, anchor="w")
        entry = ctk.CTkEntry(self.sidebar, placeholder_text=default, show="*" if is_password else "",
                             fg_color=COLORS["bg"], border_color=COLORS["glass_highlight"], 
                             text_color=COLORS["text_main"], font=UI_FONT_REGULAR, height=38, corner_radius=8)
        entry.insert(0, default)
        entry.pack(pady=(2, 5), padx=25, fill="x")
        setattr(self, attr, entry)

    # --- CONFIG PERSISTENCE ---
    def load_config(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
                    if "api_key" in config:
                        self.entry_api_key.delete(0, "end")
                        self.entry_api_key.insert(0, config["api_key"])
            except Exception:
                self.log("System: Failed to load config block.")

    def save_config(self):
        key = self.entry_api_key.get().strip()
        if key:
            try:
                with open("config.json", "w") as f:
                    json.dump({"api_key": key}, f)
            except Exception:
                self.log("System: Config block save rejected.")

    # --- ANIMATION ENGINE ---
    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb):
        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def animate_pulse(self):
        """Creates a smooth breathing/pulsing animation for the status dot when active."""
        if self.is_running:
            # Interpolate between success green and a slightly dimmer green
            c1 = self.hex_to_rgb(COLORS["success"])
            c2 = self.hex_to_rgb("#064E3B") # Dark emerald
            
            # Simple sine-wave-like oscillation
            self.pulse_state += 0.05 * self.pulse_direction
            if self.pulse_state >= 1.0:
                self.pulse_state = 1.0
                self.pulse_direction = -1
            elif self.pulse_state <= 0.0:
                self.pulse_state = 0.0
                self.pulse_direction = 1
                
            r = c1[0] * self.pulse_state + c2[0] * (1 - self.pulse_state)
            g = c1[1] * self.pulse_state + c2[1] * (1 - self.pulse_state)
            b = c1[2] * self.pulse_state + c2[2] * (1 - self.pulse_state)
            
            current_color = self.rgb_to_hex((r, g, b))
            self.status_val.configure(text_color=current_color)
        
        # Schedule the next frame in 50ms (approx 20fps, safe for Tkinter)
        self.after(50, self.animate_pulse)

    # --- LOGIC ---
    def log(self, message):
        timestamp = time.strftime('%H:%M:%S')
        self.textbox.insert("end", f"[{timestamp}]  {message}\n")
        self.textbox.see("end")

    def fetch_price(self, symbol):
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        params = urllib.parse.urlencode({"symbol": symbol, "convert": "USD"})
        request = urllib.request.Request(f"{url}?{params}", headers={"X-CMC_PRO_API_KEY": self.active_api_key})
        context = ssl.create_default_context(cafile=certifi.where())
        try:
            with urllib.request.urlopen(request, context=context) as response:
                data = json.load(response)
                return data["data"][symbol]["quote"]["USD"]["price"]
        except:
            self.log("Error: Invalid API token or connection refused.")
            self.stop_bot()
            return None

    def start_bot(self):
        key = self.entry_api_key.get().strip()
        if not key: return
        
        self.save_config()
        self.active_api_key = key
        self.is_running = True
        self.symbol = self.entry_symbol.get().upper()
        self.interval = int(self.entry_interval.get())
        self.trade_amt = float(self.entry_trade.get())
        self.portfolio["USD"] = float(self.entry_usd.get())
        
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_val.configure(text="● Synchronizing")
        self.log(f"System: Data stream initialized for {self.symbol}")
        
        threading.Thread(target=self.bot_loop, daemon=True).start()

    def stop_bot(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status_val.configure(text="● Suspended", text_color=COLORS["text_dim"])
        self.log("System: Data stream terminated.")

    def bot_loop(self):
        while self.is_running:
            price = self.fetch_price(self.symbol)
            if price:
                self.price_history.append(price)
                self.price_val.configure(text=f"${price:,.2f}")
                
                if len(self.price_history) >= self.window_size:
                    sma = statistics.mean(self.price_history)
                    std = statistics.stdev(self.price_history)
                    upper, lower = sma + (std * 2), sma - (std * 2)
                    
                    self.sma_val.configure(text=f"SMA: ${sma:,.2f}")
                    self.upper_val.configure(text=f"UPPER: ${upper:,.2f}")
                    self.lower_val.configure(text=f"LOWER: ${lower:,.2f}")
                    
                    if price <= lower: self.execute_trade("BUY", price)
                    elif price >= upper: self.execute_trade("SELL", price)
            
            self.usd_val.configure(text=f"${self.portfolio['USD']:,.2f}")
            self.crypto_val.configure(text=f"{self.portfolio['holdings'].get(self.symbol, 0):.6f} {self.symbol}")
            
            for _ in range(self.interval):
                if not self.is_running: break
                time.sleep(1)

    def execute_trade(self, side, price):
        if side == "BUY" and self.portfolio["USD"] >= self.trade_amt:
            bought = self.trade_amt / price
            self.portfolio["USD"] -= self.trade_amt
            self.portfolio["holdings"][self.symbol] = self.portfolio["holdings"].get(self.symbol, 0) + bought
            self.log(f"Execution: Filled BUY {bought:.4f} {self.symbol}")
        elif side == "SELL":
            owned = self.portfolio["holdings"].get(self.symbol, 0)
            if owned > 0:
                self.portfolio["USD"] += (owned * price)
                self.portfolio["holdings"][self.symbol] = 0
                self.log(f"Execution: Filled SELL {self.symbol} position")

if __name__ == "__main__":
    app = TradingBotGUI()
    app.mainloop()