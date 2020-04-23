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
import argparse
import collections

STYLE_KEY = 'style'
YIELD_SIZE_KEY = 'yield size'
GRAINS_KEY = 'grains'
HOPS_KEY = 'hops'
YEASTS_KEY = 'yeasts'
FERMENTABLES_KEY = 'Fermentable'
AMOUNT_KEY = 'Amount'
VARIETY_KEY = 'Variety'


class RecipeWriter(object):
    """Reads beer recipes from the database and generates a new recipe."""

    def __init__(self):
        super(RecipeWriter, self).__init__()

    def normalize_grains_and_hops(self, grains, hops):
        new_grains = []
        new_hops = []

        # Normalize grains
        for grain in grains:
            if isinstance(grain, dict):
                new_grains.append(grain)
            else:
                parts = grain.split(' ')

                # These are things we might find in the string.
                amount = ""
                desc = ""

                # Should start with an amount.
                amount = parts[0]
                del parts[0]

                # Is the second part the units?
                units = ['lb', 'oz', 'tsp', 'pkg', 'ounce', 'teaspoon']
                units_func = lambda x,y : x.find(y) >= 0
                matched_units = [units_func(parts[0], i) for i in units]
                if any(matched_units):
                    amount += " "
                    amount += parts[0]
                    del parts[0]
                if '-' in parts:
                    parts.remove('-')

                # Build the description string and figure out if it is grains or hops
                # because some websites lump them together.
                is_grain = True
                for part in parts:
                    part_lower = part.lower()
                    if part_lower.find('hop') >= 0 or part_lower.find('boil') >= 0:
                        is_grain = False
                    desc += part
                    desc += " "
                desc.strip()

                # Did we find grains?
                if is_grain and len(desc) > 0 and len(amount) > 0:
                    grain = {}
                    grain[FERMENTABLES_KEY] = desc
                    grain[AMOUNT_KEY] = amount
                    new_grains.append(grain)

                # Did we find any hops?
                elif len(desc) > 0 and len(amount) > 0:
                    hops = {}
                    hops[HOPS_KEY] = desc
                    hops[AMOUNT_KEY] = amount
                    new_hops.append(hops)

        # Normalize hops
        for hop in hops:
            if isinstance(hop, dict):
                new_hops.append(hop)

        return new_grains, new_hops

    def normalize_yeast(self, yeast):
        return yeast

    def generate_avg_recipe(self, db, style):
        all_pages = db.retrieve_all_pages()
        lower_style = style.lower()

        grains = []
        hops = []
        yeasts = []

        # The recipes were collected from various sites and will need normalizing
        # after we filter for the recipes that match the search criteria.
        for page in all_pages:

            # Filter for the desired beer style.
            if STYLE_KEY in page and page[STYLE_KEY].lower().find(lower_style) >= 0:
                grain_value = None
                hops_value = None

                if GRAINS_KEY in page:
                    grain_value = page[GRAINS_KEY]
                if HOPS_KEY in page:
                    hops_value = page[HOPS_KEY]

                norm_grains, norm_hops = self.normalize_grains_and_hops(grain_value, hops_value)
                grains.extend(norm_grains)
                hops.extend(norm_hops)

                if YEASTS_KEY in page:
                    yeast = self.normalize_yeast(page[YEASTS_KEY])
                    yeasts.extend(yeast)

        print("------")
        print("Grains")
        print("------")
        #sorted_grains = sorted(grains, key=get_grains_sort_key)
        for grain in grains:
            print(grain)

        print("----")
        print("Hops")
        print("----")
        for hop in hops:
            print(hop)

        print("------")
        print("Yeasts")
        print("------")
        for yeast in collections.Counter(yeasts):
            print(yeast)

def main():
    """This is the entry point that is used to perform unit tests on this module."""

    # Command line options.
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="", help="Style of beers to dump.", required=False)
    parser.add_argument("--mongodb-addr", default="localhost:27017", help="Address of the mongo database.", required=False)
    args = parser.parse_args()

    # Instantiate the object that connects to the database.
    db = None
    if args.mongodb_addr is not None:
        db = CrawlerDatabase.MongoDatabase()
        db.connect(args.mongodb_addr)

    # This option allows the user to dump recipes to stdout.
    if args.style is not None:

        # Sanity check.
        if db is None:
            print("ERROR: No database.")

        writer = RecipeWriter()
        writer.generate_avg_recipe(db, args.style)

if __name__ == "__main__":
    main()
