import requests
import subprocess
import time
from datetime import datetime
import pytz
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from threading import Thread

BASE_API_URL = "https://www.elprisetjustnu.se/api/v1/prices/{year}/{month_day}_{region}.json"

class MinerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GMiner Controller")
        self.root.geometry("900x700")
        self.root.configure(bg="#2d2d2d")

        # Skapa menyrad
        self.create_menu()

        # Tkinter-stil
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#2d2d2d")
        style.configure("TLabel", background="#2d2d2d", foreground="#ffffff", font=("Arial", 10), padding=5)
        style.configure("TButton", padding=6, relief="flat", background="#4472C4", foreground="white", font=("Arial", 10, "bold"))
        style.map("TButton", background=[("active", "#0052cc")])



        # Init-variabler
        self.program_path = tk.StringVar(value="./miner")
        self.algo = tk.StringVar(value="kawpow")
        self.server = tk.StringVar(value="kawpow.auto.nicehash.com:9200")
        self.user = tk.StringVar(value="38bj4uu8uDsnC5NjoeGb8TMviBCEtMiaet")
        self.password = tk.StringVar(value="")
        self.api_bind = tk.StringVar(value="0.0.0.0:4067")
        self.region = tk.StringVar(value="SE3")
        self.custom_price = tk.StringVar(value="")
        self.start_mining_price = tk.DoubleVar(value=0)
        self.poll_interval = 300
        self.program_process = None
        self.polling = False

        # Lista över tillgängliga algoritmer
        self.algorithms = [
            "zil", "vds", "equihash144_5", "equihash125_4", "beamhash", "equihash210_9",
            "cuckoo29", "cuckatoo32", "eth", "etc", "cortex", "kawpow", "sero", "firo",
            "autolykos2", "octopus", "kheavyhash", "ethash+kheavyhash", "ethash+sha512_256d",
            "ethash+ironfish", "etchash+kheavyhash", "etchash+sha512_256d", "etchash+ironfish",
            "octopus+kheavyhash", "octopus+sha512_256d", "octopus+ironfish",
            "autolykos2+kheavyhash", "autolykos2+sha512_256d", "sha512_256d", "ironfish", "karlsenhash"
        ]

        # Variabel för att visa aktuellt elpris (i stor etikett)
        self.current_price_text = tk.StringVar(value="N/A")

        # Skapa GUI
        self.create_widgets()

    def create_menu(self):
        """Skapar en enkel menyrad (Arkiv -> Avsluta)."""
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Avsluta", command=self.root.quit)
        menubar.add_cascade(label="Arkiv", menu=file_menu)
        self.root.config(menu=menubar)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Gör att fönstret kan expandera
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 1) Stor rubrik
        title_label = ttk.Label(
            main_frame,
            text="GMiner Controller",
            font=("Arial", 16, "bold"),
            foreground="#FFD700"  # Valfri färg på texten, guld t.ex.
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15), sticky="w")

        # 2) Stor etikett för nuvarande elpris
        self.current_price_label = tk.Label(
            main_frame,
            textvariable=self.current_price_text,
            font=("Arial", 14, "bold"),
            width=25,
            bg="#808080",  # utgångsläge (grå)
            fg="#ffffff",
            relief="groove",
            bd=2
        )
        self.current_price_label.grid(row=1, column=0, columnspan=3, pady=(0, 15))

        row_index = 2

        ttk.Label(main_frame, text="Path to GMiner:").grid(row=row_index, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.program_path, width=40).grid(row=row_index, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_program_path).grid(row=row_index, column=2, padx=5)
        row_index += 1

        ttk.Label(main_frame, text="Algorithm:").grid(row=row_index, column=0, sticky="w")
        algo_menu = ttk.OptionMenu(main_frame, self.algo, self.algo.get(), *self.algorithms)
        algo_menu.configure(width=30)
        algo_menu.grid(row=row_index, column=1, padx=5, sticky="w")
        row_index += 1

        ttk.Label(main_frame, text="Server:").grid(row=row_index, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.server, width=40).grid(row=row_index, column=1, padx=5, sticky="w")
        row_index += 1

        ttk.Label(main_frame, text="User:").grid(row=row_index, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.user, width=40).grid(row=row_index, column=1, padx=5, sticky="w")
        row_index += 1

        ttk.Label(main_frame, text="Password:").grid(row=row_index, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.password, width=40).grid(row=row_index, column=1, padx=5, sticky="w")
        row_index += 1

        ttk.Label(main_frame, text="Region:").grid(row=row_index, column=0, sticky="w")
        ttk.OptionMenu(main_frame, self.region, self.region.get(), "SE1", "SE2", "SE3", "SE4").grid(row=row_index, column=1, padx=5, sticky="w")
        row_index += 1

        ttk.Label(main_frame, text="Custom Price (SEK/kWh):").grid(row=row_index, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.custom_price, width=15).grid(row=row_index, column=1, padx=5, sticky="w")
        row_index += 1

        ttk.Label(main_frame, text="Start Mining Price (SEK/kWh):").grid(row=row_index, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.start_mining_price, width=15).grid(row=row_index, column=1, padx=5, sticky="w")
        row_index += 1

        ttk.Label(main_frame, text="API Bind:").grid(row=row_index, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.api_bind, width=20).grid(row=row_index, column=1, padx=5, sticky="w")
        row_index += 1

        # Knappar för start/stopp
        tk.Button(main_frame, text="Start", command=self.start_polling, bg="#4caf50", fg="#ffffff").grid(row=row_index, column=0, pady=10)
        tk.Button(main_frame, text="Stop", command=self.stop_polling, bg="#f44336", fg="#ffffff").grid(row=row_index, column=1, pady=10)
        row_index += 1

        # Debug Output
        ttk.Label(main_frame, text="Debug Output:").grid(row=row_index, column=0, sticky="nw")
        row_index += 1

        self.debug_output = tk.Text(main_frame, height=10, width=70, state="normal", bg="#F0F0F0", fg="black")
        self.debug_output.grid(row=row_index, column=0, columnspan=3, sticky="w", pady=10)

    def create_row(self, *args, **kwargs):
        """(Valfritt) Hjälpfunktion om du vill bygga rader. Ej används just nu."""
        pass

    def browse_program_path(self):
        path = filedialog.askopenfilename(title="Select GMiner executable")
        if path:
            self.program_path.set(path)

    def log_debug(self, message):
        self.debug_output.configure(state="normal")
        self.debug_output.insert(tk.END, f"{message}\n")
        self.debug_output.configure(state="normal")
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

        sweden_tz = pytz.timezone("Europe/Stockholm")
        current_time_sweden = datetime.now(sweden_tz)

        for price_entry in prices:
            start_time = datetime.fromisoformat(price_entry["time_start"]).astimezone(sweden_tz)
            end_time = datetime.fromisoformat(price_entry["time_end"]).astimezone(sweden_tz)
            if start_time <= current_time_sweden < end_time:
                return price_entry.get("SEK_per_kWh", None)
        return None

    def check_and_start_miner(self):
        api_url = self.get_api_url()
        self.log_debug(f"Fetching prices from: {api_url}")
        prices = self.fetch_prices(api_url)
        if prices or self.custom_price.get():
            current_price = self.get_current_hour_price(prices)
            if current_price is not None:
                self.log_debug(f"Current price: {current_price} SEK/kWh")
                # Uppdatera stor etikett
                self.update_current_price_label(current_price)

                if current_price < self.start_mining_price.get():
                    self.start_miner()
                else:
                    self.stop_miner()
            else:
                self.log_debug("No price found for the current hour.")
                self.update_current_price_label(None)
        else:
            self.log_debug("Failed to fetch price data.")
            self.update_current_price_label(None)

    def update_current_price_label(self, current_price):
        """Uppdaterar den stora etiketten med aktuellt elpris, samt färgkod."""
        if current_price is None:
            self.current_price_text.set("N/A")
            self.current_price_label.configure(bg="#808080")  # Grå
            return

        self.current_price_text.set(f"{current_price:.2f} SEK/kWh")

        if current_price < self.start_mining_price.get():
            # Grön bakgrund om under tröskel
            self.current_price_label.configure(bg="#77dd77")
        else:
            # Röd bakgrund om över tröskel
            self.current_price_label.configure(bg="#FF6961")

    def start_miner(self):
        if self.program_process:
            self.log_debug("Miner is already running.")
            return
        command = [
            self.program_path.get(),
            "-a", self.algo.get(),
            "-s", self.server.get(),
            "-u", self.user.get(),
            "--api", self.api_bind.get()
        ]
        # Lägg till lösenord om ifyllt
        if self.password.get():
            command += ["-p", self.password.get()]

        try:
            self.program_process = subprocess.Popen(command)
            self.log_debug(f"GMiner started with command: {' '.join(command)}")
        except Exception as e:
            self.log_debug(f"Failed to start miner: {e}")

    def stop_miner(self):
        if self.program_process:
            self.program_process.terminate()
            self.program_process.wait()
            self.program_process = None
            self.log_debug("GMiner stopped.")
        else:
            self.log_debug("Miner is not running.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MinerGUI(root)
    root.mainloop()
