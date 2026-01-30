#
#  GoogleFindMyTools - A set of tools to interact with the Google Find My API
#  Copyright © 2024 Leon Böttger. All rights reserved.
#
import undetected_chromedriver as uc
import os
import re
import shutil
import platform
import subprocess
import time

def _patch_uc_del():
    """Suppress noisy __del__ errors from undetected_chromedriver cleanup."""
    if getattr(uc.Chrome, "_gfmt_patched_del", False):
        return
    original_del = getattr(uc.Chrome, "__del__", None)

    def _safe_del(self):
        try:
            if original_del:
                original_del(self)
        except Exception:
            pass

    uc.Chrome.__del__ = _safe_del
    uc.Chrome._gfmt_patched_del = True

def find_chrome():
    """Find Chrome executable using known paths and system commands."""
    possiblePaths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\ProgramData\chocolatey\bin\chrome.exe",
        r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/local/bin/google-chrome",
        "/opt/google/chrome/chrome",
        "/snap/bin/chromium",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    ]
    # Check predefined paths
    for path in possiblePaths:
        if os.path.exists(path):
            return path
    # Use system command to find Chrome
    try:
        if platform.system() == "Windows":
            chrome_path = shutil.which("chrome")
        else:
            chrome_path = shutil.which("google-chrome") or shutil.which("chromium")
        if chrome_path:
            return chrome_path
    except Exception as e:
        print(f"[ChromeDriver] Error while searching system paths: {e}")
    return None

def get_options():
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return chrome_options

def get_chrome_major_version(chrome_path=None):
    """Return the Chrome major version if detectable, otherwise None."""
    if platform.system() == "Windows":
        # Prefer registry to avoid launching Chrome.
        try:
            import winreg

            reg_paths = [
                (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Google\Chrome\BLBeacon"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Google\Chrome\BLBeacon"),
            ]
            for root, subkey in reg_paths:
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        version, _ = winreg.QueryValueEx(key, "version")
                        print(f"[ChromeDriver] Registry version: {version}")
                        match = re.search(r"(\d+)\.", str(version))
                        if match:
                            return int(match.group(1))
                except FileNotFoundError:
                    continue
        except Exception as e:
            print(f"[ChromeDriver] Registry version lookup failed: {e}")

        # Fallback: use file version via PowerShell if we have a path.
        if chrome_path:
            try:
                ps_cmd = (
                    f"(Get-Item '{chrome_path}').VersionInfo.ProductVersion"
                )
                print("[ChromeDriver] Checking file version via PowerShell...")
                output = subprocess.check_output(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                ).strip()
                print(f"[ChromeDriver] File version: {output}")
                match = re.search(r"(\d+)\.", output)
                if match:
                    return int(match.group(1))
            except Exception as e:
                print(f"[ChromeDriver] File version lookup failed: {e}")
        return None

    # Non-Windows: use --version output from Chrome/Chromium on PATH.
    possible_commands = [
        ["google-chrome", "--version"],
        ["chrome", "--version"],
        ["chromium", "--version"],
    ]
    for cmd in possible_commands:
        try:
            print(f"[ChromeDriver] Checking Chrome version with: {' '.join(cmd)}")
            output = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            ).strip()
            print(f"[ChromeDriver] Version output: {output}")
            match = re.search(r"(\d+)\.", output)
            if match:
                return int(match.group(1))
        except Exception:
            continue
    return None

def create_driver():
    """Create a Chrome WebDriver with undetected_chromedriver."""
    try:
        # Kill any existing Chrome processes first
        try:
            if platform.system() == "Windows":
                os.system("taskkill /f /im chrome.exe >nul 2>&1")
            else:
                os.system("pkill -f chrome")
            time.sleep(2)  # Wait for processes to close
        except:
            pass
            
        _patch_uc_del()
        chrome_options = get_options()
        chrome_path = find_chrome()
        if chrome_path:
            print(f"[ChromeDriver] Detected Chrome at: {chrome_path}")
        else:
            print("[ChromeDriver] Chrome path not found in known locations.")
        print("[ChromeDriver] Detecting Chrome version...")
        chrome_major = get_chrome_major_version(chrome_path)
        print(f"[ChromeDriver] Using Chrome major version: {chrome_major}")
        print("[ChromeDriver] Creating driver (this may take a while)...")
        driver = uc.Chrome(
            options=chrome_options,
            version_main=chrome_major,
        )
        print("[ChromeDriver] Installed and browser started.")
        return driver
    except Exception as e:
        print(f"[ChromeDriver] Default ChromeDriver creation failed: {e}")
        print("[ChromeDriver] Trying alternative paths...")
        chrome_path = find_chrome()
        if chrome_path:
            chrome_options = get_options()
            chrome_options.binary_location = chrome_path
            print(f"[ChromeDriver] Detected Chrome at: {chrome_path}")
            print("[ChromeDriver] Detecting Chrome version...")
            chrome_major = get_chrome_major_version(chrome_path)
            print(f"[ChromeDriver] Using Chrome major version: {chrome_major}")
            print("[ChromeDriver] Creating driver (this may take a while)...")
            try:
                driver = uc.Chrome(
                    options=chrome_options,
                    version_main=chrome_major,
                )
                print(f"[ChromeDriver] ChromeDriver started using {chrome_path}")
                return driver
            except Exception as e:
                print(f"[ChromeDriver] ChromeDriver failed using path {chrome_path}: {e}")
        else:
            print("[ChromeDriver] No Chrome executable found in known paths.")
        
        # Final fallback - try headless mode
        print("[ChromeDriver] Trying headless mode as last resort...")
        try:
            chrome_options = get_options()
            chrome_options.add_argument("--headless")
            print("[ChromeDriver] Detecting Chrome version...")
            chrome_major = get_chrome_major_version()
            print(f"[ChromeDriver] Using Chrome major version: {chrome_major}")
            print("[ChromeDriver] Creating driver in headless mode (this may take a while)...")
            driver = uc.Chrome(
                options=chrome_options,
                version_main=chrome_major,
            )
            print("[ChromeDriver] Started in headless mode successfully.")
            return driver
        except Exception as e:
            print(f"[ChromeDriver] Headless mode also failed: {e}")
        
        raise Exception(
            "[ChromeDriver] Failed to install ChromeDriver. A current version of Chrome was not detected on your system.\n"
            "If you know that Chrome is installed, update Chrome to the latest version. If the script is still not working, "
            "set the path to your Chrome executable manually inside the script."
        )

if __name__ == '__main__':
    create_driver()
