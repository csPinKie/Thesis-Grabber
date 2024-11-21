# -*- coding: utf-8 -*-
"""Created on Wed Nov 20 10:45:52 2024
@author: DHEBLIK & KAI
Version: 0.9 (2024)

Beschreibung:
Dieses Tool dient dazu, PDF-Dateien aus einem Quellverzeichnis zu durchsuchen und alle Thesis-bezogenen PDFs in ein Zielverzeichnis zu kopieren.
Es bietet die Möglichkeit, nur Thesis-Dateien oder alle PDFs zu kopieren und ermöglicht das Abbrechen des Vorgangs.
"""

import os
import shutil
import re
import hashlib
from datetime import datetime
import threading
import tkinter as tk
from tkinter import PhotoImage
from tkinter import filedialog, messagebox

# Maximale Pfadlänge für Windows
MAX_PATH_LENGTH = 260

# Standard-Pfad zum Quellverzeichnis
default_source_dir = r"Downloads"

# Muster für unerwünschte Wörter
unwanted_general_patterns = re.compile(r'(buch|Messung|Versuch|Norm|VDI|\bDIN\b|\bISO\b)', re.IGNORECASE)

# Wörter für den Thesis-Ordner
thesis_keywords = [
    'Thesis', 'BA ', 'MA ', 'DA ', 'BA_', 'MA_', 'DA_', 'BA-', 'MA-', 'DA-',
    'Dissertation', 'Doktor', 'Diplom', 'Master', 'Bachelor', 'Arbeit' 
    'Bachelorarbeit', 'Masterarbeit', 'Diplomarbeit',
    'Doktorarbeit', 'Dissertation', 'Habilitationsschrift',
    'Projektarbeit', 'Hausarbeit', 'Seminararbeit',
    'Facharbeit', 'Abschlussarbeit', 'Studienarbeit',
    'Examensarbeit', 'Staatsexamensarbeit', 'Magisterarbeit',
    'Zulassungsarbeit', 'Semesterarbeit', 'Forschungsarbeit',
    'Praktikumsbericht', 'Promotion', 'Promotionsarbeit',
    'Lizentiatsarbeit', 'Technikerarbeit',

]
thesis_pattern = re.compile('|'.join(thesis_keywords), re.IGNORECASE)

# Funktion zum Überprüfen der Pfadlänge
def is_path_too_long(path):
    return len(path) > MAX_PATH_LENGTH

# Funktion zum Kopieren von Dateien
def copy_files(src, dst):
    try:
        if is_path_too_long(dst):
            print(f"Überspringe Kopieren (Zielpfad zu lang): {dst}")
            return
        if os.path.exists(dst):
            base, extension = os.path.splitext(dst)
            counter = 1
            new_dst = f"{base}_{counter}{extension}"
            while os.path.exists(new_dst) or is_path_too_long(new_dst):
                counter += 1
                new_dst = f"{base}_{counter}{extension}"
            dst = new_dst
        shutil.copy2(src, dst)
        print(f"Kopiert: {src} -> {dst}")
    except FileNotFoundError:
        print(f"Fehler: Datei nicht gefunden - {src}")
    except Exception as e:
        print(f"Fehler beim Kopieren von {src} nach {dst}: {e}")

# Funktion zur Normalisierung und Hashing von Dateinamen
def hash_filename(filename):
    # Entferne Zahlen, Unterstriche, Bindestriche, Klammern und zusätzliche Leerzeichen
    filename = re.sub(r'[\d\_\-\(\)]', '', filename)
    filename = re.sub(r'\s+', '', filename)
    filename = filename.lower()
    # Erstelle einen Hash
    return hashlib.md5(filename.encode('utf-8')).hexdigest()

# Cancel Event für das Backup
cancel_event = threading.Event()

# Hauptfunktion für den Kopiervorgang
def start_backup(source_dir, target_dir, save_non_thesis_files):
    # Wörterbuch zum Speichern von Hashes und Dateiinformationen
    thesis_files = {}

    # Erstelle Thesis-Verzeichnis im Zielverzeichnis
    thesis_dir = os.path.join(target_dir, "Thesis")
    os.makedirs(thesis_dir, exist_ok=True)

    # Verzeichnisse, die übersprungen werden sollen
    excluded_dirs = {"Python", "Pandas", "Code_Docker", "venv", "Ansys"}

    # Durchsuche das Quellverzeichnis und alle Unterverzeichnisse nach .pdf-Dateien
    for root, dirs, files in os.walk(source_dir):
        if cancel_event.is_set():
            print("Backup abgebrochen.")
            break

        if is_path_too_long(root):
            print(f"Überspringe Verzeichnis (Pfad zu lang): {root}")
            continue

        # Verzeichnisse frühzeitig ausschließen
        dirs[:] = [d for d in dirs if d not in excluded_dirs and not is_path_too_long(os.path.join(root, d))]

        print(f"Durchsuche Verzeichnis: {root}")

        for file in files:
            if cancel_event.is_set():
                print("Backup abgebrochen.")
                break
            if not file.lower().endswith(".pdf"):
                continue
            source_file = os.path.join(root, file)
            if is_path_too_long(source_file):
                print(f"Überspringe Datei (Pfad zu lang): {source_file}")
                continue
            filename_without_ext = os.path.splitext(file)[0]
            # Existenzprüfung vor Zugriff
            if not os.path.exists(source_file):
                print(f"Überspringe Datei (existiert nicht): {source_file}")
                continue
            # Überprüfen, ob der Dateiname unerwünschte Wörter enthält
            if unwanted_general_patterns.search(filename_without_ext):
                print(f"Überspringe Datei (unerwünschte Wörter): {source_file}")
                continue
            # Prüfen, ob der Dateiname eines der Thesis-Schlüsselwörter enthält
            if thesis_pattern.search(filename_without_ext):
                try:
                    file_size_mb = os.path.getsize(source_file) / (1024 * 1024)
                    src_mtime = os.path.getmtime(source_file)
                except FileNotFoundError:
                    print(f"Überspringe Datei (Fehler beim Zugriff): {source_file}")
                    continue
                if file_size_mb < 1:
                    print(f"Überspringe Datei (kleiner als 1 MB): {source_file}")
                    continue
                filename_hash = hash_filename(filename_without_ext)
                if filename_hash in thesis_files:
                    existing_file_info = thesis_files[filename_hash]
                    if src_mtime > existing_file_info['mtime']:
                        try:
                            print(f"Ersetze ältere Datei: {existing_file_info['path']} mit {source_file}")
                            os.remove(existing_file_info['path'])
                        except Exception as e:
                            print(f"Fehler beim Löschen von {existing_file_info['path']}: {e}")
                            continue
                        target_file = os.path.join(thesis_dir, os.path.basename(source_file))
                        if is_path_too_long(target_file):
                            print(f"Überspringe Kopieren (Zielpfad zu lang): {target_file}")
                            continue
                        copy_files(source_file, target_file)
                        thesis_files[filename_hash] = {'path': target_file, 'mtime': src_mtime}
                    else:
                        print(f"Überspringe Datei (ältere Version): {source_file}")
                        continue
                else:
                    target_file = os.path.join(thesis_dir, os.path.basename(source_file))
                    if is_path_too_long(target_file):
                        print(f"Überspringe Kopieren (Zielpfad zu lang): {target_file}")
                        continue
                    copy_files(source_file, target_file)
                    thesis_files[filename_hash] = {'path': target_file, 'mtime': src_mtime}
            else:
                if not save_non_thesis_files:
                    print(f"Überspringe Datei (Nicht-Thesis-Datei): {source_file}")
                    continue
                try:
                    file_size_mb = os.path.getsize(source_file) / (1024 * 1024)
                    src_mtime = os.path.getmtime(source_file)
                except FileNotFoundError:
                    print(f"Überspringe Datei (Fehler beim Zugriff): {source_file}")
                    continue
                target_file = os.path.join(target_dir, os.path.basename(source_file))
                if is_path_too_long(target_file):
                    print(f"Überspringe Kopieren (Zielpfad zu lang): {target_file}")
                    continue
                print(f"Gefundene PDF-Datei: {source_file}")
                copy_files(source_file, target_file)

    print(f"Backup abgeschlossen. Dateien wurden in {target_dir} gespeichert.")
    messagebox.showinfo("Fertig", f"Backup abgeschlossen.\nDateien wurden in {target_dir} gespeichert.")
    # Buttons wieder aktivieren/deaktivieren
    button_start.config(state=tk.NORMAL)
    button_cancel.config(state=tk.DISABLED)

# Funktion zum Auswählen des Quellverzeichnisses
def select_source_directory():
    directory = filedialog.askdirectory(initialdir=default_source_dir)
    if directory:
        entry_source_dir.delete(0, tk.END)
        entry_source_dir.insert(0, directory)

# Funktion zum Auswählen des Zielverzeichnisses
def select_target_directory():
    directory = filedialog.askdirectory()
    if directory:
        entry_target_dir.delete(0, tk.END)
        entry_target_dir.insert(0, directory)

# Funktion zum Starten des Backups in einem Thread
def start_backup_thread():
    source_dir = entry_source_dir.get()
    target_dir = entry_target_dir.get()
    save_non_thesis_files = var_save_all_pdfs.get()
    if not source_dir:
        messagebox.showwarning("Warnung", "Bitte wählen Sie ein Quellverzeichnis aus.")
        return
    if not target_dir:
        messagebox.showwarning("Warnung", "Bitte wählen Sie ein Zielverzeichnis aus.")
        return
    if not os.path.exists(source_dir):
        messagebox.showerror("Fehler", f"Quellverzeichnis existiert nicht:\n{source_dir}")
        return
    if not os.path.exists(target_dir):
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Fehler", f"Kann Zielverzeichnis nicht erstellen:\n{e}")
            return
    # Starten des Backups in einem separaten Thread
    cancel_event.clear()
    threading.Thread(target=start_backup, args=(source_dir, target_dir, save_non_thesis_files), daemon=True).start()
    # Buttons aktivieren/deaktivieren
    button_start.config(state=tk.DISABLED)
    button_cancel.config(state=tk.NORMAL)

# Funktion zum Abbrechen des Backups
def cancel_backup():
    cancel_event.set()
    button_cancel.config(state=tk.DISABLED)
    button_start.config(state=tk.NORMAL)
    print("Backup wird abgebrochen...")

# Tooltip-Klasse
class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.top = None
    def enter(self, event=None):
        x = y = 0
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.top = tk.Toplevel(self.widget)
        self.top.overrideredirect(True)
        self.top.geometry("+%d+%d" % (x, y))
        label = tk.Label(self.top, text=self.text, justify='left',
                       background="#ffffe0", relief='solid', borderwidth=1,
                       font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)
    def leave(self, event=None):
        if self.top:
            self.top.destroy()

# Erstelle die GUI
root = tk.Tk()
root.title("Thesis Backup Tool")

# Farben anpassen (Mercedes-Farben)
background_color = "#000000"  # Schwarz
foreground_color = "#C0C0C0"  # Silber

root.configure(bg=background_color)

# Fenstergröße fixieren
root.resizable(False, False)

# Beschreibung hinzufügen
label_description = tk.Label(root, text="Dieses Tool kopiert alle Thesis-bezogenen PDF-Dateien aus dem Quellverzeichnis in ein Zielverzeichnis.", wraplength=500, bg=background_color, fg=foreground_color)
label_description.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

# Labels und Eingabefelder
label_source_dir = tk.Label(root, text="Quellverzeichnis:", bg=background_color, fg=foreground_color)
label_source_dir.grid(row=1, column=0, padx=10, pady=5, sticky="e")

entry_source_dir = tk.Entry(root, width=50, bg=foreground_color, fg=background_color)
entry_source_dir.grid(row=1, column=1, padx=10, pady=5)
entry_source_dir.insert(0, default_source_dir)

button_browse_source = tk.Button(root, text="Durchsuchen...", command=select_source_directory, bg=foreground_color, fg=background_color)
button_browse_source.grid(row=1, column=2, padx=10, pady=5)

# Fragezeichen mit Tooltip für Quellverzeichnis
label_source_help = tk.Label(root, text="?", fg="blue", cursor="question_arrow", bg=background_color)
label_source_help.grid(row=1, column=3, padx=5, pady=5)
ToolTip(label_source_help, text="Wählen Sie das Quellverzeichnis aus, von dem die PDFs kopiert werden sollen.")

label_target_dir = tk.Label(root, text="Zielverzeichnis:", bg=background_color, fg=foreground_color)
label_target_dir.grid(row=2, column=0, padx=10, pady=5, sticky="e")

entry_target_dir = tk.Entry(root, width=50, bg=foreground_color, fg=background_color)
entry_target_dir.grid(row=2, column=1, padx=10, pady=5)

button_browse_target = tk.Button(root, text="Durchsuchen...", command=select_target_directory, bg=foreground_color, fg=background_color)
button_browse_target.grid(row=2, column=2, padx=10, pady=5)

# Fragezeichen mit Tooltip für Zielverzeichnis
label_target_help = tk.Label(root, text="?", fg="blue", cursor="question_arrow", bg=background_color)
label_target_help.grid(row=2, column=3, padx=5, pady=5)
ToolTip(label_target_help, text="Wählen Sie das Zielverzeichnis aus, in das die PDFs kopiert werden sollen.\nEin 'Thesis'-Ordner wird darin erstellt.")

# Checkbox für Speichern aller PDFs
var_save_all_pdfs = tk.BooleanVar(value=False)
checkbox_save_all_pdfs = tk.Checkbutton(root, text="Alle PDFs speichern", variable=var_save_all_pdfs, bg=background_color, fg=foreground_color, selectcolor=background_color)
checkbox_save_all_pdfs.grid(row=3, column=1, padx=10, pady=5)

# Fragezeichen mit Tooltip für Checkbox
label_save_all_help = tk.Label(root, text="?", fg="blue", cursor="question_arrow", bg=background_color)
label_save_all_help.grid(row=3, column=2, padx=5, pady=5)
ToolTip(label_save_all_help, text="Wenn aktiviert, werden alle PDFs gespeichert, nicht nur Thesis-Dateien.")

# Start- und Abbrechen-Buttons
button_start = tk.Button(root, text="Backup starten", command=start_backup_thread, bg=foreground_color, fg=background_color)
button_start.grid(row=4, column=1, padx=10, pady=10)

button_cancel = tk.Button(root, text="Abbrechen", command=cancel_backup, state=tk.DISABLED, bg=foreground_color, fg=background_color)
button_cancel.grid(row=4, column=2, padx=10, pady=10)

# Credits und Version
label_credits = tk.Label(root, text="Made by csPinKie & koreanski, Version 0.8 (2024)", bg=background_color, fg=foreground_color)
label_credits.grid(row=5, column=0, columnspan=4, padx=10, pady=10)

# Hauptschleife starten
root.mainloop()
