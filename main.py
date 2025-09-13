import requests
import time
import json
import pandas as pd
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import random

class RelayFeeCalculator:
    def __init__(self):
        self.base_url = "https://api.relay.link/requests/v2"
        self.target_recipient = "0xc2d921da88d3d5e718cf97aa9afb5b35d821918c"
        self.proxies = []
        self.lock = threading.Lock()
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Origin': 'https://relay.link',
            'Referer': 'https://relay.link/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        
    def load_proxies(self, filename: str = "proxy.txt") -> List[Dict]:
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                proxy_lines = [line.strip() for line in file if line.strip()]
            
            proxies = []
            for line in proxy_lines:
                if '@' in line:
                    auth_part, ip_port = line.split('@')
                    login, password = auth_part.split(':')
                    ip, port = ip_port.split(':')
                    
                    proxy = {
                        'http': f'http://{login}:{password}@{ip}:{port}',
                        'https': f'http://{login}:{password}@{ip}:{port}'
                    }
                    proxies.append(proxy)
            
            return proxies
        except FileNotFoundError:
            return []
        except Exception as e:
            return []
        
    def read_wallets(self, filename: str = "wallets.txt") -> List[str]:
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                wallets = [line.strip() for line in file if line.strip()]
            return wallets
        except FileNotFoundError:
            return []
        except Exception as e:
            return []
    
    def get_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(self.headers)
        
        if self.proxies:
            proxy = random.choice(self.proxies)
            session.proxies = proxy
        
        return session
    
    def fetch_requests_page(self, wallet_address: str, continuation: Optional[str] = None, max_retries: int = 3) -> Dict:
        params = {
            "user": wallet_address,
            "privateChainsToInclude": ""
        }
        
        if continuation:
            params["continuation"] = continuation
        
        for attempt in range(max_retries + 1):
            session = self.get_session()
            
            try:
                response = session.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                    continue
                return {}
            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                    continue
                return {}
            finally:
                session.close()
        
        return {}
    
    def extract_fees_from_requests(self, requests_data: List[Dict]) -> List[Dict]:
        fees = []
        
        for request in requests_data:
            request_id = request.get("id", "")
            user = request.get("user", "")
            created_at = request.get("createdAt", "")
            
            if "appFees" in request:
                app_fees = request["appFees"]
                
                for app_fee in app_fees:
                    recipient = app_fee.get("recipient", "").lower()
                    target_recipient = self.target_recipient.lower()
                    
                    if recipient == target_recipient:
                        fee_info = {
                            "request_id": request_id,
                            "user": user,
                            "amount_usd": float(app_fee.get("amountUsd", 0)),
                            "amount": app_fee.get("amount", ""),
                            "bps": app_fee.get("bps", ""),
                            "created_at": created_at
                        }
                        fees.append(fee_info)
            
            if "data" in request and "appFees" in request["data"]:
                app_fees = request["data"]["appFees"]
                
                for app_fee in app_fees:
                    recipient = app_fee.get("recipient", "").lower()
                    target_recipient = self.target_recipient.lower()
                    
                    if recipient == target_recipient:
                        fee_info = {
                            "request_id": request_id,
                            "user": user,
                            "amount_usd": float(app_fee.get("amountUsd", 0)),
                            "amount": app_fee.get("amount", ""),
                            "bps": app_fee.get("bps", ""),
                            "created_at": created_at
                        }
                        fees.append(fee_info)
        
        return fees
    
    def process_wallet(self, wallet_address: str) -> Dict:
        all_fees = []
        continuation = None
        page_count = 0
        seen_request_ids = set()
        
        while True:
            page_count += 1
            
            data = self.fetch_requests_page(wallet_address, continuation)
            
            if not data or "requests" not in data:
                break
            
            requests_data = data["requests"]
            
            new_requests = []
            duplicate_count = 0
            
            for request in requests_data:
                request_id = request.get("id", "")
                if request_id and request_id not in seen_request_ids:
                    seen_request_ids.add(request_id)
                    new_requests.append(request)
                elif request_id:
                    duplicate_count += 1
            
            if not new_requests:
                new_continuation = data.get("continuation")
                if new_continuation and new_continuation != continuation:
                    continuation = new_continuation
                    continue
                else:
                    break
            
            page_fees = self.extract_fees_from_requests(new_requests)
            all_fees.extend(page_fees)
            
            new_continuation = data.get("continuation")
            if not new_continuation:
                break
                
            if new_continuation == continuation:
                break
                
            continuation = new_continuation
            
            if page_count >= 200:
                break
            
            time.sleep(random.uniform(0.3, 0.7))
        
        wallet_total = sum(fee["amount_usd"] for fee in all_fees)
        
        with self.lock:
            print(f"{wallet_address}: ${wallet_total:.2f}")
        
        return {
            "wallet": wallet_address,
            "fees": all_fees,
            "tx_count": len(all_fees),
            "total_amount": wallet_total
        }
    
    def save_to_excel(self, results: List[Dict], wallets_order: List[str]):
        excel_data = []
        
        results_dict = {result["wallet"].lower(): result for result in results}
        
        for wallet in wallets_order:
            wallet_lower = wallet.lower()
            if wallet_lower in results_dict:
                result = results_dict[wallet_lower]
                excel_data.append({
                    "Адрес кошелька": wallet,
                    "Tx count": result["tx_count"],
                    "Общая сумма комиссий": f"${result['total_amount']:.2f}"
                })
            else:
                excel_data.append({
                    "Адрес кошелька": wallet,
                    "Tx count": 0,
                    "Общая сумма комиссий": "$0.00"
                })
        
        df = pd.DataFrame(excel_data)
        
        excel_filename = "relay_fees_results.xlsx"
        df.to_excel(excel_filename, index=False, engine='openpyxl')
        
        return excel_filename
    
    def save_results(self, all_fees: List[Dict], total_amount: float):
        with open("fees_detailed.json", "w", encoding="utf-8") as f:
            json.dump(all_fees, f, indent=2, ensure_ascii=False)
        
        summary = {
            "total_fees_count": len(all_fees),
            "total_amount_usd": total_amount,
            "target_recipient": self.target_recipient,
            "wallets_processed": len(set(fee["user"] for fee in all_fees)),
            "fees_by_wallet": {}
        }
        
        for fee in all_fees:
            wallet = fee["user"]
            if wallet not in summary["fees_by_wallet"]:
                summary["fees_by_wallet"][wallet] = {
                    "count": 0,
                    "total_usd": 0
                }
            summary["fees_by_wallet"][wallet]["count"] += 1
            summary["fees_by_wallet"][wallet]["total_usd"] += fee["amount_usd"]
        
        with open("fees_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def run(self, max_workers: int = 5):
        self.proxies = self.load_proxies()
        
        wallets = self.read_wallets()
        if not wallets:
            return
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_wallet = {
                executor.submit(self.process_wallet, wallet): wallet 
                for wallet in wallets
            }
            
            for future in as_completed(future_to_wallet):
                wallet = future_to_wallet[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "wallet": wallet,
                        "fees": [],
                        "tx_count": 0,
                        "total_amount": 0
                    })
        
        all_fees = []
        for result in results:
            all_fees.extend(result["fees"])
        
        total_amount = sum(fee["amount_usd"] for fee in all_fees)
        processed_count = len([r for r in results if r["tx_count"] > 0])
        
        print(f"\nИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
        print(f"{'='*50}")
        print(f"Обработано кошельков: {len(results)}/{len(wallets)}")
        print(f"Кошельков с комиссиями: {processed_count}")
        print(f"Найдено комиссий: {len(all_fees)}")
        print(f"Общая сумма комиссий: ${total_amount:.2f}")
        
        if all_fees:
            self.save_results(all_fees, total_amount)
            
        self.save_to_excel(results, wallets)

def main():
    calculator = RelayFeeCalculator()
    calculator.run(max_workers=5)

if __name__ == "__main__":
    main()