# -*- coding: utf-8 -*-
# 
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
import os
import requests
import signal
import sys
from bs4 import BeautifulSoup
from url_normalize import url_normalize

g_crawler = None

# Import things so that they have the same name regardless of whether we are using python2 or python3.
if sys.version_info[0] < 3:
    import imp
    import urlparse
    from urlparse import urljoin
else:
    from importlib.machinery import SourceFileLoader
    import urllib.parse as urlparse
    from urllib.parse import urljoin


def signal_handler(signal, frame):
    print("Exiting...")
    if g_crawler is not None:
        g_crawler.running = False
    print("Done")
    
class Crawler(object):
    """Class containing the URL handlers."""

    def __init__(self, rate_secs, parse_module_name, max_depth, verbose):
        self.rate_secs = rate_secs
        self.parse_module = None
        self.max_depth = max_depth
        self.verbose = verbose
        self.running = True
        if os.path.isfile(parse_module_name):
            if sys.version_info[0] < 3:
                self.parse_module = imp.load_source("", parse_module_name)
            else:
                self.parse_module = mymodule = SourceFileLoader('modname', parse_module_name).load_module()
        super(Crawler, self).__init__()

    def crawl_file(self, file_name):
        """Starts crawling from a file."""
        with open(file_name, 'r') as f:
            pass

    def crawl_url(self, parent_url, child_url, current_depth):
        """Crawls, starting at the given URL, up to the maximum depth."""

        # If the crawling has been cancelled.
        if self.running is False:
            return

        # Canonicalize the URL.
        url = urljoin(parent_url, child_url)
        url = url_normalize(url)

        # Download the page from the URL.
        response = requests.get(url)

        # If downloaded....
        if response.status_code == 200:
            if self.verbose:
                print("Parsing " + url + "...")

            # Parse the page.
            soup = BeautifulSoup(response.content, 'html5lib')

            # Look for new links.
            if self.max_depth is > 0 or current_depth < self.max_depth:
                for a in soup.find_all('a', href=True):
                    self.crawl_url(url, a['href'], current_depth + 1)

def main():
    """Entry point for the app."""

    # Parse command line options.
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="", help="File to crawl.", required=False)
    parser.add_argument("--url", default="", help="URL to crawl.", required=False)
    parser.add_argument("--rate", type=int, default=0, help="Rate, in seconds, at which to crawl.", required=False)
    parser.add_argument("--max-depth", type=int, default=None, help="Maximum crawl depth.", required=False)
    parser.add_argument("--parse-module", default="", help="Python module that will parse each page.", required=False)
    parser.add_argument("--verbose", action="store_true", default=False, help="Enables verbose output.", required=False)

    try:
        args = parser.parse_args()
    except IOError as e:
        parser.error(e)
        sys.exit(1)

    # Sanity check.
    if len(args.file) == 0 and len(args.url) == 0:
        print("Neither a file nor a URL to crawl was specified.")
        sys.exit(1)

    g_crawler = Crawler(args.rate, args.parse_module, args.max_depth, args.verbose)

    # Register the signal handler.
    signal.signal(signal.SIGINT, signal_handler)

    # Crawl a file.
    if len(args.file) > 0:
        crawler.crawl_file(args.file)

    # Crawl a URL.
    if len(args.url) > 0:
        crawler.crawl_url("", args.url, 0)

if __name__ == "__main__":
    main()
