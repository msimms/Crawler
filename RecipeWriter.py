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
BOIL_KEY = 'Boil'
COMMMON_HOPS = ['cascade', 'kent goldings', 'golding', 'citra', 'centennial', 'mosaic', 'columbus', 'equinox']
UNITS = ['lb', 'oz', 'tsp', 'pkg', 'ounce', 'teaspoon', 'cup', 'pound', 'gal']


class RecipeWriter(object):
    """Reads beer recipes from the database and generates a new recipe."""

    def __init__(self):
        super(RecipeWriter, self).__init__()

    def normalize_grains_and_hops(self, grains, hops):
        new_grains = []
        new_hops = []

        search_list_func = lambda x,y : x.find(y) >= 0
        ignore_strs = ['(', '[', '#', '-', 'sugar', 'water', 'total', 'dme', 'honey', 'syrup', 'moss', 'yeast', 'extract']

        # Normalize grains
        for grain in grains:

            # Was this formatted in a nice is python dictionary for us?
            if isinstance(grain, dict):
                if AMOUNT_KEY in grain and FERMENTABLES_KEY in grain:
                    amount = grain[AMOUNT_KEY]
                    fermentables = grain[FERMENTABLES_KEY]
                    offset = fermentables.find(amount)
                    if offset > 0:
                        grain[FERMENTABLES_KEY] = fermentables[offset + len(amount):].strip()
                new_grains.append(grain)
            else:
                # Does the string contain junk?
                matched_ignore_strs = [search_list_func(grain.lower(), i) for i in ignore_strs]
                if any(matched_ignore_strs):
                    continue

                # These are things we might find in the string.
                amount = ""
                desc = ""
                boil = ""

                # Should start with an amount.
                parts = grain.split(' ')
                amount = parts[0]
                del parts[0]

                # Is the second part the units?
                matched_units = [search_list_func(parts[0].lower(), i) for i in UNITS]
                if any(matched_units):
                    amount += " "
                    amount += parts[0]
                    del parts[0]
                if '-' in parts:
                    parts.remove('-')

                # Build the description string and figure out if it is grains or hops
                # because some websites lump them together.
                is_grain = True
                is_hop = False
                in_boil = False
                for part in parts:

                    part_lower = part.lower()

                    if part_lower in COMMMON_HOPS:
                        is_grain = False
                        is_hop = True

                    elif is_hop:
                        in_boil = in_boil or part_lower.find('at') >= 0 or part_lower.find('boil')
                        if in_boil and part_lower.find('hop') >= 0:
                            boil += part

                    if not in_boil:
                        desc += part
                        desc += " "

                # Did we find grains?
                if is_grain and len(desc) > 0:
                    grain = {}
                    grain[FERMENTABLES_KEY] = desc.strip()
                    if len(amount) > 0:
                        grain[AMOUNT_KEY] = amount
                    new_grains.append(grain)

                # Did we find any hops?
                elif is_hop and len(desc) > 0:
                    hops = {}
                    hops[VARIETY_KEY] = desc.strip()
                    if len(amount) > 0:
                        hops[AMOUNT_KEY] = amount
                    if len(boil) > 0:
                        hops[BOIL_KEY] = boil
                    new_hops.append(hops)

        # Normalize hops.
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
        fermentable_names = []
        for grain in grains:
            fermentable_names.append(grain[FERMENTABLES_KEY])
        counted_fermentables = collections.Counter(fermentable_names).most_common()
        for fermentable in counted_fermentables:
            print(fermentable)

        print("----")
        print("Hops")
        print("----")
        hop_names = []
        for hop in hops:
            hop_names.append(hop[VARIETY_KEY])
        counted_hop_names = collections.Counter(hop_names).most_common()
        for hop_name in counted_hop_names:
            print(hop_name)

        print("------")
        print("Yeasts")
        print("------")
        counted_yeasts = collections.Counter(yeasts).most_common()
        for yeast in counted_yeasts:
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
