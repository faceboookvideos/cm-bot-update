import time
import pandas as pd
import os
import threading
import random
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime
from colorama import init, Fore

# Initialize
init(autoreset=True)

# Google Sheet Web App Verification
def verify_license_from_sheet(input_key):
    try:
        web_app_url = "https://script.google.com/macros/s/AKfycbxL_bO-akYPcQ5zkuZzSauHtBy6BkIY6nWcli3sFfD9ejDANuWowlz9fXUpPqfA9rV1/exec"
        response = requests.get(f"{web_app_url}?key={input_key}")
        data = response.json()
        if data.get('status') == 'active':
            return True
        return False
    except Exception as e:
        print(f"{Fore.RED}Connection Error: {e}")
        return False

def get_max_threads():
    try:
        if os.path.exists('thread_count.txt'):
            with open('thread_count.txt', 'r') as f: return int(f.read().strip())
    except: return 2

MAX_THREADS = get_max_threads()
thread_limiter = threading.Semaphore(MAX_THREADS)
success_logs = []
log_lock = threading.Lock()

def log_login_result(email, password, status):
    filename = "login_success.txt" if status == "success" else "login_fail.txt"
    with log_lock:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(f"{email}:{password}\n")

def save_success_to_excel():
    report_path = os.path.join(os.path.dirname(__file__), 'success_report.xlsx')
    with log_lock:
        if success_logs:
            pd.DataFrame(success_logs).to_excel(report_path, index=False)

def auto_post_to_communities(page, email, image_path, post_link):
    try:
        page.goto('https://www.tumblr.com/communities', wait_until='networkidle', timeout=60000)
        time.sleep(6)
        community_links = page.eval_on_selector_all('a[href*="/communities/"]', "elements => elements.map(el => el.href)")
        unique_communities = [l for l in list(set(community_links)) if "/communities/" in l and not any(x in l for x in ["/explore", "/posts", "/all", "/search"])]
        for url in unique_communities:
            try:
                page.goto(url, wait_until='networkidle', timeout=60000); time.sleep(6)
                view_btn = page.locator('button:has-text("View community")').first
                if view_btn.is_visible(timeout=5000): view_btn.click(); time.sleep(4)
                photo_btn = page.locator('button[aria-label="Photo"]').last
                if photo_btn.is_visible(): photo_btn.click(); time.sleep(5)
                if image_path and os.path.exists(image_path):
                    page.set_input_files('input[type="file"]', image_path); time.sleep(15) 
                    post_now_btn = page.locator('button:has-text("Post now")').last
                    if post_now_btn.is_enabled(): post_now_btn.click(); time.sleep(5)
                page.click('button[aria-label="Link"]'); time.sleep(5)
                link_box = page.locator('[role="textbox"]').first
                if link_box: link_box.click(); page.keyboard.type(post_link); page.keyboard.press("Enter"); time.sleep(8) 
                final_post_btn = page.locator('button:has-text("Post now")').last
                if final_post_btn.is_enabled(): final_post_btn.click(); time.sleep(6)
                with log_lock: success_logs.append({'Email': email, 'Community': url, 'Status': 'Success', 'Time': datetime.now().strftime("%H:%M")})
                save_success_to_excel(); time.sleep(random.randint(12, 18))
            except: continue
    except: pass

def run_bot(email, password, tag, image_path, post_link, mode, is_headless):
    with thread_limiter:
        with sync_playwright() as p:
            android_device = p.devices['Pixel 7']
            browser = p.chromium.launch(headless=is_headless, args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-setuid-sandbox'])
            context = browser.new_context(**android_device)
            page = context.new_page()
            try:
                page.goto('https://www.tumblr.com/login')
                page.fill('input[name="email"]', email); page.keyboard.press("Enter"); time.sleep(5)
                page.fill('input[name="password"]', password); page.keyboard.press("Enter")
                try:
                    page.wait_for_url("**/dashboard**", timeout=50000)
                    print(f"{Fore.GREEN}[{email}] LOGIN SUCCESSFUL!")
                    log_login_result(email, password, "success")
                    if mode == "3": return
                except:
                    print(f"{Fore.RED}[{email}] LOGIN FAILED!")
                    log_login_result(email, password, "fail")
                    return
                
                # MODE 1: Scan and Join (Updated Logic for Join & Request)
                if mode == "1":
                    page.goto(f"https://www.tumblr.com/tagged/{tag}?sort=community", wait_until='load', timeout=60000)
                    time.sleep(12)
                    raw_links = page.evaluate('''() => { return Array.from(document.querySelectorAll('a[href*="/communities/"]')).map(a => a.href); }''')
                    for target_url in list(set(raw_links)):
                        try:
                            page.goto(f"{target_url}/join", wait_until='domcontentloaded', timeout=50000); time.sleep(6)
                            
                            # এখানে সব ধরণের বাটন হ্যান্ডেল করা হবে
                            join_btn = page.locator('button:has-text("Agree and join"), button:has-text("Join"), button:has-text("Request to join"), button:has-text("Agree and request")').last
                            
                            if join_btn.is_visible(timeout=10000):
                                join_btn.click()
                                time.sleep(8) # রিকোয়েস্ট পাঠানোর জন্য একটু বেশি সময় অপেক্ষা
                                print(f"{Fore.GREEN}[{email}] SUCCESS: Processed {target_url}")
                        except: continue
                # MODE 2: Create Posts
                elif mode == "2":
                    auto_post_to_communities(page, email, image_path, post_link)
            except: pass
            finally: browser.close()

def display_banner(num_threads, acc_count):
    os.system('cls' if os.name == 'nt' else 'clear')
    c = Fore.CYAN; y = Fore.YELLOW; g = Fore.GREEN
    print(f"{c}╔══════════════════════════════════════════════════════════════════════════╗")
    print(f"{c}║   {c}████████╗██╗   ██╗███╗   ███╗██████╗ ██╗     ██████╗ {c}                  ║")
    print(f"{c}║   {c}╚══██╔══╝██║   ██║████╗ ████║██╔══██╗██║     ██╔══██╗{c}                  ║")
    print(f"{c}║   {c}   ██║   ██║   ██║██╔████╔██║██████╔╝██║     ██████╔╝{c}                  ║")
    print(f"{c}║   {c}   ██║   ██║   ██║██║╚██╔╝██║██╔══██╗██║     ██╔══██╗{c}                  ║")
    print(f"{c}║   {c}   ██║   ╚██████╔╝██║ ╚═╝ ██║██████╔╝███████╗██║  ██║{c}                  ║")
    print(f"{c}║   {c}   ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝{c}                  ║")
    print(f"{c}╠══════════════════════════════════════════════════════════════════════════╣")
    print(f"{c}║  {y}> Version: 14.0 (Auto Agree & Request) {c} ║ {g}> Threads: {str(num_threads):<3} {c}║ {g}> Accounts: {str(acc_count):<3} {c}           ║")
    print(f"{c}╚══════════════════════════════════════════════════════════════════════════╝")

def main():
    while True:
        key_input = input(f"\n{Fore.YELLOW}Enter License Key: ").strip()
        if verify_license_from_sheet(key_input):
            print(f"{Fore.GREEN}Access Granted!")
            time.sleep(1)
            break
        else:
            print(f"{Fore.RED}Invalid Key or Inactive Status!")

    while True:
        acc_count = len([l for l in open('account.txt', 'r', encoding='utf-8') if ':' in l]) if os.path.exists('account.txt') else 0
        display_banner(MAX_THREADS, acc_count)
        print(f"\n  {Fore.WHITE}[1] Scan and Join | [2] Create Posts | [3] Login Check | [X] Exit")
        mode = input(f"\n  {Fore.YELLOW}Select Mode: ").strip()
        if mode.lower() == 'x': break
        
        br_choice = input(f"  {Fore.YELLOW}Browser Mode: [1] Open | [2] Hidden: ").strip()
        is_headless = True if br_choice == "2" else False
        
        if os.path.exists('account.txt'):
            accounts = [line.strip().split(':') for line in open('account.txt', 'r', encoding='utf-8') if ':' in line]
            img = ""; lnk = ""
            if os.path.exists('posts.xlsx'):
                df = pd.read_excel('posts.xlsx'); img = df.iloc[0]['image'] if 'image' in df.columns else ""; lnk = str(df.iloc[0]['link'])
            threads = []
            for acc in accounts:
                t = threading.Thread(target=run_bot, args=(acc[0], acc[1], acc[2] if len(acc)>2 else "gay", img, lnk, mode, is_headless))
                t.start(); time.sleep(5); threads.append(t)
            for t in threads: t.join()
        if input(f"\n{Fore.CYAN}  Press 0 for Menu: ") != '0': break

if __name__ == "__main__":
    main()