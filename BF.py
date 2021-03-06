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
import Keys
import ParseModule
import argparse
import itertools
import requests
import sys
import time
import bs4
import urllib

TITLE_KEY = 'title'
STYLE_KEY = 'style'
YIELD_SIZE_KEY = 'yield size'
GRAINS_KEY = 'grains'
HOPS_KEY = 'hops'
YEASTS_KEY = 'yeasts'

# Import things so that they have the same name regardless of whether we are using python2 or python3.
if sys.version_info[0] < 3:
    import urlparse
else:
    import urllib.parse as urlparse

# Handle another python2/3 difference.
if sys.version_info[0] < 3:
    zip_func = itertools.izip
else:
    zip_func = zip

# Factory function.
def create():
    return BF()

class BF(ParseModule.ParseModule):
    """Module for parsing web pages from brewersfriend.com."""

    def __init__(self):
        """Constructor."""
        ParseModule.ParseModule.__init__(self)

    def make_cookies(self, url):
        """Builds the cookies dictionary that will be passed with the HTTP GET requests."""
        parsed = urlparse.urlparse(url)
        if parsed.netloc.find("brewersfriend.com") >= 0 and parsed.path.find("search") >= 0:
            #search_dict = dict(search_settings = urllib.urlencode(dict(keyword = "session ipa", method = "allgrain")))
            search_dict = dict(search_settings = '%7B%22keyword%22%3A%22session+ipa%22%2C%22method%22%3A%22allgrain%22%2C%22units%22%3A%22us%22%7D')
            return search_dict
        return None

    def is_interesting_url(self, url):
        """Returns TRUE if this URL is something this class can parse. Returns FALSE otherwise."""
        parsed = urlparse.urlparse(url)
        return parsed.netloc.find("brewersfriend.com") >= 0

    def parse(self, url, soup):
        """Parses the contents downloaded from the URL, extracts the recipe, and stores it in the database."""

        # Ignore links from other sites.
        if not self.is_interesting_url(url):
            print("Invalid network location for this module: " + url)
            return None

        recipe = {}
        fermentable_titles = []
        hop_titles = []

        # Find the title.
        title_div = soup.find("div", {"id": "viewTitle"})
        if title_div is None:
            print("Failed to find the title div.")
            return None
        title_header = title_div.find("h3")
        if title_header is None:
            print("Failed to find the title header.")
            return None
        recipe[TITLE_KEY] = title_header.get_text().strip()

        # Find the style.
        style_span = soup.find("span", {"itemprop": "recipeCategory"})
        if style_span is None:
            print("Failed to find the style.")
            return None
        recipe[STYLE_KEY] = style_span.get_text().strip()

        # Find the yield size.
        yield_size_span = soup.find("span", {"itemprop": "recipeYield"})
        if yield_size_span is None:
            print("Failed to find the yield size.")
            return None
        recipe[YIELD_SIZE_KEY] = yield_size_span.get_text().strip()

        # Find the fermentables (i.e. the grains).
        grains_div = soup.find("div", {"id": "fermentables"})
        if grains_div is None:
            print("Failed to find the fermentables div.")
            return None
        grains_table = grains_div.find("table")
        if grains_table is None:
            print("Failed to find the fermentables table.")
            return None

        # Find the fermentables column titles.
        grains_table_titles = grains_table.find("tr")
        if grains_table_titles is None:
            print("Failed to find the fermentables table column titles.")
            return None
        columns = grains_table_titles.findAll("th")
        for column in grains_table_titles:
            if (isinstance(column, bs4.element.Tag)):
                fermentable_titles.append(column.get_text().strip())
        if len(fermentable_titles) == 0:
            print("Could not find the column titles for the fermentables table.")
            return None

        # Find the fermentables body.
        grains_table_body = grains_table.find("tbody")
        if grains_table_body is None:
            print("Failed to find the fermentables table body.")
            return None
        grains_table_rows = grains_table_body.findAll("tr")
        if grains_table_rows is None:
            print("Failed to find the fermentables table row.")
            return None

        # Parse the fermentables.
        fermentables = []
        for row in grains_table_rows:
            fermentable = {}
            columns = row.findAll("td")
            for title, column in zip_func(fermentable_titles, columns):
                fermentable[title] = column.get_text().strip()
            fermentables.append(fermentable)
        recipe[GRAINS_KEY] = fermentables

        # Find the hop schedule.
        hops_div = soup.find("div", {"id": "hops"})
        if hops_div is None:
            print("Failed to find the hops div.")
            return None
        hops_table = hops_div.find("table")
        if hops_table is None:
            print("Failed to find the hops table.")
            return None

        # Find the hops column titles.
        hops_table_titles = hops_table.find("tr")
        if hops_table_titles is None:
            print("Failed to find the hops table column titles.")
            return None
        columns = hops_table_titles.findAll("th")
        for column in hops_table_titles:
            if (isinstance(column, bs4.element.Tag)):
                hop_titles.append(column.get_text().strip())
        if len(hop_titles) == 0:
            print("Could not find the column titles for the hops table.")
            return None

        # Find the hops body.
        hops_table_body = hops_table.find("tbody")
        if hops_table_body is None:
            print("Failed to find the hops table body.")
            return None
        hops_table_rows = hops_table_body.findAll("tr")
        if hops_table_rows is None:
            print("Failed to find the hops table row.")
            return None

        # Parse the hops.
        hops = []
        for row in hops_table_rows:
            hop = {}
            columns = row.findAll("td")
            for title, column in zip_func(hop_titles, columns):

                # If there's a link in the cell then use the text from the link.
                href = column.find("a")
                if href:
                    hop[title] = href.get_text().strip()
                else:
                    hop[title] = column.get_text().strip()
            hops.append(hop)
        recipe[HOPS_KEY] = hops

        # Find the yeasts section.
        yeasts = []
        yeasts_div = soup.find("div", {"id": "yeasts"})
        if yeasts_div is None:
            print("Failed to find the yeasts section.")
            return None
        yeasts_table = yeasts_div.find("table")
        if yeasts_table is None:
            print("Failed to find the yeasts table.")
            return None
        yeasts_table_head = yeasts_table.find("thead")
        if yeasts_table_head is None:
            print("Failed to find the yeasts table head.")
            return None
        yeasts_table_row = yeasts_table_head.findAll("tr")
        for row in yeasts_table_row:
            yeasts.append(row.get_text().strip())
        recipe[YEASTS_KEY] = yeasts

        # Return the recipe so it can be stored in the database.
        return recipe

def main():
    """This is the entry point that is used to perform unit tests on this module."""

    # Command line options.
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="", help="URL to parse.", required=False)
    parser.add_argument("--dump", action="store_true", default=False, help="Dumps recipes to stdout.", required=False)
    parser.add_argument("--style", default="", help="Style of beers to dump.", required=False)
    parser.add_argument("--mongodb-addr", default="localhost:27017", help="Address of the mongo database.", required=False)
    args = parser.parse_args()

    # Instantiate the object that connects to the database.
    db = None
    if args.mongodb_addr is not None:
        db = CrawlerDatabase.MongoDatabase()
        db.connect(args.mongodb_addr)

    # This option exists for testing by allowing the user to give a URL directly to the parser.
    if args.url:
        response = requests.get(args.url, headers={'User-Agent': 'Mozilla/5.0'})

        if response.status_code == 200:
            soup = bs4.BeautifulSoup(response.content, 'html5lib')
            parser = BF()
            parser.parse(args.url, soup)
        else:
            print("ERROR: Received status invalid code: " + str(response.status_code))

    # This option allows the user to dump recipes to stdout.
    if args.dump:

        # Sanity check.
        if db is None:
            print("ERROR: No database.")

        parser = BF()
        all_pages = db.retrieve_all_pages()
        for page in all_pages:
            if Keys.URL_KEY in page and parser.is_interesting_url(page[Keys.URL_KEY]):
                if TITLE_KEY in page:
                    if len(args.style) > 0:
                        if STYLE_KEY in page and page[STYLE_KEY].lower().find(args.style.lower()) != -1:
                            print(page)
                    else:
                        print(page)

if __name__ == "__main__":
    main()
