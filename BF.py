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

import CrawlerDatabase
import ParseModule
import argparse
import requests
import sys
import time
from bs4 import BeautifulSoup

# Import things so that they have the same name regardless of whether we are using python2 or python3.
if sys.version_info[0] < 3:
    import urlparse
else:
    import urllib.parse as urlparse
    
def create(db):
    return BF(db)

class BF(ParseModule.ParseModule):
    """Module for parsing web pages from brewersfriend.com."""

    def __init__(self, db):
        self.db = db
        ParseModule.ParseModule.__init__(self)

    def parse(self, url, soup):
        """Parses the contents downloaded from the URL, extracts the recipe, and stores it in the database."""

        # Ignore links from other sites.
        parsed = urlparse.urlparse(url)
        if parsed.netloc.find("www.brewersfriend.com") != 0:
            print("Invalid network location: " + parsed.netloc)
            return False

        # Parse the recipe.
        blob = {}

        # Find the fermentables (i.e. the grains).
        grains_div = soup.find("div", {"id": "fermentables"})
        if grains_div is None:
            print("Failed to find the fermentables section.")
            return False
        grains_table = grains_div.find("table")
        if grains_table is None:
            print("Failed to find the fermentables table.")
            return False

        print(grains_table)

        # Find the hop schedule.
        hops_div = soup.find("div", {"id": "hops"})
        if hops_div is None:
            print("Failed to find the hops section.")
        #print(hops_div)

        if self.db is not None:

            # Store it.
            visit_time = time.time()
            if not self.db.create_page(url, visit_time, blob):

                # Page was not created, presumably because it already exists, so just update it.
                return self.db.update_page(url, visit_time, blob)

        # Page was created.
        return True

def main():
    """This is the entry point that is used to perform unit tests on this module."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="", help="URL to parse.", required=False)
    args = parser.parse_args()

    response = requests.get(args.url, headers={'User-Agent': 'Mozilla/5.0'})
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html5lib')
        parser = BF(None)
        parser.parse(args.url, soup)
    else:
        print("Received status invalid code: " + str(response.status_code))

if __name__ == "__main__":
    main()
