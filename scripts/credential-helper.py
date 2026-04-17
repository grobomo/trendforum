#!/usr/bin/env python3
"""Tkinter GUI to securely store Entra ID credentials in Linux keyring.

Displays on Windows via WSLg. Values go straight to gnome-keyring,
never touch disk.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys


def store_in_keyring(service: str, key: str, value: str) -> bool:
    """Store a secret in the Linux keyring via secret-tool."""
    try:
        proc = subprocess.run(
            ["secret-tool", "store", "--label", f"{service}/{key}", "service", service, "key", key],
            input=value.encode(),
            capture_output=True,
            timeout=10,
        )
        return proc.returncode == 0
    except Exception as e:
        print(f"Error storing {key}: {e}", file=sys.stderr)
        return False


def lookup_in_keyring(service: str, key: str) -> str:
    """Check if a value exists in keyring."""
    try:
        proc = subprocess.run(
            ["secret-tool", "lookup", "service", service, "key", key],
            capture_output=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return "••••••••"
        return ""
    except Exception:
        return ""


class CredentialHelper:
    SERVICE = "openclaw"

    FIELDS = [
        ("ENTRA_TENANT_ID", "Tenant ID"),
        ("ENTRA_CLIENT_ID", "Client ID (Application ID)"),
        ("ENTRA_CLIENT_SECRET", "Client Secret"),
    ]

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🌴 Coconut Credential Manager")
        self.root.geometry("520x350")
        self.root.resizable(False, False)

        # Style
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10))

        # Title
        title = ttk.Label(self.root, text="🌴 Coconut Policy Guard — Entra ID", style="Title.TLabel")
        title.pack(pady=(15, 5))

        subtitle = ttk.Label(self.root, text="Paste each value below. Saved directly to Linux keyring (never on disk).")
        subtitle.pack(pady=(0, 15))

        # Fields
        self.entries = {}
        frame = ttk.Frame(self.root)
        frame.pack(padx=30, fill="x")

        for i, (key, label) in enumerate(self.FIELDS):
            existing = lookup_in_keyring(self.SERVICE, key)
            lbl = ttk.Label(frame, text=f"{label}:")
            lbl.grid(row=i, column=0, sticky="w", pady=5)

            entry = ttk.Entry(frame, width=45, show="•")
            entry.grid(row=i, column=1, sticky="ew", pady=5, padx=(10, 0))
            if existing:
                entry.insert(0, existing)
            self.entries[key] = entry

        frame.columnconfigure(1, weight=1)

        # Toggle show/hide
        self.show_var = tk.BooleanVar(value=False)
        show_cb = ttk.Checkbutton(self.root, text="Show values", variable=self.show_var, command=self.toggle_show)
        show_cb.pack(pady=(10, 5))

        # Buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=15)

        save_btn = ttk.Button(btn_frame, text="💾 Save to Keyring", command=self.save_all)
        save_btn.grid(row=0, column=0, padx=10)

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.root.quit)
        cancel_btn.grid(row=0, column=1, padx=10)

        # Status
        self.status_var = tk.StringVar(value="")
        status_lbl = ttk.Label(self.root, textvariable=self.status_var, style="Status.TLabel")
        status_lbl.pack(pady=(5, 10))

    def toggle_show(self):
        show = "" if self.show_var.get() else "•"
        for entry in self.entries.values():
            entry.config(show=show)

    def save_all(self):
        saved = 0
        errors = []
        for key, entry in self.entries.items():
            val = entry.get().strip()
            if val and val != "••••••••":
                if store_in_keyring(self.SERVICE, key, val):
                    saved += 1
                else:
                    errors.append(key)

        if errors:
            messagebox.showerror("Error", f"Failed to store: {', '.join(errors)}")
        elif saved == 0:
            self.status_var.set("Nothing new to save.")
        else:
            self.status_var.set(f"✅ {saved} credential(s) saved to keyring!")
            messagebox.showinfo("Success", f"Saved {saved} credential(s) to keyring.\nWindow will close.")
            self.root.after(500, self.root.quit)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = CredentialHelper()
    app.run()
