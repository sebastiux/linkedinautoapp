'''
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

Support me: https://github.com/sponsors/GodsScion

version:    26.01.20.5.08
'''

from modules.helpers import get_default_temp_profile, make_directories
from config.settings import run_in_background, stealth_mode, disable_extensions, safe_mode, file_name, failed_file_name, logs_folder_path, generated_resume_path
from config.questions import default_resume_path
if stealth_mode:
    import undetected_chromedriver as uc
else: 
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    # from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from modules.helpers import find_default_profile_directory, critical_error_log, print_lg
from selenium.common.exceptions import SessionNotCreatedException

def createChromeSession(isRetry: bool = False, version_main: int = None):
    make_directories([file_name,failed_file_name,logs_folder_path+"/screenshots",default_resume_path,generated_resume_path+"/temp"])
    # Set up WebDriver with Chrome Profile
    options = uc.ChromeOptions() if stealth_mode else Options()
    if run_in_background:   options.add_argument("--headless")
    if disable_extensions:  options.add_argument("--disable-extensions")
    # Skip Chrome's first-run screens and the "Who uses Chrome?" profile picker
    # so the bot can drive the browser without a human clicking through them.
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--profile-directory=Default")

    print_lg("IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM! Or it's highly likely that application will just open browser and not do anything!")
    profile_dir = find_default_profile_directory()
    if isRetry:
        print_lg("Will login with a guest profile, browsing history will not be saved in the browser!")
    elif profile_dir and not safe_mode:
        options.add_argument(f"--user-data-dir={profile_dir}")
    else:
        print_lg("Logging in with a guest profile, Web history will not be saved!")
        options.add_argument(f"--user-data-dir={get_default_temp_profile()}")
    if stealth_mode:
        # try:
        #     driver = uc.Chrome(driver_executable_path="C:\\Program Files\\Google\\Chrome\\chromedriver-win64\\chromedriver.exe", options=options)
        # except (FileNotFoundError, PermissionError) as e:
        #     print_lg("(Undetected Mode) Got '{}' when using pre-installed ChromeDriver.".format(type(e).__name__))
            print_lg("Downloading Chrome Driver... This may take some time. Undetected mode requires download every run!")
            if version_main:
                print_lg(f"Matching ChromeDriver to your installed Chrome version: {version_main}")
            driver = uc.Chrome(options=options, version_main=version_main)
    else: driver = webdriver.Chrome(options=options) #, service=Service(executable_path="C:\\Program Files\\Google\\Chrome\\chromedriver-win64\\chromedriver.exe"))
    driver.maximize_window()
    wait = WebDriverWait(driver, 5)
    actions = ActionChains(driver)
    return options, driver, actions, wait


def _chrome_major_from_error(error_text: object) -> int | None:
    '''
    Parses the installed Chrome major version from a Selenium error message
    (e.g. "Current browser version is 148.0.7778.179"). Returns None if absent.
    '''
    import re
    match = re.search(r"Current browser version is (\d+)", str(error_text))
    return int(match.group(1)) if match else None


def _detect_installed_chrome_major() -> int | None:
    '''
    Detects the installed Chrome major version directly from the system, so we
    can download a matching ChromeDriver. Tries the Windows registry first (the
    most reliable source), then reads the Chrome executable's file version.
    Returns None if it cannot be determined.
    '''
    import re, sys, subprocess

    # 1. Windows registry (BLBeacon holds the exact installed version)
    if sys.platform.startswith("win"):
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive, r"Software\Google\Chrome\BLBeacon") as key:
                        version, _ = winreg.QueryValueEx(key, "version")
                        if version:
                            return int(str(version).split(".")[0])
                except FileNotFoundError:
                    continue
        except Exception:
            pass

    # 2. Read the version straight off the Chrome executable
    try:
        from undetected_chromedriver import find_chrome_executable
        chrome_path = find_chrome_executable()
        if chrome_path:
            if sys.platform.startswith("win"):
                out = subprocess.check_output(
                    ["powershell", "-NoProfile", "-Command",
                     f"(Get-Item '{chrome_path}').VersionInfo.ProductVersion"],
                    text=True, stderr=subprocess.DEVNULL,
                ).strip()
            else:
                out = subprocess.check_output([chrome_path, "--version"], text=True).strip()
            ver = re.search(r"(\d+)\.", out)
            if ver:
                return int(ver.group(1))
    except Exception:
        pass

    return None


def _open_with_matching_driver():
    '''
    Opens Chrome, automatically matching the ChromeDriver to the installed
    Chrome version. undetected_chromedriver's own auto-detection is unreliable
    on some setups (it may grab a newer driver than the installed Chrome), so we
    detect the version ourselves and pass it explicitly, retrying as needed.
    '''
    # Detect the installed Chrome version up-front and pass it explicitly.
    chrome_major = _detect_installed_chrome_major()
    try:
        if chrome_major:
            print_lg(f"Detected installed Chrome version: {chrome_major}. Downloading a matching ChromeDriver...")
        return createChromeSession(version_main=chrome_major)
    except SessionNotCreatedException as e:
        # If it still mismatched, the error now tells us the real Chrome version.
        detected = _chrome_major_from_error(e) or chrome_major
        critical_error_log("Chrome session failed, retrying with a matching driver and a guest profile", e)
        return createChromeSession(True, version_main=detected)


try:
    options, driver, actions, wait = None, None, None, None
    options, driver, actions, wait = _open_with_matching_driver()
except Exception as e:
    msg = 'Could not open Chrome with the undetected (stealth) driver.\n\nMOST RELIABLE FIX: open the GUI, go to "Bot Settings" and UNCHECK "Stealth mode" (stealth_mode = False). Without stealth mode, Selenium auto-downloads the correct ChromeDriver for your Chrome version.\n\nAlternatively, update Google Chrome to the latest version and try again.\n\nFor help: https://github.com/GodsScion/Auto_job_applier_linkedIn  OR  https://discord.gg/fFp7uUzWCY'
    if isinstance(e,TimeoutError): msg = "Couldn't download Chrome-driver. Set stealth_mode = False in config!"
    print_lg(msg)
    critical_error_log("In Opening Chrome", e)
    from pyautogui import alert
    alert(msg, "Error in opening chrome")
    try: driver.quit()
    except NameError: exit()
    
