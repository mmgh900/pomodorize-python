import customtkinter as ctk
import time
import ctypes
from PIL import Image, ImageTk
import pygame
import datetime
from datetime import timedelta
import json
from typing import Dict, List, Any, Optional

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("matrial.json")


class PomodoroApp:
    def __init__(self, master: ctk.CTk) -> None:
        self.master: ctk.CTk = master
        self.master.title("Pomodoro Timer")
        self.master.geometry("800x600")

        self.work_time: ctk.StringVar = ctk.StringVar(value="25")
        self.short_break_time: ctk.StringVar = ctk.StringVar(value="5")
        self.long_break_time: ctk.StringVar = ctk.StringVar(value="20")
        self.cycles: ctk.IntVar = ctk.IntVar(value=0)
        self.current_cycle: ctk.IntVar = ctk.IntVar(value=1)

        self.timer_running: bool = False
        self.current_timer: Optional[str] = None
        self.remaining_time: int = 0
        self.timer_type: str = "Work"

        # Initialize pygame mixer for sound
        pygame.mixer.init()
        self.start_sound: pygame.mixer.Sound = pygame.mixer.Sound("start_work.mp3")
        self.end_sound: pygame.mixer.Sound = pygame.mixer.Sound("end_work.mp3")
        self.end_break_sound: pygame.mixer.Sound = pygame.mixer.Sound("end_work.mp3")

        # Load or initialize user data
        self.load_user_data()

        self.create_widgets()

    def create_widgets(self) -> None:
        self.notebook: ctk.CTkTabview = ctk.CTkTabview(self.master)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=20)

        self.timer_tab: ctk.CTkFrame = self.notebook.add("Timer")
        self.stats_tab: ctk.CTkFrame = self.notebook.add("Stats")

        self.create_timer_tab()
        self.create_stats_tab()

    def create_timer_tab(self) -> None:
        frame: ctk.CTkFrame = ctk.CTkFrame(self.timer_tab)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Pomodoro Timer", font=("Arial", 24, "bold")).pack(pady=10)

        settings_frame: ctk.CTkFrame = ctk.CTkFrame(frame)
        settings_frame.pack(pady=10)

        ctk.CTkLabel(settings_frame, text="Work Time (minutes):").grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkEntry(settings_frame, textvariable=self.work_time, width=50).grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(settings_frame, text="Short Break (minutes):").grid(row=1, column=0, padx=5, pady=5)
        ctk.CTkEntry(settings_frame, textvariable=self.short_break_time, width=50).grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(settings_frame, text="Long Break (minutes):").grid(row=2, column=0, padx=5, pady=5)
        ctk.CTkEntry(settings_frame, textvariable=self.long_break_time, width=50).grid(row=2, column=1, padx=5, pady=5)

        self.time_label: ctk.CTkLabel = ctk.CTkLabel(frame, text="25:00", font=("Arial", 48, "bold"))
        self.time_label.pack(pady=20)

        self.cycle_label: ctk.CTkLabel = ctk.CTkLabel(frame, text="Cycle: 1 / 4", font=("Arial", 18))
        self.cycle_label.pack()

        self.progress_bar: ctk.CTkProgressBar = ctk.CTkProgressBar(frame, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=20)

        button_frame: ctk.CTkFrame = ctk.CTkFrame(frame)
        button_frame.pack(pady=10)

        self.start_button: ctk.CTkButton = ctk.CTkButton(button_frame, text="Start", command=self.start_timer,
                                                         width=120)
        self.start_button.pack(side="left", padx=10)

        self.reset_button: ctk.CTkButton = ctk.CTkButton(button_frame, text="Reset", command=self.reset_timer,
                                                         width=120)
        self.reset_button.pack(side="left", padx=10)

        self.pause_button: ctk.CTkButton = ctk.CTkButton(button_frame, text="Pause", command=self.pause_timer,
                                                         width=120)
        self.pause_button.pack(side="left", padx=10)

        self.coins_label: ctk.CTkLabel = ctk.CTkLabel(frame, text=f"Coins: {self.user_data['coins']}",
                                                      font=("Arial", 18))
        self.coins_label.pack(pady=10)

    def pause_timer(self) -> None:
        if self.timer_running:
            self.timer_running = False
            self.pause_button.configure(text="Resume", command=self.resume_timer)

    def resume_timer(self) -> None:
        if not self.timer_running:
            self.timer_running = True
            self.pause_button.configure(text="Pause", command=self.pause_timer)
            self.countdown(self.remaining_time)

    def create_stats_tab(self) -> None:
        frame: ctk.CTkFrame = ctk.CTkFrame(self.stats_tab)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Statistics", font=("Arial", 24, "bold")).pack(pady=10)

        self.stats_text: ctk.CTkTextbox = ctk.CTkTextbox(frame, height=200)
        self.stats_text.pack(pady=10, fill="x")

        self.update_stats_display()

    def start_timer(self) -> None:
        if not self.timer_running:
            self.timer_running = True
            self.start_button.configure(text="Stop", command=self.stop_timer)
            if self.timer_type == "Work":
                self.start_sound.play()
                self.run_work_timer()
            else:
                self.run_work_timer()  # Start next work cycle if we were in a break

    def stop_timer(self) -> None:
        if self.timer_running:
            self.timer_running = False
            self.start_button.configure(text="Start", command=self.start_timer)
            if self.current_timer:
                self.master.after_cancel(self.current_timer)
            if self.timer_type != "Work":
                self.prepare_next_work_cycle()

    def reset_timer(self) -> None:
        self.stop_timer()
        self.cycles.set(0)
        self.current_cycle.set(1)
        self.timer_type = "Work"
        self.remaining_time = int(self.work_time.get()) * 60
        self.update_display()
        self.cycle_label.configure(text=f"Cycle: 1 / 4")
        self.progress_bar.set(0)

    def run_work_timer(self) -> None:
        self.timer_type = "Work"
        self.remaining_time = int(float(self.work_time.get()) * 60)
        self.countdown(self.remaining_time)

    def run_break_timer(self) -> None:
        if self.current_cycle.get() % 4 == 0:
            self.timer_type = "Long Break"
            self.remaining_time = int(float(self.long_break_time.get()) * 60)
        else:
            self.timer_type = "Short Break"
            self.remaining_time = int(float(self.short_break_time.get()) * 60)
        self.countdown(self.remaining_time)

    def prepare_next_work_cycle(self) -> None:
        self.timer_type = "Work"
        self.current_cycle.set((self.current_cycle.get() % 4) + 1)
        self.cycle_label.configure(text=f"Cycle: {self.current_cycle.get()} / 4")
        self.remaining_time = int(float(self.work_time.get()) * 60)
        self.update_display()

    def countdown(self, seconds: int) -> None:
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
                self.end_break_sound.play()
                self.prepare_next_work_cycle()
                self.start_button.configure(text="Start", command=self.start_timer)
                self.timer_running = False

    def update_display(self) -> None:
        mins, secs = divmod(self.remaining_time, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self.time_label.configure(text=f"{time_str} - {self.timer_type}")

        if self.timer_type == "Work":
            total_seconds = int(float(self.work_time.get()) * 60)
        elif self.timer_type == "Long Break":
            total_seconds = int(float(self.long_break_time.get()) * 60)
        else:
            total_seconds = int(float(self.short_break_time.get()) * 60)

        progress = (total_seconds - self.remaining_time) / total_seconds
        self.progress_bar.set(progress)

    def lock_screen(self) -> None:
        ctypes.windll.user32.LockWorkStation()

    def record_work_session(self) -> None:
        now = datetime.datetime.now()
        duration = int(float(self.work_time.get()) * 60)  # Convert to seconds
        self.user_data['sessions'].append({
            'date': now.strftime('%Y-%m-%d'),
            'start_time': (now - datetime.timedelta(seconds=duration)).strftime('%H:%M'),
            'end_time': now.strftime('%H:%M'),
            'duration': duration / 60  # Convert back to minutes for storage
        })

        self.user_data['coins'] += duration / 60  # Coins added equal to cycle minutes
        self.coins_label.configure(text=f"Coins: {self.user_data['coins']}")
        self.save_user_data()
        self.update_stats_display()

    def update_stats_display(self) -> None:
        stats_text = "Recent Work Sessions:\n\n"
        total_work_time = 0
        for session in self.user_data['sessions'][-5:]:  # Show last 5 sessions
            stats_text += f"Date: {session['date']}, Time: {session['start_time']} - {session['end_time']}, Duration: {session['duration']} minutes\n"
            if session['date'] == datetime.datetime.now().strftime('%Y-%m-%d'):
                total_work_time += session['duration']
        stats_text += f"\nTotal work time today: {total_work_time} minutes"
        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", stats_text)

    def load_user_data(self) -> None:
        try:
            with open('user_data.json', 'r') as f:
                self.user_data: Dict[str, Any] = json.load(f)
        except FileNotFoundError:
            self.user_data = {'coins': 0, 'sessions': []}

    def save_user_data(self) -> None:
        with open('user_data.json', 'w') as f:
            json.dump(self.user_data, f)


if __name__ == "__main__":
    root: ctk.CTk = ctk.CTk()
    app: PomodoroApp = PomodoroApp(root)
    root.mainloop()