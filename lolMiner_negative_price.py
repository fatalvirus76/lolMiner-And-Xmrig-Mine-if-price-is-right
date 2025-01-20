import requests
import subprocess
import subprocess
import time
from datetime import datetime, timezone, timedelta
import pytz
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from threading import Thread

# Base API URL
BASE_API_URL = "https://www.elprisetjustnu.se/api/v1/prices/{year}/{month_day}_{region}.json"

class MinerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("lolMiner Controller")
        self.root.geometry("800x640")

        # Add a themed style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=6, relief="flat", background="#4472C4", foreground="white")
        style.configure("TLabel", font=("Arial", 10), padding=5)

        self.program_path = tk.StringVar(value="./lolMiner")
        self.algo = tk.StringVar(value="ETCHASH")
        self.pool = tk.StringVar(value="stratum+tcp://etchash.auto.nicehash.com:9200")
        self.user = tk.StringVar(value="38bj4uu8uDsnC5NjoeGb8TMviBCEtMiaet.GPU0")
        self.api_port = tk.StringVar(value="4069")
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

        ttk.Label(main_frame, text="Path to lolMiner:").grid(row=0, column=0, sticky="w")
        path_entry = ttk.Entry(main_frame, textvariable=self.program_path, width=50)
        path_entry.grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_program_path).grid(row=0, column=2, padx=5)

        ttk.Label(main_frame, text="Algorithm:").grid(row=1, column=0, sticky="w")
        algo_dropdown = ttk.Combobox(
            main_frame,
            textvariable=self.algo,
            values=[
                "ALEPH", "AUTOLYKOS2", "BEAM-III", "C29AE", "C30CTX", "C31",
                "C32", "CR29-32", "CR29-40", "EQUI144_5", "EQUI144_5_EXCC",
                "EQUI192_7", "EQUI210_9", "ETCHASH", "ETHASH", "ETHASHB3",
                "FISHHASH", "FLUX", "GRAM", "IRONFISH", "KARLSEN", "NEXA",
                "PYRIN", "RADIANT", "UBQHASH"
            ],
            width=47
        )
        algo_dropdown.grid(row=1, column=1, padx=5)
        algo_dropdown.set("ETCHASH")  # Set a default value if needed

        ttk.Label(main_frame, text="Pool:").grid(row=2, column=0, sticky="w")
        pool_entry = ttk.Entry(main_frame, textvariable=self.pool, width=50)
        pool_entry.grid(row=2, column=1, padx=5)

        ttk.Label(main_frame, text="User:").grid(row=3, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.user, width=50).grid(row=3, column=1, padx=5)

        ttk.Label(main_frame, text="API Port:").grid(row=4, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.api_port, width=50).grid(row=4, column=1, padx=5)

        ttk.Label(main_frame, text="Region:").grid(row=5, column=0, sticky="w")
        ttk.OptionMenu(main_frame, self.region, self.region.get(), "SE1", "SE2", "SE3", "SE4").grid(row=5, column=1, sticky="w", padx=5)

        ttk.Label(main_frame, text="Custom Price (SEK/kWh):").grid(row=6, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.custom_price, width=50).grid(row=6, column=1, padx=5)

        ttk.Label(main_frame, text="Start Mining When Price is Under (SEK/kWh):").grid(row=7, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.start_mining_price, width=50).grid(row=7, column=1, padx=5)

        tk.Button(main_frame, text="Start", command=self.start_polling, bg="#4caf50", fg="#ffffff").grid(row=8, column=0, pady=10)
        tk.Button(main_frame, text="Stop", command=self.stop_polling, bg="#f44336", fg="#ffffff").grid(row=8, column=1, pady=10)

        ttk.Label(main_frame, text="Debug Output:").grid(row=9, column=0, sticky="nw")
        self.debug_output = tk.Text(main_frame, height=15, width=85, state="normal", bg="#F0F0F0", fg="black")
        self.debug_output.grid(row=10, column=0, columnspan=3, sticky="w", pady=10)

    def browse_program_path(self):
        path = filedialog.askopenfilename(title="Select lolMiner executable")
        if path:
            self.program_path.set(path)

    def log_debug(self, message):
        self.debug_output.configure(state="normal")
        self.debug_output.insert(tk.END, f"{message}\n")
        self.debug_output.configure(state="normal")
        self.debug_output.see(tk.END)

    # ... Rest of the existing methods remain unchanged ...

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
            "--algo", self.algo.get(),
            "--pool", self.pool.get(),
            "--user", self.user.get(),
            "--apiport", self.api_port.get()
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
