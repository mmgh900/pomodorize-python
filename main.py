import customtkinter as ctk
import time
import ctypes
from PIL import Image, ImageTk
import pygame
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import json

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class PomodoroApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Pomodoro Timer")
        self.master.geometry("800x600")

        self.work_time = ctk.StringVar(value="25")
        self.short_break_time = ctk.StringVar(value="5")
        self.long_break_time = ctk.StringVar(value="20")
        self.cycles = ctk.IntVar(value=0)
        self.current_cycle = ctk.IntVar(value=1)

        self.timer_running = False
        self.current_timer = None
        self.remaining_time = 0
        self.timer_type = "Work"

        # Initialize pygame mixer for sound
        pygame.mixer.init()
        self.start_sound = pygame.mixer.Sound("start_work.mp3")
        self.end_sound = pygame.mixer.Sound("end_work.mp3")

        # Load or initialize user data
        self.load_user_data()

        self.create_widgets()

    def create_widgets(self):
        self.notebook = ctk.CTkTabview(self.master)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=20)

        self.timer_tab = self.notebook.add("Timer")
        self.stats_tab = self.notebook.add("Stats")
        self.shop_tab = self.notebook.add("Shop")

        self.create_timer_tab()
        self.create_stats_tab()
        self.create_shop_tab()

    def create_timer_tab(self):
        frame = ctk.CTkFrame(self.timer_tab)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Pomodoro Timer", font=("Arial", 24, "bold")).pack(pady=10)

        settings_frame = ctk.CTkFrame(frame)
        settings_frame.pack(pady=10)

        ctk.CTkLabel(settings_frame, text="Work Time (minutes):").grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkEntry(settings_frame, textvariable=self.work_time, width=50).grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(settings_frame, text="Short Break (minutes):").grid(row=1, column=0, padx=5, pady=5)
        ctk.CTkEntry(settings_frame, textvariable=self.short_break_time, width=50).grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(settings_frame, text="Long Break (minutes):").grid(row=2, column=0, padx=5, pady=5)
        ctk.CTkEntry(settings_frame, textvariable=self.long_break_time, width=50).grid(row=2, column=1, padx=5, pady=5)

        self.time_label = ctk.CTkLabel(frame, text="25:00", font=("Arial", 48, "bold"))
        self.time_label.pack(pady=20)

        self.cycle_label = ctk.CTkLabel(frame, text="Cycle: 1 / 4", font=("Arial", 18))
        self.cycle_label.pack()

        self.progress_bar = ctk.CTkProgressBar(frame, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=20)

        button_frame = ctk.CTkFrame(frame)
        button_frame.pack(pady=10)

        self.start_button = ctk.CTkButton(button_frame, text="Start", command=self.start_timer, width=120)
        self.start_button.pack(side="left", padx=10)

        self.reset_button = ctk.CTkButton(button_frame, text="Reset", command=self.reset_timer, width=120)
        self.reset_button.pack(side="left", padx=10)

        self.coins_label = ctk.CTkLabel(frame, text=f"Coins: {self.user_data['coins']}", font=("Arial", 18))
        self.coins_label.pack(pady=10)

    def create_stats_tab(self):
        frame = ctk.CTkFrame(self.stats_tab)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Statistics", font=("Arial", 24, "bold")).pack(pady=10)

        self.stats_text = ctk.CTkTextbox(frame, height=200)
        self.stats_text.pack(pady=10, fill="x")

        self.update_stats_display()

        # Create a matplotlib figure for the chart
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(pady=10, fill="x")

        self.update_chart()

    def create_shop_tab(self):
        frame = ctk.CTkFrame(self.shop_tab)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Shop", font=("Arial", 24, "bold")).pack(pady=10)

        items = [
            ("Productivity Boost", 50),
            ("Focus Enhancer", 100),
            ("Time Wizard", 200),
        ]

        for item, cost in items:
            item_frame = ctk.CTkFrame(frame)
            item_frame.pack(pady=5, fill="x")

            ctk.CTkLabel(item_frame, text=item).pack(side="left", padx=10)
            ctk.CTkLabel(item_frame, text=f"Cost: {cost} coins").pack(side="left", padx=10)
            ctk.CTkButton(item_frame, text="Buy", command=lambda c=cost: self.buy_item(c)).pack(side="right", padx=10)

    def start_timer(self):
        if not self.timer_running:
            self.timer_running = True
            self.start_button.configure(text="Stop", command=self.stop_timer)
            if self.timer_type == "Work":
                self.start_sound.play()
                self.run_work_timer()
            else:
                self.run_work_timer()  # Start next work cycle if we were in a break

    def stop_timer(self):
        if self.timer_running:
            self.timer_running = False
            self.start_button.configure(text="Start", command=self.start_timer)
            if self.current_timer:
                self.master.after_cancel(self.current_timer)
            if self.timer_type != "Work":
                self.prepare_next_work_cycle()

    def reset_timer(self):
        self.stop_timer()
        self.cycles.set(0)
        self.current_cycle.set(1)
        self.timer_type = "Work"
        self.remaining_time = int(float(self.work_time.get())) * 60

        self.update_display()
        self.cycle_label.configure(text=f"Cycle: 1 / 4")
        self.progress_bar.set(0)

    def run_work_timer(self):
        self.timer_type = "Work"
        self.remaining_time = int(float(self.work_time.get()) * 60)
        self.countdown(self.remaining_time)

    def run_break_timer(self):
        if self.current_cycle.get() % 4 == 0:
            self.timer_type = "Long Break"
            self.remaining_time = int(float(self.long_break_time.get()) * 60)
        else:
            self.timer_type = "Short Break"
            self.remaining_time = int(float(self.short_break_time.get()) * 60)
        self.countdown(self.remaining_time)

    def prepare_next_work_cycle(self):
        self.timer_type = "Work"
        self.current_cycle.set((self.current_cycle.get() % 4) + 1)
        self.cycle_label.configure(text=f"Cycle: {self.current_cycle.get()} / 4")
        self.remaining_time = int(float(self.work_time.get()) * 60)
        self.update_display()

    def countdown(self, seconds):
        if seconds > 0 and self.timer_running:
            self.remaining_time = seconds
            self.update_display()
            self.current_timer = self.master.after(1000, self.countdown, seconds - 1)
        elif self.timer_running:
            if self.timer_type == "Work":
                self.end_sound.play()
                self.cycles.set(self.cycles.get() + 1)
                self.record_work_session()
                self.lock_screen()
                self.run_break_timer()
            else:
                self.prepare_next_work_cycle()
                self.start_sound.play()
                self.run_work_timer()

    def update_display(self):
        mins, secs = divmod(self.remaining_time, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self.time_label.configure(text=time_str)
        
        if self.timer_type == "Work":
            total_seconds = int(float(self.work_time.get()) * 60)
        elif self.timer_type == "Long Break":
            total_seconds = int(float(self.long_break_time.get()) * 60)
        else:
            total_seconds = int(float(self.short_break_time.get()) * 60)
        
        progress = (total_seconds - self.remaining_time) / total_seconds
        self.progress_bar.set(progress)

    def lock_screen(self):
        ctypes.windll.user32.LockWorkStation()

    def record_work_session(self):
        now = datetime.datetime.now()
        duration = int(float(self.work_time.get()) * 60)  # Convert to seconds
        self.user_data['sessions'].append({
            'date': now.strftime('%Y-%m-%d'),
            'start_time': (now - datetime.timedelta(seconds=duration)).strftime('%H:%M'),
            'end_time': now.strftime('%H:%M'),
            'duration': duration // 60  # Convert back to minutes for storage
        })
        self.user_data['coins'] += duration // 60  # Coins added equal to cycle minutes
        self.coins_label.configure(text=f"Coins: {self.user_data['coins']}")
        self.save_user_data()
        self.update_stats_display()
        self.update_chart()

    def update_stats_display(self):
        stats_text = "Recent Work Sessions:\n\n"
        total_work_time = 0
        for session in self.user_data['sessions'][-5:]:  # Show last 5 sessions
            stats_text += f"Date: {session['date']}, Time: {session['start_time']} - {session['end_time']}, Duration: {session['duration']} minutes\n"
            if session['date'] == datetime.datetime.now().strftime('%Y-%m-%d'):
                total_work_time += session['duration']
        stats_text += f"\nTotal work time today: {total_work_time} minutes"
        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", stats_text)

    def update_chart(self):
        dates = []
        durations = []
        for session in self.user_data['sessions'][-30:]:  # Last 30 sessions
            date = datetime.datetime.strptime(session['date'], '%Y-%m-%d').date()
            if date not in dates:
                dates.append(date)
                durations.append(session['duration'])
            else:
                index = dates.index(date)
                durations[index] += session['duration']

        self.ax.clear()
        self.ax.bar(dates, durations)
        self.ax.set_xlabel('Date')
        self.ax.set_ylabel('Work Duration (minutes)')
        self.ax.set_title('Work Duration per Day')
        plt.xticks(rotation=45)
        plt.tight_layout()
        self.canvas.draw()

    def buy_item(self, cost):
        if self.user_data['coins'] >= cost:
            self.user_data['coins'] -= cost
            self.coins_label.configure(text=f"Coins: {self.user_data['coins']}")
            self.save_user_data()
            ctk.CTkMessagebox(title="Success", message=f"Item purchased for {cost} coins!")
        else:
            ctk.CTkMessagebox(title="Error", message="Not enough coins to purchase this item.")

    def load_user_data(self):
        try:
            with open('user_data.json', 'r') as f:
                self.user_data = json.load(f)
        except FileNotFoundError:
            self.user_data = {'coins': 0, 'sessions': []}

    def save_user_data(self):
        with open('user_data.json', 'w') as f:
            json.dump(self.user_data, f)

if __name__ == "__main__":
    root = ctk.CTk()
    app = PomodoroApp(root)
    root.mainloop()