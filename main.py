import requests
import json
import time
import random
import os
import sys
from datetime import datetime, timedelta

class FakeUserAgent:
    @staticmethod
    def get_chrome_120():
        chrome_versions = [
            "120.0.0.0", "120.0.6099.0", "120.0.6099.109", 
            "120.0.6099.199", "120.0.6099.216"
        ]
        
        platforms = [
            "Windows NT 10.0; Win64; x64",
            "Windows NT 10.0; WOW64",
            "Windows NT 10.0",
            "Macintosh; Intel Mac OS X 10_15_7",
            "X11; Linux x86_64"
        ]
        
        chrome_version = random.choice(chrome_versions)
        platform = random.choice(platforms)
        
        return f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"

class ConfigLoader:
    def __init__(self, config_file="akun.txt"):
        self.config_file = config_file
        self.config = {}
        self.load_config()
    
    def load_config(self):
        if not os.path.exists(self.config_file):
            print(f"ERROR: File '{self.config_file}' tidak ditemukan!")
            sys.exit(1)
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.config[key.strip()] = value.strip()
            
            required = ['AUTH_TOKEN']
            missing = [key for key in required if key not in self.config]
            
            if missing:
                print(f"ERROR: Konfigurasi tidak lengkap!")
                sys.exit(1)
                
        except Exception as e:
            print(f"ERROR: Gagal memuat konfigurasi: {str(e)}")
            sys.exit(1)
    
    def get(self, key, default=None):
        return self.config.get(key, default)

class NovaEXBot:
    def __init__(self):
        self.config = ConfigLoader()
        
        self.BASE_URL = "https://m.novaexai.com/prod-api"
        self.CHECKIN_STATUS_URL = f"{self.BASE_URL}/sign-in/hasSignedInToday"
        self.BALANCE_URL = f"{self.BASE_URL}/api/assets/query?aType=NEX"
        self.CHECKIN_URL = f"{self.BASE_URL}/sign-in"
        
        self.session = requests.Session()
        self.setup_session()
        
        self.checkin_count = 0
        self.start_time = datetime.now()
    
    def generate_realistic_headers(self):
        user_agent = FakeUserAgent.get_chrome_120()
        
        headers = {
            'authority': 'm.novaexai.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'content-type': 'application/json',
            'lang': 'en',
            'origin': 'https://m.novaexai.com',
            'priority': 'u=1, i',
            'referer': 'https://m.novaexai.com/',
            'sec-ch-ua': '"Chromium";v="120", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': user_agent,
            'x-app-version': '1.0'
        }
        
        auth_token = self.config.get('AUTH_TOKEN')
        if auth_token:
            headers['authorization'] = f'Bearer {auth_token}'
        
        device_id = self.config.get('DEVICE_ID')
        if device_id:
            headers['deviceid'] = device_id
        
        return headers
    
    def setup_session(self):
        self.session.headers.update(self.generate_realistic_headers())
        
        cookies_config = {
            'sl-session': self.config.get('SL_SESSION'),
            '__cflb': self.config.get('CFLB'),
            'cf_clearance': self.config.get('CF_CLEARANCE')
        }
        
        for key, value in cookies_config.items():
            if value:
                self.session.cookies.set(key, value)
    
    def check_connection(self):
        try:
            response = self.session.get(self.CHECKIN_STATUS_URL, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_checkin_status(self):
        try:
            response = self.session.get(self.CHECKIN_STATUS_URL, timeout=10)
            data = response.json()
            
            if data.get('code') == 200:
                return data.get('data', False)
            else:
                print(f"Gagal cek status: {data.get('msg')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Network error: {str(e)}")
            return None
        except json.JSONDecodeError:
            print("Invalid JSON response")
            return None
    
    def get_balance(self):
        try:
            response = self.session.get(self.BALANCE_URL, timeout=10)
            data = response.json()
            
            if data.get('code') == 200:
                return data.get('data', {})
            else:
                print(f"Gagal cek saldo: {data.get('msg')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Network error: {str(e)}")
            return None
        except json.JSONDecodeError:
            print("Invalid JSON response")
            return None
    
    def generate_checkin_data(self):
        return {
            "ephemeralPublicKey": self.config.get('PUBLIC_KEY', ''),
            "encryptedData": self.config.get('ENCRYPTED_DATA', ''),
            "authTag": self.config.get('AUTH_TAG', ''),
            "iv": self.config.get('IV', '')
        }
    
    def do_checkin(self):
        try:
            checkin_data = self.generate_checkin_data()
            
            if not all(checkin_data.values()):
                print("Data check-in tidak lengkap di config")
                return False
            
            response = self.session.post(self.CHECKIN_URL, 
                                        json=checkin_data, 
                                        timeout=10)
            data = response.json()
            
            if data.get('code') == 200:
                self.checkin_count += 1
                return True
            else:
                print(f"Check-in gagal: {data.get('msg')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Network error: {str(e)}")
            return False
        except json.JSONDecodeError:
            print("Invalid JSON response")
            return False
    
    def display_stats(self):
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        print("\n" + "=" * 50)
        print("STATISTIK BOT:")
        print(f"Uptime: {uptime.days} hari, {hours} jam, {minutes} menit")
        print(f"Check-in berhasil: {self.checkin_count} kali")
        print("=" * 50)
    
    def single_checkin(self):
        print(f"\n{'='*60}")
        print(f"PROSES CHECK-IN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('='*60)
        
        if not self.check_connection():
            print("Tidak bisa terkoneksi ke NovaEX")
            return False
        
        print("\nMengecek saldo...")
        balance_data = self.get_balance()
        
        if balance_data:
            available = float(balance_data.get('availableAssets', 0))
            frozen = float(balance_data.get('frozenAssets', 0))
            total = available + frozen
            
            print(f"Tersedia: {available:,.6f} NEX")
            print(f"Beku: {frozen:,.6f} NEX")
            print(f"Total: {total:,.6f} NEX")
            print(f"Rate: {balance_data.get('exchangeRate', 'N/A')}")
        
        print("\nMengecek status check-in...")
        has_signed = self.get_checkin_status()
        
        if has_signed is False:
            print("Status: BELUM check-in hari ini")
            print("\nMelakukan check-in...")
            
            if self.do_checkin():
                print("CHECK-IN BERHASIL!")
                
                print("\nMengecek saldo baru...")
                time.sleep(3)
                new_balance = self.get_balance()
                
                if balance_data and new_balance:
                    new_available = float(new_balance.get('availableAssets', 0))
                    old_available = float(balance_data.get('availableAssets', 0))
                    difference = new_available - old_available
                    
                    if difference > 0:
                        print(f"Anda mendapatkan: {difference:,.6f} NEX")
                    else:
                        print(f"Saldo baru: {new_available:,.6f} NEX")
                
                return True
            else:
                return False
                
        elif has_signed is True:
            print("Status: SUDAH check-in hari ini")
            print("Tidak perlu check-in lagi")
            return True
        else:
            print("Tidak bisa menentukan status check-in")
            return False
    
    def run_continuous(self, interval_hours=24, interval_minutes=2):
        print("\nNovaEX AI Auto Check-in Bot")
        print(f"Interval: {interval_hours} jam {interval_minutes} menit")
        print(f"Waktu mulai: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        total_seconds = (interval_hours * 3600) + (interval_minutes * 60)
        
        run_count = 0
        error_count = 0
        max_errors = 5
        
        while True:
            run_count += 1
            print(f"\nRUN #{run_count}")
            
            try:
                success = self.single_checkin()
                
                if success:
                    error_count = 0
                    print(f"\nRun #{run_count} berhasil")
                else:
                    error_count += 1
                    print(f"\nRun #{run_count} gagal (Error #{error_count})")
                
                self.display_stats()
                
                if error_count >= max_errors:
                    print(f"\nTerlalu banyak error ({error_count}), bot akan berhenti")
                    break
                
                next_run = datetime.now() + timedelta(seconds=total_seconds)
                print(f"\nCheck-in berikutnya: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Tidur selama {interval_hours} jam {interval_minutes} menit...")
                
                self.sleep_with_progress(total_seconds)
                
                if run_count % 3 == 0:
                    print("\nRotating user agent...")
                    self.session.headers.update(self.generate_realistic_headers())
                
            except KeyboardInterrupt:
                print("\nBot dihentikan oleh user")
                break
            except Exception as e:
                error_count += 1
                print(f"\nError tidak terduga: {str(e)}")
                
                if error_count >= max_errors:
                    print(f"Terlalu banyak error, bot akan berhenti")
                    break
                
                retry_delay = min(300, error_count * 60)
                print(f"Akan mencoba lagi dalam {retry_delay//60} menit...")
                time.sleep(retry_delay)
    
    def sleep_with_progress(self, total_seconds):
        intervals = 20
        sleep_interval = total_seconds / intervals
        
        for i in range(intervals):
            progress = (i + 1) / intervals * 100
            bar_length = 30
            filled_length = int(bar_length * (i + 1) // intervals)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            remaining = total_seconds - (i * sleep_interval)
            hours_remaining = int(remaining // 3600)
            minutes_remaining = int((remaining % 3600) // 60)
            seconds_remaining = int(remaining % 60)
            
            sys.stdout.write(f'\r[{bar}] {progress:.0f}% | Tersisa: {hours_remaining:02d}:{minutes_remaining:02d}:{seconds_remaining:02d}')
            sys.stdout.flush()
            time.sleep(sleep_interval)
        
        print()

def main():
    bot = NovaEXBot()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--once":
            print("\nMode single run")
            bot.single_checkin()
        elif sys.argv[1] == "--test":
            print("\nMode test koneksi")
            if bot.check_connection():
                print("Koneksi OK")
            else:
                print("Koneksi gagal")
        else:
            print(f"\nUsage: python {sys.argv[0]} [options]")
            print("Options:")
            print("  --once     Run once and exit")
            print("  --test     Test connection only")
            print("  (no args)  Run continuously")
    else:
        bot.run_continuous(interval_hours=24, interval_minutes=2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot dihentikan")
    except Exception as e:
        print(f"\nError fatal: {str(e)}")
