import requests
import subprocess
import time
from datetime import datetime, timezone, timedelta
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog, ttk
from threading import Thread

BASE_API_URL = "https://www.elprisetjustnu.se/api/v1/prices/{year}/{month_day}_{region}.json"

class MinerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Miner Controller")
        self.root.geometry("800x600")
        self.root.configure(bg="#2d2d2d")

        self.program_path = tk.StringVar(value="./miner")
        self.algo = tk.StringVar(value="kawpow")
        self.server = tk.StringVar(value="kawpow.auto.nicehash.com:9200")
        self.user = tk.StringVar(value="38bj4uu8uDsnC5NjoeGb8TMviBCEtMiaet")
        self.password = tk.StringVar(value="")
        self.api_bind = tk.StringVar(value="0.0.0.0:4067")
        self.region = tk.StringVar(value="SE3")
        self.start_mining_price = tk.DoubleVar(value=0)
        self.poll_interval = 300
        self.program_process = None
        self.polling = False

        self.algorithms = [
            "zil", "vds", "equihash144_5", "equihash125_4", "beamhash", "equihash210_9",
            "cuckoo29", "cuckatoo32", "eth", "etc", "cortex", "kawpow", "sero", "firo",
            "autolykos2", "octopus", "kheavyhash", "ethash+kheavyhash", "ethash+sha512_256d",
            "ethash+ironfish", "etchash+kheavyhash", "etchash+sha512_256d", "etchash+ironfish",
            "octopus+kheavyhash", "octopus+sha512_256d", "octopus+ironfish",
            "autolykos2+kheavyhash", "autolykos2+sha512_256d", "sha512_256d", "ironfish", "karlsenhash"
        ]

        self.create_widgets()

    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        main_tab = ttk.Frame(notebook)
        api_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Main")
        notebook.add(api_tab, text="API")
        notebook.pack(expand=True, fill="both")

        # Main Tab Widgets
        tk.Label(main_tab, text="Path to Miner:", fg="#ffffff", bg="#2d2d2d").grid(row=0, column=0, sticky="w")
        tk.Entry(main_tab, textvariable=self.program_path, width=50).grid(row=0, column=1)
        tk.Button(main_tab, text="Browse", command=self.browse_program_path, bg="#4caf50", fg="#ffffff").grid(row=0, column=2)

        tk.Label(main_tab, text="Algorithm:", fg="#ffffff", bg="#2d2d2d").grid(row=1, column=0, sticky="w")
        tk.OptionMenu(main_tab, self.algo, *self.algorithms).grid(row=1, column=1, sticky="w")

        self.create_entry(main_tab, "Server:", self.server, 2)
        self.create_entry(main_tab, "User:", self.user, 4)
        self.create_entry(main_tab, "Password:", self.password, 5)

        tk.Label(main_tab, text="Region:", fg="#ffffff", bg="#2d2d2d").grid(row=6, column=0, sticky="w")
        tk.OptionMenu(main_tab, self.region, "SE1", "SE2", "SE3", "SE4").grid(row=6, column=1, sticky="w")

        tk.Label(main_tab, text="Start Mining When Price is Under (SEK/kWh):", fg="#ffffff", bg="#2d2d2d").grid(row=7, column=0, sticky="w")
        tk.Entry(main_tab, textvariable=self.start_mining_price).grid(row=7, column=1)

        tk.Button(main_tab, text="Start", command=self.start_polling, bg="#4caf50", fg="#ffffff").grid(row=8, column=0)
        tk.Button(main_tab, text="Stop", command=self.stop_polling, bg="#f44336", fg="#ffffff").grid(row=8, column=1)

        tk.Label(main_tab, text="Debug Output:", fg="#ffffff", bg="#2d2d2d").grid(row=9, column=0, sticky="nw")
        self.debug_output = tk.Text(main_tab, height=10, width=80, state="disabled", bg="#1e1e1e", fg="#ffffff")
        self.debug_output.grid(row=10, column=0, columnspan=3, sticky="w")

        # API Tab Widgets
        self.create_entry(api_tab, "API (ip:port):", self.api_bind, 0)

    def create_entry(self, parent, label, variable, row, validate=None):
        tk.Label(parent, text=label, fg="#ffffff", bg="#2d2d2d").grid(row=row, column=0, sticky="w")
        tk.Entry(parent, textvariable=variable, validate="key", validatecommand=validate).grid(row=row, column=1)

    def browse_program_path(self):
        path = filedialog.askopenfilename(title="Select Miner executable")
        if path:
            self.program_path.set(path)

    def log_debug(self, message):
        self.debug_output.configure(state="normal")
        self.debug_output.insert(tk.END, f"{message}\n")
        self.debug_output.configure(state="disabled")
        self.debug_output.see(tk.END)

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
        if prices:
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

    def fetch_prices(self, api_url):
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log_debug(f"Error fetching prices: {e}")
            return []

    def get_current_hour_price(self, prices):
        current_time = datetime.now(timezone.utc) + timedelta(hours=1)
        for price_entry in prices:
            start_time = datetime.fromisoformat(price_entry["time_start"])
            end_time = datetime.fromisoformat(price_entry["time_end"])
            if start_time <= current_time < end_time:
                return price_entry.get("SEK_per_kWh", None)
        return None

    def get_api_url(self):
        now = datetime.now()
        year = now.year
        month_day = now.strftime("%m-%d")
        return BASE_API_URL.format(year=year, month_day=month_day, region=self.region.get())

    def start_miner(self):
        if self.program_process and self.program_process.poll() is None:
            self.log_debug("Miner is already running.")
            return

        command = [
            self.program_path.get(),
            "-a", self.algo.get(),
            "-s", self.server.get(),
            "-u", self.user.get(),
            "--api", self.api_bind.get()
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

