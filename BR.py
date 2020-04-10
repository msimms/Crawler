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
    return BR()

class BR(ParseModule.ParseModule):
    """Module for parsing web pages from beerrecipes.org."""

    def __init__(self):
        """Constructor."""
        ParseModule.ParseModule.__init__(self)

    def make_cookies(self, url):
        """Builds the cookies dictionary that will be passed with the HTTP GET requests."""
        return None

    def is_interesting_url(self, url):
        """Returns TRUE if this URL is something this class can parse. Returns FALSE otherwise."""
        parsed = urlparse.urlparse(url)
        return parsed.netloc.find("beerrecipes.org") >= 0

    def parse(self, url, soup):
        """Parses the contents downloaded from the URL, extracts the recipe, and stores it in the database."""

        # Ignore links from other sites.
        if not self.is_interesting_url(url):
            print("Invalid network location: " + parsed.netloc)
            return None

        recipe = {}
        fermentables = []
        hops = []
        yeasts = []

        # Find the title.
        brew_name = soup.find("h1", {"itemprop": "name"})
        if brew_name is None:
            print("Failed to find the brew name.")
            return None
        recipe[TITLE_KEY] = brew_name.get_text().strip()

        # Find and parse the ingredients.
        ingredient_items = soup.find_all("span", {"itemprop": "ingredients"})
        for ingredient_item in ingredient_items:
            item_text = ingredient_item.get_text().strip()
            if item_text.find("minutes") > 0 or item_text.find("flameout") > 0 or item_text.find("knockout") > 0 or item_text.find("end of boil") > 0 or item_text.find("dry hop") > 0:
                hops.append(item_text)
            elif item_text.find("pack") > 0 or item_text.find("yeast") > 0:
                yeasts.append(item_text)
            else:
                fermentables.append(item_text)
        recipe[GRAINS_KEY] = fermentables
        recipe[HOPS_KEY] = hops
        recipe[YEASTS_KEY] = yeasts

        # Find the yield.
        yield_item = soup.find("span", {"itemprop": "recipeYield"})
        if yield_item:
            recipe[YIELD_SIZE_KEY] = yield_item.get_text().strip()

        # Find the style.
        paragraphs = soup.find_all("p")
        for paragraph in paragraphs:
            paragraph_text = paragraph.get_text()
            style_offset = paragraph_text.find("Beer Style:")
            if style_offset > 0:
                newline_offset = paragraph_text.find("\n", style_offset)
                recipe[STYLE_KEY] = paragraph_text[style_offset+len("Beer Style:"):newline_offset].strip()

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
            parser = BR()
            parser.parse(args.url, soup)
        else:
            print("ERROR: Received status invalid code: " + str(response.status_code))

    # This option allows the user to dump recipes to stdout.
    if args.dump:

        # Sanity check.
        if db is None:
            print("ERROR: No database.")

        parser = BR()
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
