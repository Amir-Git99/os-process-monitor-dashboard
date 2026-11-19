import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import psutil

# --- Configuration ---
ADMIN_PIN = "1234"
CPU_THRESHOLD = 20.0   # Highlight red if CPU > 20%
RAM_THRESHOLD = 300.0  # Highlight red if RAM > 300 MB
LOG_FILE = "termination_log.txt"


class ProcessMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OS Process Monitoring & Management Dashboard")
        self.root.geometry("880x560")
        self.root.configure(bg="#1e1e2e")

        self.is_authorized = False
        self.search_var = tk.StringVar()

        self.setup_ui()
        self.update_stats()

    def setup_ui(self):
        # --- Top Header & System Summary ---
        header_frame = tk.Frame(self.root, bg="#1e1e2e", pady=10)
        header_frame.pack(fill="x", padx=15)

        title_lbl = tk.Label(
            header_frame, text="System Process Monitor",
            font=("Segoe UI", 16, "bold"), fg="#cdd6f4", bg="#1e1e2e"
        )
        title_lbl.pack(side="left")

        self.sys_info_lbl = tk.Label(
            header_frame, text="Total CPU: 0% | Total RAM: 0%",
            font=("Segoe UI", 11, "bold"), fg="#a6e3a1", bg="#1e1e2e"
        )
        self.sys_info_lbl.pack(side="right")

        # --- Search, Filter & Legend Bar ---
        control_frame = tk.Frame(self.root, bg="#1e1e2e", pady=5)
        control_frame.pack(fill="x", padx=15)

        tk.Label(control_frame, text="Search Process:", fg="#cdd6f4", bg="#1e1e2e", font=("Segoe UI", 10)).pack(side="left")
        search_entry = tk.Entry(control_frame, textvariable=self.search_var, width=28, font=("Segoe UI", 10))
        search_entry.pack(side="left", padx=10)

        refresh_btn = tk.Button(
            control_frame, text="Refresh Now", command=self.populate_processes,
            bg="#89b4fa", fg="#11111b", font=("Segoe UI", 9, "bold"), padx=10
        )
        refresh_btn.pack(side="left", padx=5)

        legend_lbl = tk.Label(
            control_frame,
            text=f"Alert Threshold: CPU > {CPU_THRESHOLD}% or RAM > {RAM_THRESHOLD} MB",
            fg="#f38ba8", bg="#1e1e2e", font=("Segoe UI", 9, "italic")
        )
        legend_lbl.pack(side="right")

        # --- Process Table (Treeview) ---
        table_frame = tk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=15, pady=10)

        columns = ("pid", "name", "status", "cpu", "memory")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        # Configure Red Alert Tag for High Resource Usage
        self.tree.tag_configure("high_usage", background="#ffd6d6", foreground="#990000")

        # Define Headings
        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="Process Name")
        self.tree.heading("status", text="Status")
        self.tree.heading("cpu", text="CPU (%)")
        self.tree.heading("memory", text="Memory (MB)")

        # Define Column Widths
        self.tree.column("pid", width=80, anchor="center")
        self.tree.column("name", width=310, anchor="w")
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("cpu", width=100, anchor="center")
        self.tree.column("memory", width=120, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # --- Bottom Action Bar ---
        bottom_frame = tk.Frame(self.root, bg="#1e1e2e", pady=10)
        bottom_frame.pack(fill="x", padx=15)

        self.auth_status_lbl = tk.Label(
            bottom_frame, text="Status: Unauthorized (Read-Only)",
            fg="#f38ba8", bg="#1e1e2e", font=("Segoe UI", 10, "bold")
        )
        self.auth_status_lbl.pack(side="left")

        terminate_btn = tk.Button(
            bottom_frame, text="Terminate Selected Process", command=self.terminate_process,
            bg="#f38ba8", fg="#11111b", font=("Segoe UI", 10, "bold"), padx=15, pady=5
        )
        terminate_btn.pack(side="right")

    def log_action(self, pid, name, action_type):
        """Appends a timestamped termination record to termination_log.txt."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {action_type} | PID: {pid} | Process: {name}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def populate_processes(self):
        # Save currently selected PID so selection doesn't jump on refresh
        selected_item = self.tree.selection()
        selected_pid = self.tree.item(selected_item[0])['values'][0] if selected_item else None

        # Clear existing rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        search_query = self.search_var.get().lower()
        processes = []

        # Fetch all running processes from the OS
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_info']):
            try:
                info = proc.info
                name = info['name'] or "Unknown"
                if search_query and search_query not in name.lower():
                    continue

                pid = info['pid']
                status = info['status']
                cpu = info['cpu_percent'] or 0.0
                mem_mb = round(info['memory_info'].rss / (1024 * 1024), 2) if info['memory_info'] else 0.0

                processes.append((pid, name, status, cpu, mem_mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Sort processes by highest CPU usage first
        processes.sort(key=lambda x: x[3], reverse=True)

        # Insert into UI table and apply red highlight if thresholds are exceeded
        for p in processes:
            pid, name, status, cpu, mem_mb = p
            row_tags = ("high_usage",) if (cpu > CPU_THRESHOLD or mem_mb > RAM_THRESHOLD) else ()
            item_id = self.tree.insert("", "end", values=p, tags=row_tags)

            if pid == selected_pid:
                self.tree.selection_set(item_id)

    def update_stats(self):
        total_cpu = psutil.cpu_percent(interval=None)
        total_ram = psutil.virtual_memory().percent
        self.sys_info_lbl.config(text=f"Total CPU: {total_cpu}%  |  Total RAM: {total_ram}%")

        self.populate_processes()
        self.root.after(3000, self.update_stats)

    def verify_authorization(self):
        if self.is_authorized:
            return True
        pin = simpledialog.askstring("Authorization Required", "Enter Admin PIN to manage processes:", show="*")
        if pin == ADMIN_PIN:
            self.is_authorized = True
            self.auth_status_lbl.config(text="Status: Authorized Admin", fg="#a6e3a1")
            return True
        elif pin is not None:
            messagebox.showerror("Access Denied", "Incorrect PIN! You are not authorized to terminate processes.")
        return False

    def terminate_process(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a process from the list first.")
            return

        # Step 1: Check user authorization
        if not self.verify_authorization():
            return

        # Step 2: Get PID and Name
        values = self.tree.item(selected[0])['values']
        pid = int(values[0])
        name = values[1]

        # Step 3: Confirm, Terminate, and Log
        confirm = messagebox.askyesno("Confirm Termination", f"Are you sure you want to terminate '{name}' (PID: {pid})?")
        if confirm:
            try:
                proc = psutil.Process(pid)
                proc.terminate()  # Sends SIGTERM (graceful termination)
                proc.wait(timeout=3)
                self.log_action(pid, name, "TERMINATED (SIGTERM)")
                messagebox.showinfo("Success", f"Process '{name}' (PID: {pid}) terminated and logged.")
                self.populate_processes()
            except psutil.TimeoutExpired:
                proc.kill()  # Force kill (SIGKILL)
                self.log_action(pid, name, "FORCE KILLED (SIGKILL)")
                messagebox.showinfo("Force Killed", f"Process '{name}' (PID: {pid}) was unresponsive, force-killed, and logged.")
                self.populate_processes()
            except psutil.AccessDenied:
                messagebox.showerror("Permission Error", f"OS Denied Access! Run the dashboard as Administrator/Root to kill '{name}'.")
            except psutil.NoSuchProcess:
                messagebox.showinfo("Info", "Process already ended.")
                self.populate_processes()


if __name__ == "__main__":
    root = tk.Tk()
    app = ProcessMonitorApp(root)
    root.mainloop()