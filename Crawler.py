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
import logging
import os
import requests
import signal
import sys
import time
import traceback
import urllib
from bs4 import BeautifulSoup
from url_normalize import url_normalize
import CrawlerDatabase

ERROR_LOG = 'error.log'

g_crawler = None # Allows us to get the main object from the signal handler

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
    """Called when the interrupt signal is received."""
    global g_crawler

    print("Exiting...")
    if g_crawler is not None:
        g_crawler.running = False
    print("Done")
    
def create_website_object(module_name, db):
    """Load the module that implements website-specific logic and instantiates an object of the class that does the work."""
    if module_name and os.path.isfile(module_name):
        if sys.version_info[0] < 3:
            module = imp.load_source("", module_name)
        else:
            module = mymodule = SourceFileLoader('modname', module_name).load_module()
        return module.create(db)
    return None

class Crawler(object):
    """Class containing the URL handlers."""

    def __init__(self, rate_secs, website_obj, db, max_depth, verbose):
        self.rate_secs = rate_secs
        self.website_obj = website_obj
        self.db = db
        self.max_depth = max_depth
        self.verbose = verbose
        self.running = True
        self.urls_to_crawl = [] # URLs awaiting crawling
        self.recent_urls = [] # Quick hack so we don't keep hitting the same URLs
        super(Crawler, self).__init__()

    def parse_content(self, url, content):
        """Parses data that was read from either a file or URL."""

        # Parse the page.
        soup = BeautifulSoup(content, 'html5lib')

        # Let the website object extract whatever it wants from the page.
        if self.website_obj is not None:
            self.website_obj.parse(url, soup)

        # Harvest new links.
        for a in soup.find_all('a', href=True):
            self.urls_to_crawl.append(a['href'])
        self.urls_to_crawl = list(dict.fromkeys(self.urls_to_crawl)) # Remove duplicates

    def visit_new_urls(self, parent_url, cookies, current_depth):
        """Visits URLs that we haven't visited yet."""

        # Crawl new links.
        for new_url in self.urls_to_crawl:

            # If the crawling has been cancelled.
            if self.running is False:
                return

            # Crawl the link.
            self.crawl_url(parent_url, new_url, cookies, current_depth + 1)

            # Wait.
            time.sleep(self.rate_secs)

    def crawl_file(self, file_name, cookies):
        """Starts crawling from a file."""

        # Open the file.
        with open(file_name, 'r') as f:

            # Read the entire contents of the file.
            content = f.read()

            # Crawl the content.
            self.parse_content("", content)

            # Visit the fresh links.
            self.visit_new_urls(url, cookies, 0)

    def crawl_url(self, parent_url, child_url, cookies, current_depth):
        """Crawls, starting at the given URL, up to the maximum depth."""

        # If we've exceeded the maximum depth.
        if self.max_depth is not None and current_depth >= self.max_depth:
            if self.verbose:
                print("Maximum crawl depth exceeded.")
            return

        # Canonicalize the URL.
        url = urljoin(parent_url, child_url)
        url = url_normalize(url)

        # If we've been here before.
        if url in self.recent_urls:
            if self.verbose:
                print("Skipping " + url + " because we've seen it before.")
            return

        try:
            # Download the page from the URL.
            if self.verbose:
                print("Requesting data from " + url + "...")
            response = requests.get(url, cookies=cookies, headers={'User-Agent': 'Mozilla/5.0'})

            # If downloaded....
            if response.status_code == 200:

                # Print the output.
                if self.verbose:
                    print("Parsing " + url + "...")

                # Don't revisit this anytime soon.
                self.recent_urls.append(url)

                # Process the content.
                self.parse_content(url, response.content)

                # Visit the fresh links.
                self.visit_new_urls(url, cookies, current_depth)

            # Print the error.
            elif self.verbose:
                print("Received HTTP Error " + str(response.status_code) + ".")

        except:
            print(traceback.format_exc())
            print(sys.exc_info()[0])
            print("Exception requesting data.")


def main():
    """Entry point for the app."""

    global g_crawler

    # Parse command line options.
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="", help="File to crawl.", required=False)
    parser.add_argument("--url", default="", help="URL to crawl.", required=False)
    parser.add_argument("--rate", type=int, default=1, help="Rate, in seconds, at which to crawl.", required=False)
    parser.add_argument("--max-depth", type=int, default=None, help="Maximum crawl depth.", required=False)
    parser.add_argument("--website-module", default=None, help="Python module that implements website-specific logic.", required=False)
    parser.add_argument("--mongodb-addr", default="localhost:27017", help="Address of the mongo database.", required=False)
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

    # Instantiate the object that connects to the database.
    db = None
    if args.mongodb_addr is not None:
        db = CrawlerDatabase.MongoDatabase()
        db.connect(args.mongodb_addr)

    # Instantiate the object that implements website-specific logic.
    website_obj = create_website_object(args.website_module, db)

    # Instantiate the object that does the crawling.
    g_crawler = Crawler(args.rate, website_obj, db, args.max_depth, args.verbose)

    # Register the signal handler.
    signal.signal(signal.SIGINT, signal_handler)

    # Configure the error logger.
    logging.basicConfig(filename=ERROR_LOG, filemode='w', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

    # Cookies to use when performing an HTTP request.
    cookies = None
    if website_obj is not None:
        cookies = website_obj.make_cookies(args)

    # Crawl a file.
    if len(args.file) > 0:
        g_crawler.crawl_file(args.file, cookies)

    # Crawl a URL.
    if len(args.url) > 0:
        g_crawler.crawl_url("", args.url, cookies, 0)

if __name__ == "__main__":
    main()
