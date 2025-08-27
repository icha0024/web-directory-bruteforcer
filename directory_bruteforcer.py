#!/usr/bin/env python3

import requests
import sys
import os
from urllib.parse import urljoin, urlparse
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

class DirectoryBruteForcer:
    def __init__(self, target_url, threads=20):
        self.target_url = target_url.rstrip('/')
        self.session = requests.Session()
        self.found_directories = []
        self.threads = threads
        self.lock = Lock()
        self.total_tested = 0
        
    def validate_url(self, url):
        """Validate if URL is properly formatted"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def load_wordlist(self, wordlist_path):
        """Load wordlist from file"""
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                wordlist = [line.strip() for line in f if line.strip()]
            print(f"[INFO] Loaded {len(wordlist)} words from {wordlist_path}")
            return wordlist
        except FileNotFoundError:
            print(f"[ERROR] Wordlist file not found: {wordlist_path}")
            return []
        except Exception as e:
            print(f"[ERROR] Error loading wordlist: {e}")
            return []
    
    def test_directory(self, directory):
        """Test a single directory/file"""
        test_url = urljoin(self.target_url + '/', directory)
        
        try:
            response = self.session.get(
                test_url, 
                timeout=10,
                allow_redirects=False,
                verify=False  # Ignore SSL certificate errors
            )
            
            status_code = response.status_code
            content_length = len(response.content)
            
            # Thread-safe result collection
            with self.lock:
                self.total_tested += 1
                
                # Print results for interesting status codes
                if status_code in [200, 301, 302, 403, 401]:
                    status_msg = f"[{status_code}] {test_url} (Size: {content_length})"
                    print(status_msg)
                    
                    self.found_directories.append({
                        'url': test_url,
                        'status_code': status_code,
                        'size': content_length
                    })
                
        except requests.exceptions.RequestException as e:
            # Silently ignore connection errors, timeouts, etc.
            with self.lock:
                self.total_tested += 1
    
    def progress_monitor(self, total_words, start_time):
        """Monitor and display progress in separate thread"""
        while self.total_tested < total_words:
            time.sleep(2)  # Update every 2 seconds
            with self.lock:
                current = self.total_tested
            
            if current > 0:
                elapsed = time.time() - start_time
                rate = current / elapsed if elapsed > 0 else 0
                percent = (current / total_words) * 100
                print(f"[PROGRESS] {current}/{total_words} ({percent:.1f}%) - {rate:.1f} req/sec")
    
    def scan(self, wordlist_path):
        """Main scanning function with multi-threading"""
        if not self.validate_url(self.target_url):
            print(f"[ERROR] Invalid URL: {self.target_url}")
            return
        
        print(f"[INFO] Starting directory brute force on: {self.target_url}")
        print(f"[INFO] Using {self.threads} threads")
        print(f"[INFO] Ignoring SSL certificate errors")
        
        # Load wordlist
        wordlist = self.load_wordlist(wordlist_path)
        if not wordlist:
            return
        
        print(f"[INFO] Starting scan with {len(wordlist)} words...")
        print("-" * 60)
        
        start_time = time.time()
        
        # Start progress monitor thread
        progress_thread = threading.Thread(
            target=self.progress_monitor, 
            args=(len(wordlist), start_time),
            daemon=True
        )
        progress_thread.start()
        
        # Multi-threaded scanning
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            executor.map(self.test_directory, wordlist)
        
        # Final results
        elapsed = time.time() - start_time
        total_rate = len(wordlist) / elapsed if elapsed > 0 else 0
        
        print("-" * 60)
        print(f"[INFO] Scan completed in {elapsed:.1f} seconds")
        print(f"[INFO] Average rate: {total_rate:.1f} requests/second")
        print(f"[INFO] Found {len(self.found_directories)} interesting directories")

def main():
    if len(sys.argv) < 3:
        print("Usage: python directory_bruteforcer.py <target_url> <wordlist_file> [threads]")
        print("Example: python directory_bruteforcer.py https://example.com wordlists/common.txt 20")
        sys.exit(1)
    
    target_url = sys.argv[1]
    wordlist_file = sys.argv[2]
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    
    # Check if wordlist exists
    if not os.path.exists(wordlist_file):
        print(f"[ERROR] Wordlist file not found: {wordlist_file}")
        sys.exit(1)
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Create and run scanner
    scanner = DirectoryBruteForcer(target_url, threads)
    scanner.scan(wordlist_file)

if __name__ == "__main__":
    main()