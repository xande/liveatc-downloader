#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from liveatc import get_stations, download_archive
import os
import time

try:
    from tkcalendar import Calendar
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False


class DatePickerEntry(ttk.Frame):
    """Custom date picker with calendar dropdown, auto-formatting, and arrow key support"""

    def __init__(self, parent, initial_date=None, **kwargs):
        super().__init__(parent)

        if initial_date is None:
            initial_date = datetime.now()

        self.current_date = initial_date
        self.calendar_window = None

        # Create entry field
        self.entry = ttk.Entry(self, width=12, justify='center')
        self.entry.pack(side=tk.LEFT, padx=(0, 2))

        # Create calendar button
        self.cal_btn = ttk.Button(self, text="📅", width=3, command=self.show_calendar)
        self.cal_btn.pack(side=tk.LEFT)

        # Set initial value
        self._update_entry()

        # Bind events for auto-formatting and arrow keys
        self.entry.bind('<KeyRelease>', self._on_key_release)
        self.entry.bind('<Up>', self._on_arrow_up)
        self.entry.bind('<Down>', self._on_arrow_down)
        self.entry.bind('<FocusOut>', self._validate_on_blur)

    def _update_entry(self):
        """Update entry field with current date"""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.current_date.strftime('%m/%d/%Y'))

    def _on_key_release(self, event):
        """Auto-format date as user types"""
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Tab', 'Shift_L', 'Shift_R'):
            return

        text = self.entry.get()
        # Remove any non-digits
        digits = ''.join(c for c in text if c.isdigit())

        # Auto-format with slashes
        if len(digits) <= 2:
            formatted = digits
        elif len(digits) <= 4:
            formatted = f"{digits[:2]}/{digits[2:]}"
        else:
            formatted = f"{digits[:2]}/{digits[2:4]}/{digits[4:8]}"

        # Update entry if changed
        if formatted != text:
            cursor_pos = self.entry.index(tk.INSERT)
            self.entry.delete(0, tk.END)
            self.entry.insert(0, formatted)
            # Try to maintain cursor position
            self.entry.icursor(min(cursor_pos + (1 if len(formatted) > len(text) else 0), len(formatted)))

    def _get_cursor_part(self):
        """Determine which part of date (month/day/year) cursor is in"""
        cursor_pos = self.entry.index(tk.INSERT)
        text = self.entry.get()

        if not text or '/' not in text:
            return 'month'

        parts = text.split('/')
        if cursor_pos <= len(parts[0]):
            return 'month'
        elif cursor_pos <= len(parts[0]) + 1 + (len(parts[1]) if len(parts) > 1 else 0):
            return 'day'
        else:
            return 'year'

    def _on_arrow_up(self, event):
        """Increment date part under cursor"""
        try:
            self._parse_current_entry()
            part = self._get_cursor_part()

            if part == 'month':
                self.current_date = self.current_date.replace(month=self.current_date.month % 12 + 1) if self.current_date.month < 12 else self.current_date.replace(month=1, year=self.current_date.year + 1)
            elif part == 'day':
                self.current_date += timedelta(days=1)
            elif part == 'year':
                self.current_date = self.current_date.replace(year=self.current_date.year + 1)

            self._update_entry()
        except:
            pass
        return 'break'

    def _on_arrow_down(self, event):
        """Decrement date part under cursor"""
        try:
            self._parse_current_entry()
            part = self._get_cursor_part()

            if part == 'month':
                self.current_date = self.current_date.replace(month=self.current_date.month - 1) if self.current_date.month > 1 else self.current_date.replace(month=12, year=self.current_date.year - 1)
            elif part == 'day':
                self.current_date -= timedelta(days=1)
            elif part == 'year':
                self.current_date = self.current_date.replace(year=self.current_date.year - 1)

            self._update_entry()
        except:
            pass
        return 'break'

    def _parse_current_entry(self):
        """Try to parse current entry text to update current_date"""
        text = self.entry.get()
        try:
            self.current_date = datetime.strptime(text, '%m/%d/%Y')
        except:
            pass  # Keep previous date if parse fails

    def _validate_on_blur(self, event):
        """Validate and reformat date when user leaves field"""
        text = self.entry.get()
        try:
            parsed = datetime.strptime(text, '%m/%d/%Y')
            self.current_date = parsed
            self._update_entry()
        except:
            # Reset to current valid date if invalid
            self._update_entry()

    def show_calendar(self):
        """Show calendar popup for date selection"""
        if not CALENDAR_AVAILABLE:
            messagebox.showinfo("Calendar Not Available",
                              "tkcalendar is not installed.\nYou can still type the date or use arrow keys.")
            return

        if self.calendar_window is not None:
            return  # Already showing

        # Parse current date
        self._parse_current_entry()

        # Create popup window
        self.calendar_window = tk.Toplevel(self)
        self.calendar_window.title("Select Date")
        self.calendar_window.transient(self)
        self.calendar_window.grab_set()

        # Create calendar widget
        cal = Calendar(self.calendar_window, selectmode='day',
                      year=self.current_date.year,
                      month=self.current_date.month,
                      day=self.current_date.day)
        cal.pack(padx=10, pady=10)

        def on_select():
            selected = cal.get_date()
            try:
                self.current_date = datetime.strptime(selected, '%m/%d/%y')
                # Handle two-digit year properly
                if self.current_date.year < 2000:
                    self.current_date = self.current_date.replace(year=self.current_date.year + 100)
                self._update_entry()
            except:
                pass
            self.calendar_window.destroy()
            self.calendar_window = None

        def on_close():
            self.calendar_window.destroy()
            self.calendar_window = None

        # Buttons
        btn_frame = ttk.Frame(self.calendar_window)
        btn_frame.pack(pady=(0, 10))

        ttk.Button(btn_frame, text="Select", command=on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_close).pack(side=tk.LEFT, padx=5)

        self.calendar_window.protocol("WM_DELETE_WINDOW", on_close)

        # Center the window
        self.calendar_window.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self.calendar_window.geometry(f"+{x}+{y}")

    def get(self):
        """Get current date value as string in MM/DD/YYYY format"""
        self._parse_current_entry()
        return self.current_date.strftime('%m/%d/%Y')

    def get_datetime(self):
        """Get current date value as datetime object"""
        self._parse_current_entry()
        return self.current_date


class LiveATCDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LiveATC Downloader")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        self.stations_data = []
        self.selected_station = None  # Track selected station persistently
        self.downloading = False
        self.download_cancelled = False
        self.download_paused = False

        # Download state tracking
        self.pending_intervals = []  # Intervals to be downloaded
        self.completed_intervals = []  # Successfully downloaded
        self.failed_intervals = []  # Failed downloads with error info
        self.download_params = None  # Store download parameters for resume

        self.create_widgets()
        
    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # ===== AIRPORT SEARCH =====
        row = 0
        ttk.Label(main_frame, text="Airport ICAO Code:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5))
        
        row += 1
        search_frame = ttk.Frame(main_frame)
        search_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        search_frame.columnconfigure(0, weight=1)
        
        self.icao_entry = ttk.Entry(search_frame, font=('Arial', 10))
        self.icao_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.icao_entry.bind('<Return>', lambda e: self.search_stations())
        
        self.search_btn = ttk.Button(search_frame, text="Search Stations", command=self.search_stations)
        self.search_btn.grid(row=0, column=1)
        
        # ===== STATIONS LIST =====
        row += 1
        ttk.Label(main_frame, text="Available Stations:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        
        row += 1
        # Frame for listbox and scrollbar
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(row, weight=1)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Listbox
        self.stations_listbox = tk.Listbox(list_frame, height=8, font=('Courier', 9),
                                           yscrollcommand=scrollbar.set)
        self.stations_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.stations_listbox.yview)
        self.stations_listbox.bind('<<ListboxSelect>>', self.on_station_select)
        
        # ===== SELECTED STATION INFO =====
        row += 1
        ttk.Label(main_frame, text="Selected Station:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        
        row += 1
        self.station_info_label = ttk.Label(main_frame, text="No station selected", 
                                           foreground='gray', wraplength=700)
        self.station_info_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # ===== TIME RANGE =====
        row += 1
        ttk.Label(main_frame, text="Time Range (UTC/Zulu):", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        
        row += 1
        time_frame = ttk.Frame(main_frame)
        time_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        from datetime import timezone
        current_time = datetime.now(timezone.utc)

        # Start time
        ttk.Label(time_frame, text="Start:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))

        # Date picker with calendar dropdown
        self.start_date_entry = DatePickerEntry(time_frame, initial_date=current_time)
        self.start_date_entry.grid(row=0, column=1, padx=(0, 5))

        # Start time - Hour spinbox (00-23)
        self.start_hour = tk.Spinbox(time_frame, from_=0, to=23, width=4, format="%02.0f",
                                     wrap=True, justify='center')
        self.start_hour.grid(row=0, column=2, padx=(0, 2))
        self.start_hour.delete(0, tk.END)
        self.start_hour.insert(0, '00')

        # Start time - Minute spinbox (00 or 30 only)
        self.start_minute = tk.Spinbox(time_frame, values=('00', '30'), width=4,
                                       wrap=True, justify='center')
        self.start_minute.grid(row=0, column=3, padx=(0, 2))
        self.start_minute.delete(0, tk.END)
        self.start_minute.insert(0, '00')

        ttk.Label(time_frame, text="Z").grid(row=0, column=4, sticky=tk.W, padx=(0, 15))

        # End time
        ttk.Label(time_frame, text="End:").grid(row=0, column=5, sticky=tk.W, padx=(0, 5))

        # Date picker with calendar dropdown
        minutes = (current_time.minute // 30) * 30
        rounded_time = current_time.replace(minute=minutes, second=0, microsecond=0)
        self.end_date_entry = DatePickerEntry(time_frame, initial_date=rounded_time)
        self.end_date_entry.grid(row=0, column=6, padx=(0, 5))

        # End time - Hour spinbox (00-23)
        self.end_hour = tk.Spinbox(time_frame, from_=0, to=23, width=4, format="%02.0f",
                                   wrap=True, justify='center')
        self.end_hour.grid(row=0, column=7, padx=(0, 2))
        self.end_hour.delete(0, tk.END)
        self.end_hour.insert(0, f"{rounded_time.hour:02d}")

        # End time - Minute spinbox (00 or 30 only)
        self.end_minute = tk.Spinbox(time_frame, values=('00', '30'), width=4,
                                     wrap=True, justify='center')
        self.end_minute.grid(row=0, column=8, padx=(0, 2))
        self.end_minute.delete(0, tk.END)
        self.end_minute.insert(0, f"{rounded_time.minute:02d}")

        ttk.Label(time_frame, text="Z").grid(row=0, column=9, sticky=tk.W)

        # Format help
        row += 1
        help_text = "Click 📅 for calendar | Type date (auto-formats) | Use ↑↓ arrows to adjust date/time | Time is in UTC/Zulu"
        ttk.Label(main_frame, text=help_text,
                 foreground='gray', font=('Arial', 8)).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # ===== OUTPUT FOLDER =====
        row += 1
        ttk.Label(main_frame, text="Output Folder:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        
        row += 1
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        
        self.output_entry = ttk.Entry(output_frame, font=('Arial', 9))
        self.output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.output_entry.insert(0, os.path.expanduser('~/Downloads'))

        self.browse_btn = ttk.Button(output_frame, text="Browse...", command=self.browse_output)
        self.browse_btn.grid(row=0, column=1)

        # ===== DOWNLOAD SETTINGS =====
        row += 1
        settings_frame = ttk.Frame(main_frame)
        settings_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(5, 10))

        # Thread count
        ttk.Label(settings_frame, text="Concurrent downloads:", font=('Arial', 9)).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5))

        self.thread_count = tk.Spinbox(settings_frame, from_=1, to=100, width=4,
                                       wrap=False, justify='center')
        self.thread_count.grid(row=0, column=1, padx=(0, 5))
        self.thread_count.delete(0, tk.END)
        self.thread_count.insert(0, '5')

        ttk.Label(settings_frame, text="threads (1-100)", font=('Arial', 9)).grid(
            row=0, column=2, sticky=tk.W, padx=(0, 15))

        # Delay between downloads
        ttk.Label(settings_frame, text="Delay between downloads:", font=('Arial', 9)).grid(
            row=0, column=3, sticky=tk.W, padx=(0, 5))

        self.delay_entry = ttk.Entry(settings_frame, width=8)
        self.delay_entry.grid(row=0, column=4, padx=(0, 5))
        self.delay_entry.insert(0, '2')

        ttk.Label(settings_frame, text="seconds (per thread, to avoid rate-limiting)",
                 foreground='gray', font=('Arial', 8)).grid(row=0, column=5, sticky=tk.W)
        
        # ===== DOWNLOAD BUTTONS =====
        row += 1
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=(10, 10))

        self.download_btn = ttk.Button(button_frame, text="Download Archives",
                                       command=self.start_download, state='disabled')
        self.download_btn.grid(row=0, column=0, padx=(0, 5))

        self.pause_btn = ttk.Button(button_frame, text="Pause",
                                    command=self.pause_download, state='disabled')
        self.pause_btn.grid(row=0, column=1, padx=(0, 5))

        self.cancel_btn = ttk.Button(button_frame, text="Stop",
                                     command=self.cancel_download, state='disabled')
        self.cancel_btn.grid(row=0, column=2, padx=(0, 15))

        self.retry_btn = ttk.Button(button_frame, text="Retry Failed",
                                    command=self.retry_failed, state='disabled')
        self.retry_btn.grid(row=0, column=3, padx=(0, 5))

        self.view_failed_btn = ttk.Button(button_frame, text="View Failed",
                                          command=self.view_failed, state='disabled')
        self.view_failed_btn.grid(row=0, column=4)
        
        # ===== PROGRESS LOG =====
        row += 1
        ttk.Label(main_frame, text="Download Log:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        
        row += 1
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(row, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, font=('Courier', 9),
                                                   state='disabled')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ===== STATUS BAR =====
        row += 1
        self.status_label = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
    def log(self, message):
        """Add message to log window"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
    def set_status(self, message):
        """Update status bar"""
        self.status_label.config(text=message)
        
    def search_stations(self):
        """Search for stations by ICAO code"""
        icao = self.icao_entry.get().strip().upper()
        if not icao:
            messagebox.showwarning("Input Required", "Please enter an airport ICAO code")
            return
        
        self.set_status(f"Searching for stations at {icao}...")
        self.search_btn.config(state='disabled')
        self.stations_listbox.delete(0, tk.END)
        self.stations_data = []
        self.selected_station = None  # Clear selected station on new search
        self.station_info_label.config(text="No station selected", foreground='gray')
        self.download_btn.config(state='disabled')
        
        # Run search in background thread
        thread = threading.Thread(target=self._search_stations_thread, args=(icao,))
        thread.daemon = True
        thread.start()
        
    def _search_stations_thread(self, icao):
        """Background thread for station search"""
        try:
            stations = list(get_stations(icao))
            self.stations_data = stations
            
            # Update UI in main thread
            self.root.after(0, self._update_stations_list, stations)
        except Exception as e:
            self.root.after(0, self._search_error, str(e))
            
    def _update_stations_list(self, stations):
        """Update stations listbox with results"""
        self.stations_listbox.delete(0, tk.END)
        
        if not stations:
            self.stations_listbox.insert(tk.END, "No stations found")
            self.set_status("No stations found")
        else:
            for station in stations:
                status = "●" if station['up'] else "○"
                display = f"{status} [{station['identifier']}] - {station['title']}"
                self.stations_listbox.insert(tk.END, display)
            self.set_status(f"Found {len(stations)} station(s)")
            
        self.search_btn.config(state='normal')
        
    def _search_error(self, error):
        """Handle search error"""
        messagebox.showerror("Search Error", f"Failed to search stations:\n{error}")
        self.set_status("Search failed")
        self.search_btn.config(state='normal')
        
    def on_station_select(self, event):
        """Handle station selection"""
        selection = self.stations_listbox.curselection()
        if not selection or not self.stations_data:
            return

        idx = selection[0]
        if idx >= len(self.stations_data):
            return

        station = self.stations_data[idx]

        # Store selected station persistently
        self.selected_station = station

        # Display station info
        freqs = ", ".join([f"{f['title']} ({f['frequency']})" for f in station['frequencies']])
        status = "ONLINE" if station['up'] else "OFFLINE"
        info = f"ID: {station['identifier']}\nStatus: {status}\nFrequencies: {freqs}"

        self.station_info_label.config(text=info, foreground='black')
        self.download_btn.config(state='normal' if station['up'] else 'disabled')
        
    def browse_output(self):
        """Browse for output folder"""
        folder = filedialog.askdirectory(initialdir=self.output_entry.get())
        if folder:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)
            
    def cancel_download(self):
        """Cancel ongoing download"""
        if self.downloading:
            self.download_cancelled = True
            self.log("Download cancelled by user")
            self.set_status("Cancelling download...")
            self.cancel_btn.config(state='disabled')
    
    def start_download(self):
        """Start or resume download process"""
        # Check if resuming
        if self.download_paused and self.pending_intervals:
            # Resume paused download
            self.download_paused = False
            self.download_cancelled = False
            self.downloading = True

            # Update UI
            self.download_btn.config(state='disabled', text="Download Archives")
            self.pause_btn.config(state='normal', text="Pause")
            self.cancel_btn.config(state='normal')
            self.search_btn.config(state='disabled')

            self.log("\n=== Resuming Download ===\n")

            # Resume with existing parameters
            params = self.download_params
            thread = threading.Thread(target=self._download_thread,
                                     args=(params['station'], None, None,
                                           params['output_folder'], params['delay'],
                                           params['num_threads']))
            thread.daemon = True
            thread.start()
            return

        # New download - validate inputs
        if not self.selected_station:
            messagebox.showwarning("No Selection", "Please select a station")
            return

        station = self.selected_station

        # Get and validate dates
        start_input = self.start_date_entry.get().strip()
        end_input = self.end_date_entry.get().strip()

        try:
            start_date = datetime.strptime(start_input, '%m/%d/%Y').strftime('%b-%d-%Y')
            end_date = datetime.strptime(end_input, '%m/%d/%Y').strftime('%b-%d-%Y')
        except ValueError:
            messagebox.showerror("Date Format Error",
                               "Invalid date format. Please use MM/DD/YYYY\n\nExample: 12/14/2025")
            return

        start_time = f"{self.start_hour.get()}{self.start_minute.get()}Z"
        end_time = f"{self.end_hour.get()}{self.end_minute.get()}Z"
        output_folder = self.output_entry.get().strip()
        delay_str = self.delay_entry.get().strip()
        thread_count_str = self.thread_count.get().strip()

        if not all([start_date, end_date, output_folder, delay_str, thread_count_str]):
            messagebox.showwarning("Input Required", "Please fill in all fields")
            return

        # Validate delay
        try:
            delay = float(delay_str)
            if delay < 0:
                messagebox.showwarning("Invalid Delay", "Delay must be a positive number")
                return
        except ValueError:
            messagebox.showwarning("Invalid Delay", "Delay must be a number (e.g., 2)")
            return

        # Validate thread count
        try:
            num_threads = int(thread_count_str)
            if num_threads < 1 or num_threads > 100:
                messagebox.showwarning("Invalid Thread Count", "Thread count must be between 1 and 100")
                return
        except ValueError:
            messagebox.showwarning("Invalid Thread Count", "Thread count must be a number")
            return

        # Validate output folder
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                messagebox.showerror("Folder Error", f"Cannot create output folder:\n{e}")
                return

        # Parse dates
        try:
            start_datetime = datetime.strptime(f"{start_date}-{start_time}", '%b-%d-%Y-%H%MZ')
            end_datetime = datetime.strptime(f"{end_date}-{end_time}", '%b-%d-%Y-%H%MZ')

            if end_datetime <= start_datetime:
                messagebox.showwarning("Invalid Range", "End time must be after start time")
                return
        except ValueError as e:
            messagebox.showerror("Date Format Error",
                               f"Invalid date/time format:\n{e}\n\nUse format: Dec-11-2025 and 1430Z")
            return

        # Clear log and reset state for new download
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

        self.completed_intervals = []
        self.failed_intervals = []
        self.pending_intervals = []

        # Store download parameters for resume/retry
        self.download_params = {
            'station': station,
            'output_folder': output_folder,
            'delay': delay,
            'num_threads': num_threads
        }

        # Disable controls
        self.download_btn.config(state='disabled')
        self.pause_btn.config(state='normal', text="Pause")
        self.cancel_btn.config(state='normal')
        self.retry_btn.config(state='disabled')
        self.view_failed_btn.config(state='disabled')
        self.search_btn.config(state='disabled')
        self.downloading = True
        self.download_cancelled = False
        self.download_paused = False

        # Start download in background
        thread = threading.Thread(target=self._download_thread,
                                 args=(station, start_datetime, end_datetime, output_folder, delay, num_threads))
        thread.daemon = True
        thread.start()
        
    def _download_thread(self, station, start_datetime, end_datetime, output_folder, delay, num_threads):
        """Background thread for downloading with multithreading support and pause/resume"""
        import shutil

        # If resuming or retrying, use pending_intervals, otherwise generate new list
        if self.pending_intervals:
            intervals = self.pending_intervals.copy()
            self.root.after(0, self.log, f"Resuming with {len(intervals)} remaining interval(s)")
        else:
            # Generate list of all time intervals to download
            intervals = []
            current = start_datetime
            while current <= end_datetime:
                intervals.append(current)
                current += timedelta(minutes=30)

            self.pending_intervals = intervals.copy()

            self.root.after(0, self.log, f"Starting download for {station['identifier']}")
            self.root.after(0, self.log, f"Time range: {start_datetime} to {end_datetime} UTC")
            self.root.after(0, self.log, f"Total intervals: {len(intervals)}")
            self.root.after(0, self.log, f"Output folder: {output_folder}")
            self.root.after(0, self.log, f"Using {num_threads} concurrent thread(s)")
            self.root.after(0, self.log, f"Delay between downloads: {delay} seconds (per thread)\n")

        total_intervals = len(self.completed_intervals) + len(self.failed_intervals) + len(intervals)
        downloaded = len(self.completed_intervals)
        failed = len(self.failed_intervals)

        def download_single_interval(interval_time):
            """Download a single time interval"""
            if self.download_cancelled or self.download_paused:
                return None

            date_str = interval_time.strftime('%b-%d-%Y')
            time_str = interval_time.strftime('%H%MZ')

            try:
                # Download to temp location first
                filepath = download_archive(station['identifier'], date_str, time_str)

                # Move to output folder
                filename = os.path.basename(filepath)
                dest_path = os.path.join(output_folder, filename)
                shutil.move(filepath, dest_path)

                return {'success': True, 'date': date_str, 'time': time_str, 'filename': filename, 'interval': interval_time}
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."
                return {'success': False, 'date': date_str, 'time': time_str, 'error': error_msg, 'interval': interval_time}

        # Use ThreadPoolExecutor for concurrent downloads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit all download tasks
            futures = []
            for idx, interval in enumerate(intervals):
                if self.download_cancelled or self.download_paused:
                    break
                future = executor.submit(download_single_interval, interval)
                futures.append((future, interval))

                # Add delay between submissions to stagger the threads
                if delay > 0 and idx < len(intervals) - 1:
                    time.sleep(delay / num_threads)

            # Process results as they complete
            processed = 0
            for future, interval in futures:
                if self.download_cancelled or self.download_paused:
                    # Cancel remaining futures
                    future.cancel()
                    continue

                try:
                    result = future.result()
                    if result is None:
                        # Task was cancelled or paused - keep in pending
                        continue

                    # Remove from pending list
                    if interval in self.pending_intervals:
                        self.pending_intervals.remove(interval)

                    processed += 1
                    current_total = downloaded + failed + processed
                    progress = f"[{current_total}/{total_intervals}]"

                    if result['success']:
                        downloaded += 1
                        self.completed_intervals.append(result['interval'])
                        self.root.after(0, self.log,
                                      f"{progress} ✓ {result['date']} {result['time']} -> {result['filename']}")
                        self.root.after(0, self.set_status,
                                      f"Progress: {current_total}/{total_intervals} ({downloaded} OK, {failed} failed)")
                    else:
                        failed += 1
                        self.failed_intervals.append({'interval': result['interval'], 'error': result['error']})
                        self.root.after(0, self.log,
                                      f"{progress} ✗ {result['date']} {result['time']}: {result['error']}")
                        self.root.after(0, self.set_status,
                                      f"Progress: {current_total}/{total_intervals} ({downloaded} OK, {failed} failed)")
                except Exception as e:
                    failed += 1
                    if interval in self.pending_intervals:
                        self.pending_intervals.remove(interval)
                    self.failed_intervals.append({'interval': interval, 'error': str(e)})
                    self.root.after(0, self.log, f"[ERROR] Unexpected error: {str(e)}")

        # Summary
        if self.download_paused:
            self.root.after(0, self.log, f"\n=== Download Paused ===")
            self.root.after(0, self.log, f"Completed: {downloaded} files")
            self.root.after(0, self.log, f"Failed: {failed} files")
            self.root.after(0, self.log, f"Remaining: {len(self.pending_intervals)} files")
        elif not self.download_cancelled:
            self.root.after(0, self.log, f"\n=== Download Complete ===")
            self.root.after(0, self.log, f"Successfully downloaded: {downloaded} files")
            self.root.after(0, self.log, f"Failed: {failed} files")
        else:
            self.root.after(0, self.log, f"\n=== Download Stopped ===")
            self.root.after(0, self.log, f"Successfully downloaded: {downloaded} files")
            self.root.after(0, self.log, f"Failed: {failed} files")

        # Re-enable controls
        self.root.after(0, self._download_complete, downloaded, failed)
        
    def _download_complete(self, downloaded, failed):
        """Handle download completion"""
        self.downloading = False

        if self.download_paused:
            # Paused state
            self.download_btn.config(text="Resume Download", state='normal')
            self.pause_btn.config(state='disabled')
            self.cancel_btn.config(state='normal')
            self.search_btn.config(state='disabled')
            self.set_status(f"Download paused: {downloaded} successful, {failed} failed, {len(self.pending_intervals)} remaining")
        else:
            # Completed or stopped
            self.download_btn.config(text="Download Archives", state='normal')
            self.pause_btn.config(state='disabled')
            self.cancel_btn.config(state='disabled')
            self.search_btn.config(state='normal')

            if self.download_cancelled:
                self.set_status(f"Download stopped: {downloaded} successful, {failed} failed")
            else:
                self.set_status(f"Download complete: {downloaded} successful, {failed} failed")

            # Enable retry button if there are failed downloads
            if len(self.failed_intervals) > 0:
                self.retry_btn.config(state='normal')
                self.view_failed_btn.config(state='normal')
            else:
                self.retry_btn.config(state='disabled')
                self.view_failed_btn.config(state='disabled')

            if downloaded > 0 and not self.download_cancelled:
                messagebox.showinfo("Download Complete",
                                  f"Downloaded {downloaded} file(s)\nFailed: {failed}\n\n"
                                  f"Files saved to:\n{self.output_entry.get()}")
            elif downloaded > 0 and self.download_cancelled:
                messagebox.showinfo("Download Stopped",
                                  f"Download cancelled.\n\nDownloaded {downloaded} file(s) before stopping\nFailed: {failed}\n\n"
                                  f"Files saved to:\n{self.output_entry.get()}")

    def pause_download(self):
        """Pause the current download"""
        if self.downloading and not self.download_paused:
            self.download_paused = True
            self.pause_btn.config(text="Pausing...", state='disabled')
            self.log("⏸ Pausing download... (will finish current batch)")

    def retry_failed(self):
        """Retry all failed downloads"""
        if not self.failed_intervals or not self.download_params:
            return

        # Ask for confirmation
        count = len(self.failed_intervals)
        if not messagebox.askyesno("Retry Failed Downloads",
                                   f"Retry {count} failed download(s)?"):
            return

        # Reset state
        self.pending_intervals = [item['interval'] for item in self.failed_intervals]
        self.failed_intervals = []
        self.download_paused = False
        self.download_cancelled = False

        # Update UI
        self.download_btn.config(state='disabled', text="Download Archives")
        self.pause_btn.config(state='normal', text="Pause")
        self.cancel_btn.config(state='normal')
        self.retry_btn.config(state='disabled')
        self.view_failed_btn.config(state='disabled')
        self.search_btn.config(state='disabled')
        self.downloading = True

        self.log(f"\n=== Retrying {count} Failed Download(s) ===\n")

        # Start download thread with failed intervals
        params = self.download_params
        thread = threading.Thread(target=self._download_thread,
                                 args=(params['station'], None, None,
                                       params['output_folder'], params['delay'],
                                       params['num_threads']))
        thread.daemon = True
        thread.start()

    def view_failed(self):
        """Show a window with all failed downloads"""
        if not self.failed_intervals:
            messagebox.showinfo("No Failed Downloads", "There are no failed downloads to view.")
            return

        # Create popup window
        failed_window = tk.Toplevel(self.root)
        failed_window.title("Failed Downloads")
        failed_window.geometry("700x400")

        # Header
        header_frame = ttk.Frame(failed_window, padding="10")
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text=f"Failed Downloads ({len(self.failed_intervals)} total)",
                 font=('Arial', 12, 'bold')).pack()

        # List frame
        list_frame = ttk.Frame(failed_window, padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Create text widget with scrollbar
        text_scroll = scrolledtext.ScrolledText(list_frame, height=15, font=('Courier', 9))
        text_scroll.pack(fill=tk.BOTH, expand=True)

        # Populate with failed downloads
        for i, item in enumerate(self.failed_intervals, 1):
            interval = item['interval']
            error = item.get('error', 'Unknown error')
            date_str = interval.strftime('%b-%d-%Y')
            time_str = interval.strftime('%H%MZ')
            text_scroll.insert(tk.END, f"[{i}] {date_str} {time_str}\n")
            text_scroll.insert(tk.END, f"    Error: {error}\n\n")

        text_scroll.config(state='disabled')

        # Buttons
        button_frame = ttk.Frame(failed_window, padding="10")
        button_frame.pack(fill=tk.X)

        def copy_to_clipboard():
            failed_window.clipboard_clear()
            text = "\n".join([f"{item['interval'].strftime('%b-%d-%Y %H%MZ')}: {item.get('error', 'Unknown')}"
                            for item in self.failed_intervals])
            failed_window.clipboard_append(text)
            messagebox.showinfo("Copied", "Failed downloads copied to clipboard")

        ttk.Button(button_frame, text="Copy to Clipboard", command=copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=failed_window.destroy).pack(side=tk.RIGHT, padx=5)


def main():
    root = tk.Tk()
    app = LiveATCDownloaderGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
