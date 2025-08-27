Web Directory Brute Forcer
A multi-threaded Python tool for discovering web directories and files using HTTP brute force techniques for authorized security testing.
⚠️ Legal Disclaimer
IMPORTANT: This tool is for educational purposes and authorized security testing only. Only use on websites you own or have explicit written permission to test. Unauthorized directory brute forcing may be illegal in your jurisdiction and could violate terms of service.
Features

HTTP/HTTPS Support: Test both secure and insecure web applications
Multi-threading: Concurrent scanning for maximum performance
Custom Wordlists: Support for custom directory and file wordlist files
Status Code Filtering: Filter results by HTTP response codes (200, 403, 404, etc.)
Real-time Progress: Live scanning feedback with completion percentage
Command-line Interface: Professional CLI for automation and scripting
SSL Certificate Handling: Support for self-signed and invalid certificates
User Agent Rotation: Randomize requests to avoid detection

Requirements

Python 3.6+
See requirements.txt for dependencies

Installation
bashgit clone https://github.com/yourusername/web-directory-bruteforcer.git
cd web-directory-bruteforcer
pip install -r requirements.txt
Usage
Coming soon - tool is under development
Wordlists
The tool includes several built-in wordlists:

common.txt - Most common directories and files (500+ entries)
medium.txt - Extended wordlist for thorough scanning (2000+ entries)
large.txt - Comprehensive wordlist for deep reconnaissance (5000+ entries)

Output
Results are saved to the results/ directory with timestamps and target information.