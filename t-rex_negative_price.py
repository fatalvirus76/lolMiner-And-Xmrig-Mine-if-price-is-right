import subprocess
import time
from datetime import datetime, timezone, timedelta
import pytz
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from threading import Thread
import requests  # We will use requests for fetching price data

# Base API URL
BASE_API_URL = "https://www.elprisetjustnu.se/api/v1/prices/{year}/{month_day}_{region}.json"

class MinerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("T-Rex Miner Controller")
        self.root.geometry("850x700")

        # Add a themed style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=6, relief="flat", background="#4472C4", foreground="white")
        style.configure("TLabel", font=("Arial", 10), padding=5)

        self.program_path = tk.StringVar(value="./t-rex")
        self.algo = tk.StringVar(value="kawpow")
        self.pool = tk.StringVar(value="stratum+tcp://kawpow.auto.nicehash.com:9200")
        self.user = tk.StringVar(value="38bj4uu8uDsnC5NjoeGb8TMviBCEtMiaet")
        self.password = tk.StringVar(value="x")
        self.worker = tk.StringVar(value="GPU0")
        self.api_bind = tk.StringVar(value="0.0.0.0:4067")
        self.region = tk.StringVar(value="SE3")
        self.custom_price = tk.StringVar(value="")
        self.start_mining_price = tk.DoubleVar(value=0)
        self.poll_interval = 300
        self.program_process = None
        self.polling = False

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Create rows for each input field
        self.create_row(main_frame, "Path to T-Rex:", self.program_path, row=0, browse=True)
        self.create_row(main_frame, "Algorithm:", self.algo, row=1, dropdown=[
            "autolykos2", "blake3", "etchash", "ethash", "firopow", "kawpow",
            "mtp", "mtp-tcr", "multi", "octopus", "progpow", "progpow-veil",
            "progpow-veriblock", "progpowz", "tensority"
        ])
        self.create_row(main_frame, "Pool:", self.pool, row=2, combobox=True, dropdown=[
            "stratum+tcp://autolykos.auto.nicehash.com:9200",
            "stratum+tcp://alephium.auto.nicehash.com:9200",
            "stratum+tcp://etchash.auto.nicehash.com:9200",
            "stratum+tcp://kawpow.auto.nicehash.com:9200",
            "stratum+tcp://octopus.auto.nicehash.com:9200",
            "stratum+tcp://rvn.2miners.com:6060"
        ])
        self.create_row(main_frame, "User:", self.user, row=3)
        self.create_row(main_frame, "Password:", self.password, row=4, hidden=True)
        self.create_row(main_frame, "Worker Name:", self.worker, row=5)
        self.create_row(main_frame, "API Bind Address:", self.api_bind, row=6)
        self.create_row(main_frame, "Region:", self.region, row=7, dropdown=["SE1", "SE2", "SE3", "SE4"])
        self.create_row(main_frame, "Custom Price (SEK/kWh):", self.custom_price, row=8)
        self.create_row(main_frame, "Start Mining When Price is Under (SEK/kWh):", self.start_mining_price, row=9)

        # Start and Stop buttons
        tk.Button(main_frame, text="Start", command=self.start_polling, bg="#4caf50", fg="#ffffff").grid(row=10, column=0, pady=10)
        tk.Button(main_frame, text="Stop", command=self.stop_polling, bg="#f44336", fg="#ffffff").grid(row=10, column=1, pady=10)

        # Debug Output
        ttk.Label(main_frame, text="Debug Output:").grid(row=11, column=0, sticky="nw")
        self.debug_output = tk.Text(main_frame, height=15, width=85, state="normal", bg="#F0F0F0", fg="black")
        self.debug_output.grid(row=12, column=0, columnspan=3, sticky="w", pady=10)

    def create_row(self, frame, label_text, variable, row, browse=False, combobox=False, dropdown=None, hidden=False):
        ttk.Label(frame, text=label_text).grid(row=row, column=0, sticky="w")
        if combobox:
            widget = ttk.Combobox(frame, textvariable=variable, values=dropdown, width=50)
            widget.grid(row=row, column=1, padx=5)
            widget.set(variable.get())  # Set the default value
        elif browse:
            entry = ttk.Entry(frame, textvariable=variable, width=50)
            entry.grid(row=row, column=1, padx=5)
            ttk.Button(frame, text="Browse", command=lambda: self.browse_program_path()).grid(row=row, column=2, padx=5)
        elif hidden:
            entry = ttk.Entry(frame, textvariable=variable, show="*", width=50)
            entry.grid(row=row, column=1, padx=5)
        else:
            entry = ttk.Entry(frame, textvariable=variable, width=50)
            entry.grid(row=row, column=1, padx=5)

    def browse_program_path(self):
        path = filedialog.askopenfilename(title="Select T-Rex executable")
        if path:
            self.program_path.set(path)

    def log_debug(self, message):
        self.debug_output.configure(state="normal")
        self.debug_output.insert(tk.END, f"{message}\n")
        self.debug_output.configure(state="normal")
        self.debug_output.see(tk.END)

    # Fetch price from the API in the same way as before
    def fetch_prices(self, api_url):
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log_debug(f"Error fetching prices: {e}")
            return []

    def get_current_hour_price(self, prices):
        custom_price = self.custom_price.get()
        if custom_price:
            try:
                return float(custom_price)
            except ValueError:
                self.log_debug("Invalid custom price entered. Using API data instead.")

        sweden_tz = pytz.timezone("Europe/Stockholm")
        current_time_sweden = datetime.now(sweden_tz)

        for price_entry in prices:
            start_time = datetime.fromisoformat(price_entry["time_start"])
            end_time = datetime.fromisoformat(price_entry["time_end"])
            start_time = start_time.astimezone(sweden_tz)
            end_time = end_time.astimezone(sweden_tz)

            if start_time <= current_time_sweden < end_time:
                return price_entry["SEK_per_kWh"]

        return None

    def start_polling(self):
        if self.polling:
            messagebox.showinfo("Info", "Polling is already active.")
            return
        self.polling = True
        Thread(target=self.poll_prices, daemon=True).start()

    def stop_polling(self):
        self.polling = False
        self.stop_miner()
        self.log_debug("Polling stopped.")

    def poll_prices(self):
        while self.polling:
            self.check_and_start_miner()
            time.sleep(self.poll_interval)

    def check_and_start_miner(self):
        api_url = self.get_api_url()
        self.log_debug(f"Fetching prices from: {api_url}")
        prices = self.fetch_prices(api_url)
        if prices or self.custom_price.get():
            current_price = self.get_current_hour_price(prices)
            if current_price is not None:
                self.log_debug(f"Current price: {current_price} SEK/kWh")
                if current_price < self.start_mining_price.get():
                    self.start_miner()
                else:
                    self.stop_miner()
            else:
                self.log_debug("Could not find price for the current hour.")
        else:
            self.log_debug("Failed to fetch price data.")

    def get_api_url(self):
        sweden_tz = pytz.timezone("Europe/Stockholm")
        current_time_sweden = datetime.now(sweden_tz)
        year = current_time_sweden.year
        month_day = current_time_sweden.strftime("%m-%d")
        return BASE_API_URL.format(year=year, month_day=month_day, region=self.region.get())

    def start_miner(self):
        if self.program_process and self.program_process.poll() is None:
            self.log_debug("Miner is already running.")
            return

        command = [
            self.program_path.get(),
            "-a", self.algo.get(),
            "-o", self.pool.get(),
            "-u", self.user.get(),
            "-p", self.password.get(),
            "-w", self.worker.get(),
            "--api-bind-http", self.api_bind.get()
        ]
        try:
            self.program_process = subprocess.Popen(command)
            self.log_debug(f"Miner started with command: {' '.join(command)}")
        except Exception as e:
            self.log_debug(f"Failed to start miner: {e}")

    def stop_miner(self):
        if self.program_process and self.program_process.poll() is None:
            self.program_process.terminate()
            self.program_process.wait()
            self.program_process = None
            self.log_debug("Miner stopped.")
        else:
            self.log_debug("Miner is not running.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MinerGUI(root)
    root.mainloop()
