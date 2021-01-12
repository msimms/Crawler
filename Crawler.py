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
import Keys

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
    
def create_website_object(module_name):
    """Load the module that implements website-specific logic and instantiates an object of the class that does the work."""
    if module_name and os.path.isfile(module_name):
        if sys.version_info[0] < 3:
            module = imp.load_source("", module_name)
        else:
            module = mymodule = SourceFileLoader('modname', module_name).load_module()
        return module.create()
    return None

def get_url_root(url):
    p = urlparse.urlparse(url)
    if p.hostname and len(p.hostname) > 0:
        return p.hostname
    return p.path

class Crawler(object):
    """Class containing the URL handlers."""

    def __init__(self, seed_url, rate_secs, website_objs, db, max_depth, min_revisit_secs, crawl_other_websites, verbose):
        """Constructor."""
        self.seed_url = seed_url
        self.rate_secs = rate_secs
        self.website_objs = website_objs
        self.db = db
        self.max_depth = max_depth
        self.min_revisit_secs = min_revisit_secs
        self.crawl_other_websites = crawl_other_websites
        self.verbose = verbose
        self.running = True
        self.last_crawl_time = 0 # The timestamp of the last time we visited a URL.
        self.error_urls = [] # These URLs are giving us problems, skip them.
        super(Crawler, self).__init__()

    def verbose_print(self, msg):
        """Helper function."""
        if self.verbose:
            print(msg)

    def log_error(self, log_str):
        """Writes an error message to the log file."""
        logger = logging.getLogger()
        logger.error(log_str)
        self.verbose_print(log_str)

    def create_or_update_database(self, url, blob):
        """Helper function."""
        if self.db is None:
            return

        # Let the user know what's going on.
        self.verbose_print("Storing " + url + " in the database...")

        # Update database.
        page_from_db = self.db.retrieve_page(url)
        now = time.time()
        if page_from_db:
            success = self.db.update_page(url, now, blob)
        else:
            success = self.db.create_page(url, now, blob)
        if not success:
            self.log_error("ERROR: Failed to store " + url + " in the database...")

    def parse_content(self, url, content):
        """Parses data that was read from either a file or URL."""

        # Let the user know what's going on.
        self.verbose_print("Parsing " + url + "...")

        # Parse the page.
        soup = BeautifulSoup(content, 'html5lib')

        # Let the website object extract whatever information it wants from the page.
        blob = None
        for website_obj in self.website_objs:
            blob = website_obj.parse(url, soup)

        # Harvest any new URLs.
        urls_to_crawl = []
        for a in soup.find_all('a', href=True):
            urls_to_crawl.append(a['href'])
        urls_to_crawl = list(dict.fromkeys(urls_to_crawl)) # Remove duplicates
        return blob, urls_to_crawl

    def visit_new_urls(self, parent_url, urls_to_crawl, current_depth):
        """Visits URLs that we haven't visited yet."""

        # Crawl all new URLs.
        for new_url in urls_to_crawl:

            # If the crawling has been cancelled.
            if self.running is False:
                return

            # Do we need to throttle ourselves?
            if self.rate_secs is not None and time.time() - self.last_crawl_time < self.rate_secs:
                self.verbose_print("Sleeping for " + str(self.rate_secs) + " second(s).")
                time.sleep(self.rate_secs)

            # Crawl the URL.
            crawled = self.crawl_url(parent_url, new_url, current_depth + 1)

    def crawl_file(self, file_name):
        """Starts crawling from a file."""

        # Open the file.
        with open(file_name, 'r') as f:

            # Read the entire contents of the file.
            content = f.read()

            # Crawl the content.
            blob, urls_to_crawl = self.parse_content("", content)

            # Visit the fresh URLs.
            self.visit_new_urls(url, urls_to_crawl, 0)

    def crawl_url(self, parent_url, child_url, current_depth):
        """Crawls, starting at the given URL, up to the maximum depth."""

        # If we've exceeded the maximum depth.
        if self.max_depth is not None and current_depth >= self.max_depth:
            self.verbose_print("Maximum crawl depth exceeded.")
            return False

        # Canonicalize the URL.
        url = urljoin(parent_url, child_url)
        url = url_normalize(url)

        # Drop any query parameters.
        parts = url.split('#')
        url = parts[0]

        # Is this URL from the seed website? Do we care?
        if not self.crawl_other_websites:
            root_url = get_url_root(url)
            if root_url != self.seed_url:
                return False

        # If this URL has given us problems then skip it.
        if url in self.error_urls:
            self.verbose_print("Skipping " + url + " because it has given us problems.")
            return False

        # Only proceed if we have a module that can parse this URL (though proceed if we don't have any modules loaded).
        # Also, if we have a module that can parse it, see if it has any cookies it wants to add to the request.
        cookies = None
        if len(self.website_objs) > 0:
            interesting = False
            for website_obj in self.website_objs:
                interesting = website_obj.is_interesting_url(url)
                if interesting:
                    cookies = website_obj.make_cookies(url)
                    break
            if not interesting:
                self.verbose_print("Skipping " + url + " because there are no modules to parse it.")
                return False

        # If we've been here before and it was within our revisit window then just skip.
        # Don't bother doing this check for the first URL, since it'll be the one the user told us to crawl.
        if current_depth > 0 and self.db and self.min_revisit_secs and self.min_revisit_secs > 0:

            # Get the database record corresonding to this URL.
            page_from_db = self.db.retrieve_page(url)
            if page_from_db and Keys.LAST_VISIT_TIME_KEY in page_from_db:

                # How long since we were last here?
                now = time.time()
                last_visited_diff = now - page_from_db[Keys.LAST_VISIT_TIME_KEY]
                if last_visited_diff < self.min_revisit_secs:
                    last_visited_units = "second"
                    if last_visited_diff >= 86400:
                        last_visited_diff = last_visited_diff / 86400
                        last_visited_units = "day"
                    elif last_visited_diff >= 3600:
                        last_visited_diff = last_visited_diff / 3600
                        last_visited_units = "hour"
                    elif last_visited_diff >= 60:
                        last_visited_diff = last_visited_diff / 60
                        last_visited_units = "minute"
                    self.verbose_print("Skipping " + url + " because we visited it " + str(last_visited_diff) + " " + last_visited_units + "(s) ago.")
                    return False

        try:

            # Download the page from the URL.
            self.verbose_print("Requesting data from " + url + "...")
            response = requests.get(url, cookies=cookies, headers={'User-Agent': 'Mozilla/5.0'})

            # If downloaded....
            if response.status_code == 200:

                # Process the content. Anything the parsing module wants stored will be returned in the blob.
                blob, urls_to_crawl = self.parse_content(url, response.content)

                # Note that we visited this webpage.
                self.create_or_update_database(url, blob)

                # Make a note of the time.
                self.last_crawl_time = time.time()

                # Visit the fresh URLs.
                self.visit_new_urls(url, urls_to_crawl, current_depth)

                return True

            # Nothing downloaded.
            else:

                # Make sure we don't go here again.
                self.error_urls.append(url)

                # Print an error.
                self.log_error("ERROR: Received HTTP Code " + str(response.status_code) + ".")

        except:

            # Make sure we don't go here again.
            self.error_urls.append(url)

            # Log an error.
            self.log_error(traceback.format_exc())
            self.log_error(sys.exc_info()[0])
            self.log_error("ERROR: Exception requesting data.")

        return False


def main():
    """Entry point for the app."""

    global g_crawler

    # Parse command line options.
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="", help="File to crawl.", required=False)
    parser.add_argument("--url", default="", help="URL to crawl.", required=False)
    parser.add_argument("--rate", type=int, default=1, help="Rate, in seconds, at which to crawl.", required=False)
    parser.add_argument("--max-depth", type=int, default=None, help="Maximum crawl depth.", required=False)
    parser.add_argument("--min-revisit-secs", type=int, default=86400, help="Minimum number of seconds before allowing a URL to be revisited.", required=False)
    parser.add_argument("--website-modules", default="", help="Python modules that implement website-specific logic.", required=False)
    parser.add_argument("--mongodb-addr", default="localhost:27017", help="Address of the mongo database.", required=False)
    parser.add_argument("--crawl-other-websites", action="store_true", default=False, help="If not set will stay on links that belong to the seed URL.", required=False)
    parser.add_argument("--verbose", action="store_true", default=False, help="Enables verbose output.", required=False)

    try:
        args = parser.parse_args()
    except IOError as e:
        parser.error(e)
        sys.exit(1)

    # Print the settings.
    print("Using the following settings:")
    var_args = vars(args)
    for arg_name in var_args:
        print("* " + arg_name + ": " + str(var_args[arg_name]))
    print("")

    # Sanity check.
    if len(args.file) == 0 and len(args.url) == 0:
        print("Neither a file nor a URL to crawl was specified.")
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Instantiate the object that connects to the database.
    db = None
    if args.mongodb_addr is not None:
        db = CrawlerDatabase.MongoDatabase()
        db.connect(args.mongodb_addr)

    # Instantiate the object that implements website-specific logic.
    website_objs = []
    if len(args.website_modules) > 0:
        website_module_names = args.website_modules.split(',')
        for website_module_name in website_module_names:
            website_obj = create_website_object(website_module_name)
            website_objs.append(website_obj)

    seed_url = ""
    if len(args.url) > 0:
        seed_url = get_url_root(args.url)

    # Instantiate the object that does the crawling.
    g_crawler = Crawler(seed_url, args.rate, website_objs, db, args.max_depth, args.min_revisit_secs, args.crawl_other_websites, args.verbose)

    # Register the signal handler.
    signal.signal(signal.SIGINT, signal_handler)

    # Configure the error logger.
    logging.basicConfig(filename=ERROR_LOG, filemode='w', level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

    # Crawl a file.
    if len(args.file) > 0:
        g_crawler.crawl_file(args.file)

    # Crawl a URL.
    if len(args.url) > 0:
        g_crawler.crawl_url("", args.url, 0)

if __name__ == "__main__":
    main()
