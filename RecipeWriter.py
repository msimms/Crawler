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
import json

ID_KEY = '_id'
STYLE_KEY = 'style'
YIELD_SIZE_KEY = 'yield size'
GRAINS_KEY = 'grains'
HOPS_KEY = 'hops'
YEASTS_KEY = 'yeasts'
FERMENTABLES_KEY = 'Fermentable'
AMOUNT_KEY = 'Amount'
VARIETY_KEY = 'Variety'
BOIL_KEY = 'Boil'
COMMMON_HOPS = ['cascade', 'centennial', 'citra', 'chinook', 'columbus', 'equinox', 'fuggles', 'kent goldings', 'golding', 'magnum', 'mosaic', 'victory', 'warrior']
UNITS = ['lb', 'oz', 'g', 'tsp', 'pkg', 'ounce', 'teaspoon', 'cup', 'pound', 'gal']


class RecipeWriter(object):
    """Reads beer recipes from the database and generates a new recipe."""

    def __init__(self):
        super(RecipeWriter, self).__init__()

    def normalize_grains_and_hops(self, grains, hops):
        """Since the recipes were collected from multiple sites, this attempts to normalize their structure."""
        if grains is None:
            return grains, hops

        new_grains = []
        new_hops = []

        search_list_func = lambda x,y : x.find(y) >= 0
        ignore_strs = ['[', '#', 'dme', 'extract', 'honey', 'moss', 'sugar', 'syrup', 'total', 'water', 'yeast']

        # Normalize grains, some websites lump the hops in with the grains for whatever reason.
        for grain in grains:

            # Was this formatted in a nice is python dictionary for us?
            if isinstance(grain, dict):

                # Do we have a dictionary with valid items?
                if AMOUNT_KEY in grain and FERMENTABLES_KEY in grain:
                    
                    amount = grain[AMOUNT_KEY]
                    fermentables = grain[FERMENTABLES_KEY]

                    # Cleanup the name. It might have the amount appended to it.
                    offset = fermentables.find(amount)
                    if offset > 0:
                        grain[FERMENTABLES_KEY] = fermentables[offset + len(amount):].strip()

                    # Does the string contain junk?
                    matched_ignore_strs = [search_list_func(grain[FERMENTABLES_KEY].lower(), i) for i in ignore_strs]
                    if any(matched_ignore_strs):
                        continue

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

                # Sanity check.
                if len(parts) == 0:
                    continue

                # Is the second part the units?
                matched_units = [search_list_func(parts[0].lower(), i) for i in UNITS]
                if any(matched_units):
                    amount += " "
                    amount += parts[0]
                    del parts[0]
                if '-' in parts:
                    parts.remove('-')

                # Sanity check.
                if len(parts) == 0:
                    continue

                # Build the description string and figure out if it is grains or hops
                # because some websites lump them together.
                is_grain = True
                is_hop = False
                in_boil = False
                for part in parts:

                    part_lower = part.lower()

                    # Sanity check.
                    if len(part_lower) == 0:
                        continue

                    # Some recipes have comments in paraenthesis or brackets at the end of the string. We don't need them.
                    if part_lower[0] in ['(', '[']:
                        break

                    # Did someone put hops in the grains category?
                    if part_lower in COMMMON_HOPS:
                        is_grain = False
                        is_hop = True
                    elif is_hop:
                        in_boil = in_boil or part_lower.find('at') >= 0 or part_lower.find('boil')
                        if in_boil and part_lower.find('hop') >= 0:
                            boil += part

                    # Fairly sure this is part of the grains.
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

    def export_to_json(self, db):
        """Exports the beer recipes to JSON."""
        all_data = []
        all_pages = db.retrieve_all_pages()
        for page in all_pages:
            grain_value = None
            hops_value = None

            if GRAINS_KEY in page:
                grain_value = page[GRAINS_KEY]
            else: # Filter out pages that aren't recipes
                continue

            if HOPS_KEY in page:
                hops_value = page[HOPS_KEY]

            norm_grains, norm_hops = self.normalize_grains_and_hops(grain_value, hops_value)

            page[GRAINS_KEY] = norm_grains
            page[HOPS_KEY] = norm_hops

            if YEASTS_KEY in page:
                page[YEASTS_KEY] = self.normalize_yeast(page[YEASTS_KEY])

            # This isn't serializable so get rid of it.
            if ID_KEY in page:
                del page[ID_KEY]

            all_data.append(page)
        
        return json.dumps(all_data)

    def list_styles(self, db):
        all_pages = db.retrieve_all_pages()

        # The recipes were collected from various sites and will need normalizing
        # after we filter for the recipes that match the search criteria.
        for page in all_pages:

            if STYLE_KEY in page:
                pass

def main():
    """This is the entry point that is used to perform unit tests on this module."""

    # Command line options.
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default=None, help="Style of beers to dump.", required=False)
    parser.add_argument("--mongodb-addr", default="localhost:27017", help="Address of the mongo database.", required=False)
    parser.add_argument("--json", action="store_true", default=False, help="Exports the recipes as JSON.", required=False)
    parser.add_argument("--list-styles", action="store_true", default=False, help="Prints all styles of beer found in the database.", required=False)
    args = parser.parse_args()

    # Instantiate the object that connects to the database.
    db = None
    if args.mongodb_addr is not None:
        db = CrawlerDatabase.MongoDatabase()
        db.connect(args.mongodb_addr)

    # Sanity check.
    if db is None:
        print("ERROR: No database.")

    # This option allows the user to dump recipes to stdout.
    if args.style is not None:

        writer = RecipeWriter()
        writer.generate_avg_recipe(db, args.style)

    # Are we exporting the recipes?
    if args.json:

        writer = RecipeWriter()
        data = writer.export_to_json(db)
        print(data)

    # Are we exporting the styles?
    if args.list_styles:

        writer = RecipeWriter()
        data = writer.list_styles(db)
        print(data)


if __name__ == "__main__":
    main()
