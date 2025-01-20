import subprocess
import time
from datetime import datetime
import pytz
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from threading import Thread
import requests  # Används för att hämta prisdata

# Bas-URL för elpris-API
BASE_API_URL = "https://www.elprisetjustnu.se/api/v1/prices/{year}/{month_day}_{region}.json"

class MinerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("T-Rex Miner Controller")
        self.root.geometry("850x950")

        # --- Meny högst upp ---
        self.create_menu()

        # Tkinter-stilar
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#2d2d2d")
        style.configure("TLabel", background="#2d2d2d", foreground="#ffffff", font=("Arial", 10), padding=5)
        style.configure("TButton", padding=6, relief="flat", background="#4472C4", foreground="white", font=("Arial", 10, "bold"))
        style.map("TButton", background=[("active", "#0052cc")])
        # Grundläggande inställningar (tkinter Variabler)
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

        # Extra T-Rex-inställningar
        self.devices = tk.StringVar(value="")             # t.ex. "0" eller "0,1"
        self.temperature_limit = tk.StringVar(value="85") # Max temp innan T-Rex stänger av
        self.intensity = tk.StringVar(value="")           # GPU-intensitet
        self.mt = tk.StringVar(value="")                  # Memory Tweak (Nvidia)

        # Manuell override (om denna är på => mina alltid)
        self.override_var = tk.BooleanVar(value=False)

        # Pollning av elpris
        self.poll_interval = 300
        self.program_process = None
        self.polling = False

        # Variabel för att visa aktuell elpris-status
        self.current_price_text = tk.StringVar(value="Ej tillgängligt")

        self.create_widgets()

    def create_menu(self):
        """Skapar en enkel menyrad (Arkiv->Avsluta)."""
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Avsluta", command=self.root.quit)
        menubar.add_cascade(label="Arkiv", menu=file_menu)
        self.root.config(menu=menubar)

    def create_widgets(self):
        # Huvudram
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Gör att fönstret kan expandera
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # En stor rubrik
        title_label = ttk.Label(
            main_frame, 
            text="T-Rex Miner Controller",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))

        # Stor label för att visa elpris i realtid
        self.current_price_label = tk.Label(
            main_frame,
            textvariable=self.current_price_text,
            font=("Arial", 14, "bold"),
            width=25,
            bg="#808080",   # utgångsläge (grå)
            relief="groove",
            bd=2
        )
        self.current_price_label.grid(row=1, column=0, columnspan=3, pady=(0, 15))

        row_index = 2

        # 1) Path till T-Rex
        self.create_row(main_frame, "Path to T-Rex:", self.program_path, row=row_index, browse=True)
        row_index += 1

        # 2) Algorithm (combobox)
        self.create_row(main_frame, "Algorithm:", self.algo, row=row_index, dropdown=[
            "autolykos2", "blake3", "etchash", "ethash", "firopow", "kawpow",
            "mtp", "mtp-tcr", "multi", "octopus", "progpow", "progpow-veil",
            "progpow-veriblock", "progpowz", "tensority"
        ])
        row_index += 1

        # 3) Pool (combobox med några förval)
        self.create_row(main_frame, "Pool:", self.pool, row=row_index, combobox=True, dropdown=[
            "stratum+tcp://autolykos.auto.nicehash.com:9200",
            "stratum+tcp://alephium.auto.nicehash.com:9200",
            "stratum+tcp://etchash.auto.nicehash.com:9200",
            "stratum+tcp://kawpow.auto.nicehash.com:9200",
            "stratum+tcp://octopus.auto.nicehash.com:9200",
            "stratum+tcp://rvn.2miners.com:6060"
        ])
        row_index += 1

        # 4) User
        self.create_row(main_frame, "User:", self.user, row=row_index)
        row_index += 1

        # 5) Password
        self.create_row(main_frame, "Password:", self.password, row=row_index, hidden=True)
        row_index += 1

        # 6) Worker Name
        self.create_row(main_frame, "Worker Name:", self.worker, row=row_index)
        row_index += 1

        # 7) API Bind Address
        self.create_row(main_frame, "API Bind Address:", self.api_bind, row=row_index)
        row_index += 1

        # 8) Region
        self.create_row(main_frame, "Region:", self.region, row=row_index, dropdown=["SE1", "SE2", "SE3", "SE4"])
        row_index += 1

        # 9) Custom Price (SEK/kWh)
        self.create_row(main_frame, "Custom Price (SEK/kWh):", self.custom_price, row=row_index)
        row_index += 1

        # 10) Start Mining Under (SEK/kWh)
        self.create_row(main_frame, "Start Mining When Price < (SEK/kWh):", self.start_mining_price, row=row_index)
        row_index += 1

        # 11) Devices
        self.create_row(main_frame, "Devices (ex. 0,1):", self.devices, row=row_index)
        row_index += 1

        # 12) Temperature Limit (°C)
        self.create_row(main_frame, "Temperature Limit (°C):", self.temperature_limit, row=row_index)
        row_index += 1

        # 13) Intensity
        self.create_row(main_frame, "Intensity:", self.intensity, row=row_index)
        row_index += 1

        # 14) Memory Tweak
        self.create_row(main_frame, "Memory Tweak (Nvidia) --mt:", self.mt, row=row_index)
        row_index += 1

        # 15) Manual Override (Checkbox)
        ttk.Label(main_frame, text="Manual Override (mine always):").grid(row=row_index, column=0, sticky="w")
        override_checkbox = ttk.Checkbutton(main_frame, variable=self.override_var)
        override_checkbox.grid(row=row_index, column=1, sticky="w")
        row_index += 1

        # 16) Start och Stop-knappar
        tk.Button(main_frame, text="Start Polling", command=self.start_polling, bg="#4caf50", fg="#ffffff").grid(row=row_index, column=0, pady=10)
        tk.Button(main_frame, text="Stop Polling", command=self.stop_polling, bg="#f44336", fg="#ffffff").grid(row=row_index, column=1, pady=10)
        row_index += 1

        # 17) Debug Output
        ttk.Label(main_frame, text="Debug Output:").grid(row=row_index, column=0, sticky="nw")
        row_index += 1

        self.debug_output = tk.Text(main_frame, height=15, width=85, state="normal", bg="#FFFFFF", fg="black")
        self.debug_output.grid(row=row_index, column=0, columnspan=3, sticky="w", pady=10)
        row_index += 1

    def create_row(self, frame, label_text, variable, row, browse=False, combobox=False, dropdown=None, hidden=False):
        """ Hjälpfunktion för att skapa en "rad" med Label + Entry/Combobox (+ ev. Browse-knapp). """
        ttk.Label(frame, text=label_text).grid(row=row, column=0, sticky="w")

        # Combobox-läge
        if combobox:
            widget = ttk.Combobox(frame, textvariable=variable, values=dropdown, width=50)
            widget.grid(row=row, column=1, padx=5)
            widget.set(variable.get())
            return

        # Dropdown-läge (readonly Combobox)
        if dropdown and not combobox:
            widget = ttk.Combobox(frame, textvariable=variable, values=dropdown, width=50, state="readonly")
            widget.grid(row=row, column=1, padx=5)
            widget.set(variable.get())
            return

        # Browse-läge (fil-sökning)
        if browse:
            entry = ttk.Entry(frame, textvariable=variable, width=50)
            entry.grid(row=row, column=1, padx=5)
            ttk.Button(frame, text="Browse", command=lambda: self.browse_program_path()).grid(row=row, column=2, padx=5)
            return

        # Dold text (t.ex. lösenord)
        if hidden:
            entry = ttk.Entry(frame, textvariable=variable, show="*", width=50)
            entry.grid(row=row, column=1, padx=5)
            return

        # Standard-läge (en vanlig Entry)
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

    def fetch_prices(self, api_url):
        """Hämtar JSON-data från elpris-API:t."""
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log_debug(f"Error fetching prices: {e}")
            return []

    def get_current_hour_price(self, prices):
        """
        Returnerar antingen 'custom_price' om användaren angett det,
        annars letar vi upp det aktuella timpriset i listan (API).
        """
        custom_price = self.custom_price.get()
        if custom_price:
            try:
                return float(custom_price)
            except ValueError:
                self.log_debug("Invalid custom price entered. Using API data instead.")

        sweden_tz = pytz.timezone("Europe/Stockholm")
        current_time_sweden = datetime.now(sweden_tz)

        for price_entry in prices:
            try:
                start_time = datetime.fromisoformat(price_entry["time_start"])
                end_time = datetime.fromisoformat(price_entry["time_end"])
                start_time = start_time.astimezone(sweden_tz)
                end_time = end_time.astimezone(sweden_tz)

                if start_time <= current_time_sweden < end_time:
                    return price_entry["SEK_per_kWh"]
            except Exception as e:
                self.log_debug(f"Price entry parsing error: {e}")

        return None

    def start_polling(self):
        """Startar en separat tråd som loopar och kollar elpriset."""
        if self.polling:
            messagebox.showinfo("Info", "Polling is already active.")
            return
        self.polling = True
        self.log_debug("Starting price polling...")
        Thread(target=self.poll_prices, daemon=True).start()

    def stop_polling(self):
        """Stoppar polling och avbryter minern."""
        self.polling = False
        self.stop_miner()
        self.log_debug("Polling stopped.")

    def poll_prices(self):
        """Loopar så länge self.polling = True och kollar priset."""
        while self.polling:
            self.check_and_start_miner()
            time.sleep(self.poll_interval)

    def check_and_start_miner(self):
        """
        Kollar elpris, jämför med start_mining_price.
        - Om price < threshold => start miner
        - annars => stop miner
        - Om override = True => start miner alltid
        """
        # Om manuell override är aktiv => strunta i prislogik, starta minern direkt
        if self.override_var.get():
            self.log_debug("Manual override is active => Starting miner regardless of price.")
            # Vi sätter label till "Override" men färgsätter den ändå
            self.update_current_price_label(None, override=True)
            self.start_miner()
            return

        api_url = self.get_api_url()
        self.log_debug(f"Fetching prices from: {api_url}")
        prices = self.fetch_prices(api_url)

        if prices or self.custom_price.get():
            current_price = self.get_current_hour_price(prices)
            if current_price is not None:
                self.log_debug(f"Current price: {current_price} SEK/kWh")
                self.update_current_price_label(current_price)
                if current_price < self.start_mining_price.get():
                    self.start_miner()
                else:
                    self.stop_miner()
            else:
                self.log_debug("Could not find price for the current hour.")
                self.update_current_price_label(None)
        else:
            self.log_debug("Failed to fetch price data.")

    def get_api_url(self):
        """
        Bygger upp korrekt URL för dagens datum och vald region.
        """
        sweden_tz = pytz.timezone("Europe/Stockholm")
        current_time_sweden = datetime.now(sweden_tz)
        year = current_time_sweden.year
        month_day = current_time_sweden.strftime("%m-%d")
        return BASE_API_URL.format(year=year, month_day=month_day, region=self.region.get())

    def update_current_price_label(self, current_price, override=False):
        """
        Uppdaterar den stora etiketten med nuvarande elpris,
        samt färgsätter den beroende på om det är under/över threshold.
        Om override=True => skriv "Override" och färgsätt blå/grå t.ex.
        """
        if override:
            self.current_price_text.set("Override Active")
            self.current_price_label.configure(bg="#87CEEB")  # ljusblå som signal
            return

        if current_price is None:
            self.current_price_text.set("N/A")
            self.current_price_label.configure(bg="#808080")  # grå
            return

        # Sätt texten och färg
        self.current_price_text.set(f"{current_price:.2f} SEK/kWh")
        if current_price < self.start_mining_price.get():
            self.current_price_label.configure(bg="#77dd77")  # ljusgrön
        else:
            self.current_price_label.configure(bg="#FF6961")  # ljusröd

    def start_miner(self):
        """Startar T-Rex i en subprocess, om den inte redan körs."""
        if self.program_process and self.program_process.poll() is None:
            self.log_debug("Miner is already running.")
            return

        # Bygg upp T-Rex-kommando
        command = [
            self.program_path.get(),
            "-a", self.algo.get(),
            "-o", self.pool.get(),
            "-u", self.user.get(),
            "-p", self.password.get(),
            "-w", self.worker.get(),
            "--api-bind-http", self.api_bind.get()
        ]

        # Lägg till extra T-Rex-flaggor om de är ifyllda
        if self.devices.get():
            command += ["--devices", self.devices.get()]

        if self.temperature_limit.get():
            command += ["--temperature-limit", self.temperature_limit.get()]

        if self.intensity.get():
            command += ["--intensity", self.intensity.get()]

        if self.mt.get():
            command += ["--mt", self.mt.get()]

        try:
            self.program_process = subprocess.Popen(command)
            self.log_debug(f"Miner started with command: {' '.join(command)}")
        except Exception as e:
            self.log_debug(f"Failed to start miner: {e}")

    def stop_miner(self):
        """Stoppar T-Rex om den körs."""
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
