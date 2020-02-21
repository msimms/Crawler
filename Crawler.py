# MIT License
# 
# Copyright (c) 2020 Mike Simms
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import requests
from bs4 import BeautifulSoup

page = requests.get(url)
soup = BeautifulSoup(page.content, 'html.parser')

def signal_handler(signal, frame):
    print("Exiting...")
    print("Done")
    
class WebCrawler(object):
    """Class containing the URL handlers."""

    def __init__(self, rate_secs, parse_module_name):
        self.rate_secs = rate_secs
        self.parse_module_name = parse_module_name
        super(WebCrawler, self).__init__()

    def crawl_file(self, file_name):
        with open(file_name, 'r') as f:
            pass

    def crawl_url(self, url):
        response = requests.get(url)
        print(response)
        if response.status_code == 200:
            pass

def main():
    """Entry point for the app."""

    # Parse command line options.
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="", help="File to crawl.", required=False)
    parser.add_argument("--url", default="", help="URL to crawl.", required=False)
    parser.add_argument("--rate", type=int, default=0, help="Rate, in seconds, at which to crawl.", required=False)
    parser.add_argument("--parse-module", default="", help="Python module that will parse each page.", required=False)

    try:
        args = parser.parse_args()
    except IOError as e:
        parser.error(e)
        sys.exit(1)

    # Sanity check.
    if len(args.file) == 0 and len(args.url) == 0:
        print("Neither a file nor a URL to crawl was specified.")
        sys.exit(1)

    crawler = WebCrawler(args.rate, args.parse_module)

    # Register the signal handler.
    signal.signal(signal.SIGINT, signal_handler)

    # Crawl a file.
    if len(args.file) > 0:
        crawler.crawl_file(args.file)

    # Crawl a URL.
    if len(args.url) > 0:
        crawler.crawl_file(args.url)

if __name__ == "__main__":
    main()
