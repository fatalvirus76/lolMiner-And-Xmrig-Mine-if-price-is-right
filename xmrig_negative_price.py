import requests
import subprocess
import time
from datetime import datetime, timezone, timedelta
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from threading import Thread

# Base API URL
BASE_API_URL = "https://www.elprisetjustnu.se/api/v1/prices/{year}/{month_day}_{region}.json"

class MinerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("xmrig Controller")

        # Initialize variables
        self.program_path = tk.StringVar(value="/home/anonymous/Programs/xmrig-6.21.3/xmrig")
        self.algo = tk.StringVar(value="randomx")
        self.pool = tk.StringVar(value="stratum+tcp://randomxmonero.auto.nicehash.com:9200")
        self.user = tk.StringVar(value="38bj4uu8uDsnC5NjoeGb8TMviBCEtMiaet.CPU0")
        self.threads = tk.StringVar(value="10")
        self.api_worker_id = tk.StringVar(value="")
        self.api_id = tk.StringVar(value="")
        self.http_host = tk.StringVar(value="127.0.0.1")
        self.http_port = tk.StringVar(value="0")  # Default 0 means disabled
        self.http_access_token = tk.StringVar(value="")
        self.http_no_restricted = tk.BooleanVar(value=False)
        self.region = tk.StringVar(value="SE3")
        self.custom_price = tk.StringVar(value="")
        self.start_mining_price = tk.DoubleVar(value=0)  # Default is 0 SEK/kWh
        self.poll_interval = 300  # Poll interval in seconds
        self.program_process = None
        self.polling = False

        # Create GUI widgets
        self.create_widgets()

    def create_widgets(self):
        # GUI Layout
        tk.Label(self.root, text="Path to xmrig:").grid(row=0, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.program_path, width=50).grid(row=0, column=1)
        tk.Button(self.root, text="Browse", command=self.browse_program_path).grid(row=0, column=2)

        tk.Label(self.root, text="Algorithm:").grid(row=1, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.algo).grid(row=1, column=1)

        tk.Label(self.root, text="Pool:").grid(row=2, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.pool, width=50).grid(row=2, column=1, columnspan=2)

        tk.Label(self.root, text="User:").grid(row=3, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.user, width=50).grid(row=3, column=1, columnspan=2)

        tk.Label(self.root, text="Threads:").grid(row=4, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.threads).grid(row=4, column=1)

        tk.Label(self.root, text="Region:").grid(row=5, column=0, sticky="w")
        tk.OptionMenu(self.root, self.region, "SE1", "SE2", "SE3", "SE4").grid(row=5, column=1, sticky="w")

        tk.Label(self.root, text="Custom Price (SEK/kWh):").grid(row=6, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.custom_price).grid(row=6, column=1)

        tk.Label(self.root, text="Start Mining When Price is Under (SEK/kWh):").grid(row=7, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.start_mining_price).grid(row=7, column=1)

        tk.Label(self.root, text="API Worker ID:").grid(row=8, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.api_worker_id).grid(row=8, column=1)

        tk.Label(self.root, text="API Instance ID:").grid(row=9, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.api_id).grid(row=9, column=1)

        tk.Label(self.root, text="HTTP Host:").grid(row=10, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.http_host).grid(row=10, column=1)

        tk.Label(self.root, text="HTTP Port:").grid(row=11, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.http_port).grid(row=11, column=1)

        tk.Label(self.root, text="HTTP Access Token:").grid(row=12, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.http_access_token).grid(row=12, column=1)

        tk.Checkbutton(self.root, text="Enable Full Remote Access", variable=self.http_no_restricted).grid(row=13, column=0, sticky="w")

        tk.Button(self.root, text="Start", command=self.start_polling).grid(row=14, column=0)
        tk.Button(self.root, text="Stop", command=self.stop_polling).grid(row=14, column=1)

        tk.Label(self.root, text="Debug Output:").grid(row=15, column=0, sticky="nw")
        self.debug_output = tk.Text(self.root, height=10, width=80, state="disabled")
        self.debug_output.grid(row=16, column=0, columnspan=3, sticky="w")

    def browse_program_path(self):
        path = filedialog.askopenfilename(title="Select xmrig executable")
        if path:
            self.program_path.set(path)

    def log_debug(self, message):
        self.debug_output.configure(state="normal")
        self.debug_output.insert(tk.END, f"{message}\n")
        self.debug_output.configure(state="disabled")
        self.debug_output.see(tk.END)

    def get_api_url(self):
        now = datetime.now()
        year = now.year
        month_day = now.strftime("%m-%d")
        return BASE_API_URL.format(year=year, month_day=month_day, region=self.region.get())

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

        current_time = datetime.now(timezone.utc) + timedelta(hours=1)
        for price_entry in prices:
            start_time = datetime.fromisoformat(price_entry["time_start"])
            end_time = datetime.fromisoformat(price_entry["time_end"])
            if start_time <= current_time < end_time:
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

    def start_miner(self):
        if self.program_process is not None:
            return
        command = [
            self.program_path.get(),
            "-a", self.algo.get(),
            "-o", self.pool.get(),
            "-u", self.user.get(),
            "--threads", self.threads.get(),
            "--api-worker-id", self.api_worker_id.get(),
            "--api-id", self.api_id.get(),
            "--http-host", self.http_host.get(),
            "--http-port", self.http_port.get(),
            "--http-access-token", self.http_access_token.get()
        ]
        if self.http_no_restricted.get():
            command.append("--http-no-restricted")
        self.program_process = subprocess.Popen(command)
        self.log_debug("xmrig started.")

    def stop_miner(self):
        if self.program_process is not None:
            self.program_process.terminate()
            self.program_process.wait()
            self.program_process = None
            self.log_debug("xmrig stopped.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MinerGUI(root)
    root.mainloop()

