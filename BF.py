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
import itertools
import requests
import sys
import time
import bs4
import urllib

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

    def make_cookies(self, args):
        """Builds the cookies dictionary that will be passed with the HTTP GET requests."""
        keyword_dict = dict(keyword="session ipa")
        search_dict = dict(search_settings = urllib.urlencode(keyword_dict))
        return search_dict

    def parse(self, url, soup):
        """Parses the contents downloaded from the URL, extracts the recipe, and stores it in the database."""

        # Ignore links from other sites.
        parsed = urlparse.urlparse(url)
        if parsed.netloc.find("www.brewersfriend.com") != 0:
            print("Invalid network location: " + parsed.netloc)
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
        recipe['title'] = title_header.get_text().strip()

        # Find the style.
        style_span = soup.find("span", {"itemprop": "recipeCategory"})
        if style_span is None:
            print("Failed to find the style.")
            return None
        recipe['style'] = style_span.get_text().strip()

        # Find the yield size.
        yield_size_span = soup.find("span", {"itemprop": "recipeYield"})
        if yield_size_span is None:
            print("Failed to find the yield size.")
            return None
        recipe['yield size'] = yield_size_span.get_text().strip()

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
        recipe['grains'] = fermentables

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
                hop[title] = column.get_text().strip()
            hops.append(hop)
        recipe['hops'] = hops

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
        recipe['yeasts'] = yeasts

        # Return the recipe so it can be stored in the database.
        return recipe

def main():
    """This is the entry point that is used to perform unit tests on this module."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="", help="URL to parse.", required=False)
    args = parser.parse_args()

    if args.url:
        response = requests.get(args.url, headers={'User-Agent': 'Mozilla/5.0'})

        if response.status_code == 200:
            soup = bs4.BeautifulSoup(response.content, 'html5lib')
            parser = BF(None)
            parser.parse(args.url, soup)
        else:
            print("Received status invalid code: " + str(response.status_code))

if __name__ == "__main__":
    main()
