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
        self.root.title("XMRig Controller")
        self.root.geometry("750x750")

        # Sätt upp en anpassad stil
        style = ttk.Style()
        # Du kan experimentera med olika teman, t.ex. "clam", "alt", "default", "classic"
        style.theme_use("clam")
        
        style.configure("TFrame", background="#2d2d2d")
        style.configure("TLabel", background="#2d2d2d", foreground="#ffffff", font=("Arial", 10), padding=5)
        style.configure("TButton", padding=6, relief="flat", background="#4472C4", foreground="white", font=("Arial", 10, "bold"))
        style.map("TButton", background=[("active", "#0052cc")])
        # Variabler
        self.program_path = tk.StringVar(value="./xmrig")
        self.algo = tk.StringVar(value="randomx")
        self.pool = tk.StringVar(value="stratum+tcp://randomxmonero.auto.nicehash.com:9200")
        self.user = tk.StringVar(value="38bj4uu8uDsnC5NjoeGb8TMviBCEtMiaet.CPU1")
        self.threads = tk.StringVar(value="6")
        self.region = tk.StringVar(value="SE3")
        self.custom_price = tk.StringVar(value="")
        self.start_mining_price = tk.DoubleVar(value=0)
        self.api_host = tk.StringVar(value="0.0.0.0")
        self.api_port = tk.StringVar(value="4444")
        self.poll_interval = 300
        self.program_process = None
        self.polling = False

        # Label-variabel för att visa nuvarande elpris i stort format
        self.current_price_text = tk.StringVar(value="Ej tillgängligt")
        
        self.create_menu()
        self.create_widgets()

    def create_menu(self):
        """Skapar en enkel menyrad (valfritt)"""
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Avsluta", command=self.root.quit)
        menubar.add_cascade(label="Arkiv", menu=file_menu)
        
        self.root.config(menu=menubar)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # En stor rubrik upptill
        title_label = ttk.Label(
            main_frame, 
            text="XMRig Kontroller",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0,10))

        # Nuvarande elpris i stor text med färg
        self.current_price_label = tk.Label(
            main_frame,
            textvariable=self.current_price_text,
            font=("Arial", 14, "bold"),
            width=20,
            relief="groove",
            bd=2
        )
        self.current_price_label.grid(row=1, column=0, columnspan=3, pady=(0, 15))

        # ----- Rad 2, 3, 4, etc: inställningar ----- #
        ttk.Label(main_frame, text="Path to XMRig:").grid(row=2, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.program_path, width=40).grid(row=2, column=1, padx=5, pady=3)
        ttk.Button(main_frame, text="Browse", command=self.browse_program_path).grid(row=2, column=2, padx=5, pady=3)

        ttk.Label(main_frame, text="Algorithm:").grid(row=3, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.algo, width=30).grid(row=3, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(main_frame, text="Pool:").grid(row=4, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.pool, width=40).grid(row=4, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(main_frame, text="User:").grid(row=5, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.user, width=40).grid(row=5, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(main_frame, text="Threads:").grid(row=6, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.threads, width=10).grid(row=6, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(main_frame, text="Region:").grid(row=7, column=0, sticky="w")
        ttk.OptionMenu(main_frame, self.region, self.region.get(), "SE1", "SE2", "SE3", "SE4").grid(row=7, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(main_frame, text="Custom Price (SEK/kWh):").grid(row=8, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.custom_price, width=15).grid(row=8, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(main_frame, text="Start Mining Price (SEK/kWh):").grid(row=9, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.start_mining_price, width=15).grid(row=9, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(main_frame, text="API Host:").grid(row=10, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.api_host, width=20).grid(row=10, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(main_frame, text="API Port:").grid(row=11, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.api_port, width=10).grid(row=11, column=1, padx=5, pady=3, sticky="w")

        # ----- Knappar för start och stopp ----- #
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=12, column=0, columnspan=3, pady=(10, 0))

        start_button = ttk.Button(button_frame, text="Start", command=self.start_polling)
        start_button.grid(row=0, column=0, padx=10)

        stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_polling)
        stop_button.grid(row=0, column=1, padx=10)

        # ----- Debug Output ----- #
        ttk.Label(main_frame, text="Debug Output:").grid(row=13, column=0, columnspan=3, sticky="nw", pady=(15, 0))

        self.debug_output = tk.Text(main_frame, height=10, width=85, state="normal", bg="#FFFFFF", fg="black", relief="sunken")
        self.debug_output.grid(row=14, column=0, columnspan=3, sticky="w", pady=5)

        # Gör att fönstret kan expandera
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

    def browse_program_path(self):
        path = filedialog.askopenfilename(title="Select XMRig executable")
        if path:
            self.program_path.set(path)

    def log_debug(self, message):
        self.debug_output.configure(state="normal")
        self.debug_output.insert(tk.END, f"{message}\n")
        self.debug_output.configure(state="normal")
        self.debug_output.see(tk.END)

    def start_polling(self):
        if self.polling:
            messagebox.showinfo("Info", "Polling är redan igång.")
            return
        self.polling = True
        self.log_debug("Startar polling av elpriser ...")
        Thread(target=self.poll_prices, daemon=True).start()

    def stop_polling(self):
        self.polling = False
        self.stop_miner()
        self.log_debug("Polling stoppad.")

    def poll_prices(self):
        while self.polling:
            self.check_and_start_miner()
            # Vänta mellan varje poll
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
            self.log_debug(f"Fel vid hämtning av priser: {e}")
            return []

    def get_current_hour_price(self, prices):
        # Om Custom Price är satt, försök att använda den
        custom_price = self.custom_price.get()
        if custom_price:
            try:
                return float(custom_price)
            except ValueError:
                self.log_debug("Ogiltigt custom price. Använder API-data istället.")

        # Annars hämta aktuellt pris från API (med svensk tidszon)
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
        self.log_debug(f"Hämtar priser från: {api_url}")
        prices = self.fetch_prices(api_url)

        if prices or self.custom_price.get():
            current_price = self.get_current_hour_price(prices)
            if current_price is not None:
                self.update_current_price_label(current_price)
                self.log_debug(f"Nuvarande pris: {current_price} SEK/kWh")
                if current_price < self.start_mining_price.get():
                    self.start_miner()
                else:
                    self.stop_miner()
            else:
                self.log_debug("Kunde inte läsa av nuvarande elpris.")
                self.update_current_price_label(None)

    def update_current_price_label(self, current_price):
        """Updaterar den stora etiketten för nuvarande pris, med färgkod."""
        if current_price is None:
            self.current_price_text.set("N/A")
            self.current_price_label.configure(bg="#808080")  # Grå om okänd
            return

        self.current_price_text.set(f"{current_price:.2f} SEK/kWh")

        # Färgsätt beroende på om priset är under eller över start_mining_price
        if current_price < self.start_mining_price.get():
            self.current_price_label.configure(bg="#77dd77")  # ljusgrön
        else:
            self.current_price_label.configure(bg="#FF6961")  # ljusröd

    def start_miner(self):
        if self.program_process:
            self.log_debug("Minern körs redan.")
            return
        command = [
            self.program_path.get(),
            "-a", self.algo.get(),
            "-o", self.pool.get(),
            "-u", self.user.get(),
            "--threads", self.threads.get(),
            "--http-host", self.api_host.get(),
            "--http-port", self.api_port.get()
        ]
        try:
            self.program_process = subprocess.Popen(command)
            self.log_debug(f"XMRig startad med kommando: {' '.join(command)}")
        except Exception as e:
            self.log_debug(f"Misslyckades starta miner: {e}")

    def stop_miner(self):
        if self.program_process:
            self.program_process.terminate()
            self.program_process.wait()
            self.program_process = None
            self.log_debug("XMRig stoppad.")
        else:
            self.log_debug("Miner körs inte just nu.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MinerGUI(root)
    root.mainloop()
