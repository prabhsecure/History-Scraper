#!/usr/bin/env python3
import os
import sqlite3
import shutil
import subprocess
from pathlib import Path
import csv

def find_firefox_places():
    base = Path.home() / ".mozilla/firefox"
    if not base.exists():
        return None
    for p in base.iterdir():
        if p.is_dir() and (p / "places.sqlite").exists():
            return p / "places.sqlite"
    return None

def find_chrome_history():
    base = Path.home() / ".config/google-chrome"
    if not base.exists():
        return None
    for p in base.rglob("History"):
        if p.is_file():
            return p
    return None

def copy_db(src, dst):
    try:
        shutil.copy(src, dst)
    except Exception:
        subprocess.run(["sqlite3", str(src), f".backup {dst}"])
    return dst

def parse_firefox(db_path, limit=50):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT url, datetime((visit_date/1000000), 'unixepoch') as vtime
        FROM moz_places, moz_historyvisits
        WHERE moz_places.id = moz_historyvisits.place_id
        ORDER BY vtime DESC
        LIMIT ?;
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def parse_chrome(db_path, limit=50):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT url, datetime((last_visit_time/1000000)-11644473600, 'unixepoch') as vtime
        FROM urls
        ORDER BY vtime DESC
        LIMIT ?;
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def save_csv(rows, out_file):
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["URL", "Visit Time"])
        writer.writerows(rows)
    return out_file

def main():
    print("=== Mini Browser History Forensic Tool (v2 Auto Detect) ===")
    print("Choose Browser:")
    print("1. Firefox")
    print("2. Chrome")
    choice = input("Enter 1 or 2: ")

    if choice == "1":
        print("[*] Searching for Firefox history...")
        src = find_firefox_places()
        if not src:
            print("[!] Firefox history not found in any profile!")
            return
        parser = parse_firefox

    elif choice == "2":
        print("[*] Searching for Chrome history...")
        src = find_chrome_history()
        if not src:
            print("[!] Chrome history not found in any profile!")
            return
        parser = parse_chrome

    else:
        print("[!] Invalid choice")
        return

    tmp_copy = Path.home() / "history_copy.sqlite"
    copy_db(src, tmp_copy)
    print(f"[+] Copied DB to {tmp_copy}")

    rows = parser(tmp_copy, limit=200)
    print("\n=== Last 200 History Entries ===")
    for url, vtime in rows:
        print(f"{vtime}  -->  {url}")

    exp = input("\nDo you want to export to CSV? (y/n): ").lower()
    if exp == "y":
        out_file = Path.home() / "history_export.csv"
        save_csv(rows, out_file)
        print(f"[+] CSV saved at {out_file}")

if __name__ == "__main__":
    main()
