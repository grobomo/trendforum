#!/usr/bin/env python3
"""GUI credential manager for Entra ID app secrets → Linux keyring."""

import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox

FIELDS = [
    ("ENTRA_TENANT_ID",  "Tenant ID (Directory ID)"),
    ("ENTRA_CLIENT_ID",  "Client ID (Application ID)"),
    ("ENTRA_CLIENT_SECRET", "Client Secret"),
]

KEYRING_ATTR = "application"
KEYRING_APP  = "openclaw"


def store_secret(key: str, value: str) -> bool:
    """Store a value in gnome-keyring via secret-tool."""
    try:
        proc = subprocess.run(
            ["secret-tool", "store", "--label", f"openclaw/{key}", KEYRING_ATTR, KEYRING_APP, "key", key],
            input=value.encode(),
            capture_output=True,
            timeout=10,
        )
        return proc.returncode == 0
    except Exception as e:
        print(f"Error storing {key}: {e}", file=sys.stderr)
        return False


class CredentialManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("🥥 Coconut — Entra ID Credential Manager")
        root.resizable(False, False)

        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 11))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))

        frame = ttk.Frame(root, padding=20)
        frame.grid()

        ttk.Label(frame, text="🌴 Entra ID Credentials", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 15)
        )
        ttk.Label(frame, text="Paste each value below. They'll be stored\nin the Linux keyring (never plaintext).").grid(
            row=1, column=0, columnspan=2, pady=(0, 15)
        )

        self.entries: dict[str, tk.Entry] = {}
        for i, (key, label) in enumerate(FIELDS):
            row = i + 2
            ttk.Label(frame, text=label + ":").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
            entry = ttk.Entry(frame, width=50, show="•")
            entry.grid(row=row, column=1, pady=5)
            self.entries[key] = entry

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(FIELDS) + 2, column=0, columnspan=2, pady=(15, 0))

        self.toggle_btn = ttk.Button(btn_frame, text="👁 Show", command=self.toggle_show)
        self.toggle_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="💾 Save to Keyring", command=self.save_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=root.destroy).pack(side="left", padx=5)

        self._showing = False
        # Focus first field
        self.entries[FIELDS[0][0]].focus()

    def toggle_show(self):
        self._showing = not self._showing
        char = "" if self._showing else "•"
        for entry in self.entries.values():
            entry.config(show=char)
        self.toggle_btn.config(text="🙈 Hide" if self._showing else "👁 Show")

    def save_all(self):
        errors = []
        empty = []
        for key, label in FIELDS:
            val = self.entries[key].get().strip()
            if not val:
                empty.append(label)
                continue
            if not store_secret(key, val):
                errors.append(label)

        if empty:
            messagebox.showwarning("Missing fields", f"These fields are empty:\n• " + "\n• ".join(empty))
            return

        if errors:
            messagebox.showerror("Error", f"Failed to store:\n• " + "\n• ".join(errors))
            return

        messagebox.showinfo("✅ Done", "All credentials saved to Linux keyring!\n\nYou can close this window.")
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CredentialManagerApp(root)
    root.mainloop()
