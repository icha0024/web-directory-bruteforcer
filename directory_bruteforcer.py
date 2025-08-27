import requests
import sys
import os
from urllib.parse import urljoin, urlparse
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import argparse
import random
import json
from datetime import datetime

class DirectoryBruteForcer:
    def __init__(self, target_url, threads=20, timeout=10, status_codes=None, user_agents=None, 
                 output_file=None, min_size=0, max_size=None):
        self.target_url = self.normalize_url(target_url)
        self.session = requests.Session()
        self.found_directories = []
        self.threads = threads
        self.timeout = timeout
        self.status_codes = status_codes or [200, 301, 302, 403, 401]
        self.user_agents = user_agents or []
        self.output_file = output_file
        self.min_size = min_size
        self.max_size = max_size
        self.lock = Lock()
        self.total_tested = 0
        
    def normalize_url(self, url):
        """Normalize URL and ensure proper protocol"""
        url = url.rstrip('/')
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            # Try HTTPS first, fallback to HTTP if needed
            url = 'https://' + url
        
        return url
    
    def detect_protocol(self, base_url):
        """Auto-detect if HTTPS is supported, fallback to HTTP"""
        if base_url.startswith('https://'):
            try:
                # Test HTTPS connectivity
                test_response = requests.get(base_url, timeout=5, verify=False)
                return base_url  # HTTPS works
            except:
                # HTTPS failed, try HTTP
                http_url = base_url.replace('https://', 'http://')
                try:
                    test_response = requests.get(http_url, timeout=5, verify=False)
                    print(f"[INFO] HTTPS failed, using HTTP: {http_url}")
                    return http_url
                except:
                    print(f"[WARNING] Both HTTPS and HTTP failed for {base_url}")
                    return base_url  # Return original, let it fail later
        
        return base_url
    
    def validate_url(self, url):
        """Validate if URL is properly formatted"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def load_user_agents(self, user_agents_path="config/user-agents.txt"):
        """Load user agents from file"""
        try:
            with open(user_agents_path, 'r', encoding='utf-8') as f:
                agents = [line.strip() for line in f if line.strip()]
            return agents
        except FileNotFoundError:
            # Return default user agent if file not found
            return ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"]
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
    
    def filter_response(self, status_code, content_length):
        """Filter responses based on status code and size"""
        # Check status code
        if status_code not in self.status_codes:
            return False
        
        # Check size filters
        if content_length < self.min_size:
            return False
        
        if self.max_size is not None and content_length > self.max_size:
            return False
        
        return True
    
    def format_result(self, url, status_code, content_length):
        """Format result for display"""
        size_str = f"{content_length:,}" if content_length >= 1000 else str(content_length)
        return f"[{status_code}] {url} (Size: {size_str} bytes)"
    
    def save_results(self):
        """Save results to output file"""
        if not self.output_file or not self.found_directories:
            return
        
        # Ensure results directory exists
        os.makedirs('results', exist_ok=True)
        
        # Generate filename with timestamp if not specified
        if self.output_file == 'auto':
            domain = urlparse(self.target_url).netloc
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"results/{domain}_{timestamp}.json"
        else:
            filename = self.output_file
        
        # Prepare data for saving
        scan_data = {
            'target': self.target_url,
            'timestamp': datetime.now().isoformat(),
            'scan_info': {
                'threads': self.threads,
                'timeout': self.timeout,
                'status_codes': self.status_codes,
                'total_tested': self.total_tested,
                'total_found': len(self.found_directories)
            },
            'results': self.found_directories
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(scan_data, f, indent=2)
            print(f"[INFO] Results saved to: {filename}")
        except Exception as e:
            print(f"[ERROR] Failed to save results: {e}")
    def test_directory(self, directory):
        """Test a single directory/file"""
        test_url = urljoin(self.target_url + '/', directory)
        
        # Get random user agent if available
        headers = {}
        if self.user_agents:
            headers['User-Agent'] = random.choice(self.user_agents)
        
        try:
            response = self.session.get(
                test_url, 
                timeout=self.timeout,
                headers=headers,
                allow_redirects=False,
                verify=False  # Ignore SSL certificate errors
            )
            
            status_code = response.status_code
            content_length = len(response.content)
            
            # Thread-safe result collection
            with self.lock:
                self.total_tested += 1
                
                # Apply filters and print results
                if self.filter_response(status_code, content_length):
                    result_msg = self.format_result(test_url, status_code, content_length)
                    print(result_msg)
                    
                    self.found_directories.append({
                        'url': test_url,
                        'status_code': status_code,
                        'size': content_length,
                        'directory': directory,
                        'timestamp': datetime.now().isoformat()
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
    
    def scan(self, wordlist_path, quiet=False):
        """Main scanning function with multi-threading"""
        if not self.validate_url(self.target_url):
            print(f"[ERROR] Invalid URL: {self.target_url}")
            return
        
        # Auto-detect protocol if needed
        self.target_url = self.detect_protocol(self.target_url)
        
        # Load user agents
        if not self.user_agents:
            self.user_agents = self.load_user_agents()
        
        if not quiet:
            print(f"[INFO] Starting directory brute force on: {self.target_url}")
            print(f"[INFO] Protocol: {'HTTPS' if self.target_url.startswith('https') else 'HTTP'}")
            print(f"[INFO] Using {self.threads} threads")
            print(f"[INFO] Timeout: {self.timeout} seconds")
            print(f"[INFO] User agents: {len(self.user_agents)} loaded")
            print(f"[INFO] Status codes: {', '.join(map(str, self.status_codes))}")
            print(f"[INFO] Ignoring SSL certificate errors")
        
        # Load wordlist
        wordlist = self.load_wordlist(wordlist_path)
        if not wordlist:
            return
        
        if not quiet:
            print(f"[INFO] Starting scan with {len(wordlist)} words...")
            print("-" * 60)
        
        start_time = time.time()
        
        # Start progress monitor thread (only if not quiet)
        if not quiet:
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
        
        # Save results to file if requested
        self.save_results()
        
        if not quiet:
            print("-" * 60)
            print(f"[INFO] Scan completed in {elapsed:.1f} seconds")
            print(f"[INFO] Average rate: {total_rate:.1f} requests/second")
            print(f"[INFO] Found {len(self.found_directories)} interesting directories")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Multi-threaded web directory and file brute forcer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python directory_bruteforcer.py https://example.com wordlists/common.txt
  python directory_bruteforcer.py -u https://example.com -w wordlists/common.txt -t 50
  python directory_bruteforcer.py -u https://example.com -w wordlists/common.txt -s 200,403 -q
        """
    )
    
    parser.add_argument('url', nargs='?', help='Target URL (e.g., https://example.com)')
    parser.add_argument('wordlist', nargs='?', help='Path to wordlist file')
    parser.add_argument('-u', '--url', dest='url_flag', help='Target URL')
    parser.add_argument('-w', '--wordlist', dest='wordlist_flag', help='Path to wordlist file')
    parser.add_argument('-t', '--threads', type=int, default=20, 
                       help='Number of threads (default: 20)')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Request timeout in seconds (default: 10)')
    parser.add_argument('-s', '--status-codes', default='200,301,302,403,401',
                       help='Status codes to show (default: 200,301,302,403,401)')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Quiet mode - only show results')
    parser.add_argument('-o', '--output', help='Output file to save results (use "auto" for automatic naming)')
    parser.add_argument('--min-size', type=int, default=0,
                       help='Minimum response size in bytes (default: 0)')
    parser.add_argument('--max-size', type=int,
                       help='Maximum response size in bytes (default: no limit)')
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Determine URL and wordlist (support both positional and flag arguments)
    target_url = args.url or args.url_flag
    wordlist_file = args.wordlist or args.wordlist_flag
    
    if not target_url or not wordlist_file:
        print("Error: Both URL and wordlist are required")
        print("Usage: python directory_bruteforcer.py <url> <wordlist> [options]")
        print("   or: python directory_bruteforcer.py -u <url> -w <wordlist> [options]")
        sys.exit(1)
    
    # Check if wordlist exists
    if not os.path.exists(wordlist_file):
        print(f"[ERROR] Wordlist file not found: {wordlist_file}")
        sys.exit(1)
    
    # Parse status codes
    try:
        status_codes = [int(code.strip()) for code in args.status_codes.split(',')]
    except ValueError:
        print(f"[ERROR] Invalid status codes format: {args.status_codes}")
        sys.exit(1)
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Create and run scanner
    scanner = DirectoryBruteForcer(
        target_url, 
        threads=args.threads,
        timeout=args.timeout,
        status_codes=status_codes,
        output_file=args.output,
        min_size=args.min_size,
        max_size=args.max_size
    )
    scanner.scan(wordlist_file, quiet=args.quiet)

if __name__ == "__main__":
    main()