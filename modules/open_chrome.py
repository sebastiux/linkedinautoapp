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


def _detect_installed_chrome_major(error_text: object) -> int | None:
    '''
    Tries to figure out the installed Chrome major version so we can download a
    matching ChromeDriver. First it parses the version mentioned in a Selenium
    error message (e.g. "Current browser version is 148.0.7778.179"); if that
    fails it falls back to querying the system.
    '''
    import re
    match = re.search(r"Current browser version is (\d+)", str(error_text))
    if match:
        return int(match.group(1))
    try:
        from undetected_chromedriver import find_chrome_executable
        from undetected_chromedriver.patcher import Patcher  # noqa: F401
        import subprocess, sys
        chrome_path = find_chrome_executable()
        if not chrome_path:
            return None
        if sys.platform.startswith("win"):
            # Read the product version via PowerShell (no extra dependencies)
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-Item '{chrome_path}').VersionInfo.ProductVersion"],
                text=True, stderr=subprocess.DEVNULL,
            ).strip()
        else:
            out = subprocess.check_output([chrome_path, "--version"], text=True).strip()
        ver = re.search(r"(\d+)\.", out)
        return int(ver.group(1)) if ver else None
    except Exception:
        return None


try:
    options, driver, actions, wait = None, None, None, None
    options, driver, actions, wait = createChromeSession()
except SessionNotCreatedException as e:
    # Most common cause: the auto-downloaded ChromeDriver does not match the
    # installed Chrome. Detect the installed Chrome version and retry with a
    # matching driver before falling back to a guest profile.
    chrome_major = _detect_installed_chrome_major(e)
    try:
        if chrome_major:
            print_lg(f"ChromeDriver/Chrome version mismatch detected. Retrying with a driver for Chrome {chrome_major}...")
            options, driver, actions, wait = createChromeSession(version_main=chrome_major)
        else:
            raise e
    except SessionNotCreatedException as e2:
        critical_error_log("Failed to create Chrome Session, retrying with guest profile", e2)
        options, driver, actions, wait = createChromeSession(True, version_main=chrome_major)
except Exception as e:
    msg = 'Seems like Google Chrome is out dated. Update browser and try again! \n\n\nIf issue persists, try Safe Mode. Set, safe_mode = True in config.py \n\nPlease check GitHub discussions/support for solutions https://github.com/GodsScion/Auto_job_applier_linkedIn \n                                   OR \nReach out in discord ( https://discord.gg/fFp7uUzWCY )'
    if isinstance(e,TimeoutError): msg = "Couldn't download Chrome-driver. Set stealth_mode = False in config!"
    print_lg(msg)
    critical_error_log("In Opening Chrome", e)
    from pyautogui import alert
    alert(msg, "Error in opening chrome")
    try: driver.quit()
    except NameError: exit()
    
