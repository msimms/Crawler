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
import re

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
COMMMON_HOPS = ['amarillo', 'cascade', 'centennial', 'citra', 'chinook', 'columbus', 'equinox', 'fuggles', 'kent goldings', 'golding', 'magnum', 'mosaic', 'victory', 'warrior']
UNITS = ['lb', 'oz', 'g', 'tsp', 'tbsp', 'pkg', 'ounce', 'teaspoon', 'cup', 'pound', 'gal']

SEARCH_LIST_FUNC = lambda x,y : x.find(y) >= 0

class RecipeWriter(object):
    """Reads beer recipes from the database and generates a new recipe."""

    def __init__(self):
        super(RecipeWriter, self).__init__()

    def capitalize(self, input):
        """Utility function for capitalizing the first letter in a string."""
        input_parts = list(input)
        input_parts[0] = input_parts[0].upper()
        return "".join(input_parts)

    def remove_letters(self, input):
        """Utility function for removing all letters from a string."""
        new = ""
        for letter in input:
            if not(letter.isalpha()):
                new += letter
        return new

    def normalize_grain_name(self, grain_name):
        """Tries to cleanup the various names that people use for the same grain."""
        pattern = re.compile("Caramel.*/.*Crystal", re.IGNORECASE)
        grain_name = pattern.sub("Crystal", grain_name)

        pattern = re.compile("American 2-row", re.IGNORECASE)
        grain_name = pattern.sub("Pale 2-Row", grain_name)

        pattern = re.compile("Pale Ale 2-Row", re.IGNORECASE)
        grain_name = pattern.sub("Pale 2-Row", grain_name)

        pattern = re.compile("2-row", re.IGNORECASE)
        grain_name = pattern.sub("2-Row", grain_name)

        pattern = re.compile("Barley, Flaked", re.IGNORECASE)
        grain_name = pattern.sub("Flaked Barley", grain_name)

        pattern = re.compile("Oats, Flaked", re.IGNORECASE)
        grain_name = pattern.sub("Flaked Oats", grain_name)

        pattern = re.compile("Crystal.*-", re.IGNORECASE)
        grain_name = pattern.sub("Crystal", grain_name)

        pattern = re.compile("Caramel", re.IGNORECASE)
        grain_name = pattern.sub("Crystal", grain_name)

        pattern = re.compile("Cara-Pils/Dextrine", re.IGNORECASE)
        grain_name = pattern.sub("Carapils", grain_name)

        pattern = re.compile("Cara-Pils", re.IGNORECASE)
        grain_name = pattern.sub("Carapils", grain_name)

        norm_name = ""
        parts = grain_name.split(' ')
        for part in parts:

            part_lower = part.lower()
            if len(part_lower) == 0:
                continue
            if part_lower[0] in ['(', '[']:
                break

            # The world 'malt' is redundant so ignore it.
            if part_lower != 'malt':

                # Make sure the first letter is capitalized.
                part = self.capitalize(part)
                norm_name += part
                norm_name += " "

        norm_name = norm_name.strip()
        if norm_name == "Pale":
            norm_name = "Pale 2-Row"
        return norm_name

    def to_number(self, num_str):
        """Utility method for string to number conversion and cleanup."""
        new_str = self.remove_letters(num_str)
        if new_str == "1--1/2": # Filty hack to handle an annoying case
            return float(1.5)
        fraction_parts = new_str.split('/')
        if len(fraction_parts) == 1:
            return float(new_str)
        return float(fraction_parts[0]) / float(fraction_parts[1])

    def normalize_amount_str(self, amount, scale):
        """Tries to cleanup the various ways people express amounts."""
        parts = amount.split(' ')
        if len(parts) < 2: # Sanity check
            return amount

        if any([SEARCH_LIST_FUNC(amount.lower(), i) for i in ['lb', 'pound']]):
            parts[0] = str(self.to_number(parts[0]) * scale)
            parts[1] = "lbs"
        if any([SEARCH_LIST_FUNC(amount.lower(), i) for i in ['kg', 'kilogram']]):
            parts[0] = str(self.to_number(parts[0]) * scale * 2.2)
            parts[1] = "lbs"
        if any([SEARCH_LIST_FUNC(amount.lower(), i) for i in ['oz', 'ounce']]):
            parts[0] = str(self.to_number(parts[0]) * scale * 0.0625)
            parts[1] = "lbs"
        if any([SEARCH_LIST_FUNC(amount.lower(), i) for i in ['gal', 'gallon', 'us gallon']]):
            parts[0] = str(self.to_number(parts[0]) * scale)
            parts[1] = "gallons"
        if any([SEARCH_LIST_FUNC(amount.lower(), i) for i in ['liter', 'litre']]):
            parts[0] = str(self.to_number(parts[0]) * scale * 0.264172)
            parts[1] = "gallons"

        amount = parts[0] + " " + parts[1]
        return amount

    def normalize_grains_and_hops(self, grains, hops, scale):
        """Since the recipes were collected from multiple sites, this attempts to normalize their structure."""
        """Some recipe writers put the grains and the hops together, so we have to deal with that."""
        if grains is None:
            return grains, hops

        new_grains = []
        new_hops = []

        ignore_strs = ['[', '#', 'dme', 'extract', 'gypsum', 'honey', 'moss', 'sugar', 'syrup', 'total', 'water', 'whirlfloc', 'yeast']

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
                    matched_ignore_strs = [SEARCH_LIST_FUNC(grain[FERMENTABLES_KEY].lower(), i) for i in ignore_strs]
                    if any(matched_ignore_strs):
                        continue

                    # Normalize the amount.
                    amount = self.normalize_amount_str(amount, scale)
                    grain[AMOUNT_KEY] = amount

                    # Normalize the grain name.
                    norm_name = self.normalize_grain_name(grain[FERMENTABLES_KEY])
                    if len(norm_name) > 1:
                        grain[FERMENTABLES_KEY] = norm_name
                        new_grains.append(grain)

            else:
                # Does the string contain junk?
                matched_ignore_strs = [SEARCH_LIST_FUNC(grain.lower(), i) for i in ignore_strs]
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
                matched_units = [SEARCH_LIST_FUNC(parts[0].lower(), i) for i in UNITS]
                if any(matched_units):
                    amount += " "
                    amount += parts[0]
                    amount = self.normalize_amount_str(amount, scale)
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

                # Cleanup whatever we extracted for name of the grain.
                desc = self.normalize_grain_name(desc)

                # Did we find grains?
                if is_grain and len(desc) > 0:
                    grain = {}
                    grain[FERMENTABLES_KEY] = desc
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

    def compute_avg_amount(self, grains, grain_name):
        """Looks through the (normalized) grains list for the specified grain and compute the average amount used."""
        avg_amount = 0.0
        count = 0.0
        for grain in grains:
            if grain[FERMENTABLES_KEY] == grain_name:
                if AMOUNT_KEY in grain:
                    amount_str_parts = grain[AMOUNT_KEY].split(' ')
                    temp_amount = float(amount_str_parts[0])
                    avg_amount = avg_amount + temp_amount
                    count = count + 1.0
        return avg_amount / count

    def generate_avg_recipe(self, db, style, desired_yield):
        """Looks through the database of crawled web pages, gets all beer recipes of the given style, normalizes the amounts"""
        """and writes a recipe using the most popular grains and hops and the avg amount in which they appear."""
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
                yield_size = None
                scale = None # Amount to scale the recipe by; will try to nomalize on a 3 gallon yield

                if GRAINS_KEY in page:
                    grain_value = page[GRAINS_KEY]
                if HOPS_KEY in page:
                    hops_value = page[HOPS_KEY]
                if YIELD_SIZE_KEY in page:
                    yield_size = self.normalize_amount_str(page[YIELD_SIZE_KEY], 1.0)
                    scale = desired_yield / float(yield_size.split(' ')[0]) 

                norm_grains, norm_hops = self.normalize_grains_and_hops(grain_value, hops_value, scale)

                grains.extend(norm_grains)
                hops.extend(norm_hops)
                yeasts.extend(page[YEASTS_KEY])

        #
        # Print the normalized inputs.
        #

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

        #
        # Do we have enough to write the recipe?
        #

        if len(counted_fermentables) < 3:
            print("ERROR: Not enough data to write a recipe.")
        if len(counted_hop_names) < 3:
            print("ERROR: Not enough data to write a recipe.")
        if len(counted_yeasts) < 1:
            print("ERROR: Not enough data to write a recipe.")

        #
        # Write the recipe
        #

        print("------")
        print("Recipe")
        print("------")

        # Grains
        grain_name = counted_fermentables[0][0]
        grain_amount = self.compute_avg_amount(grains, grain_name)
        print(grain_name + ", {:.2f}".format(grain_amount) + " lbs")
        grain_name = counted_fermentables[1][0]
        grain_amount = self.compute_avg_amount(grains, grain_name)
        print(grain_name + ", {:.2f}".format(grain_amount) + " lbs")
        grain_name = counted_fermentables[2][0]
        grain_amount = self.compute_avg_amount(grains, grain_name)
        print(grain_name + ", {:.2f}".format(grain_amount) + " lbs")
        grain_name = counted_fermentables[3][0]
        grain_amount = self.compute_avg_amount(grains, grain_name)
        print(grain_name + ", {:.2f}".format(grain_amount) + " lbs")

        # Hops
        print(counted_hop_names[0][0] + " Hops")
        print(counted_hop_names[1][0] + " Hops")
        print(counted_hop_names[2][0] + " Hops")

        # Yeast
        print(counted_yeasts[0][0])

    def export_to_json(self, db):
        """Exports the beer recipes to JSON."""
        all_data = []
        all_pages = db.retrieve_all_pages()
        for page in all_pages:

            if GRAINS_KEY in page:
                grain_value = page[GRAINS_KEY]
            else: # Filter out pages that aren't recipes
                continue

            if HOPS_KEY in page:
                hops_value = page[HOPS_KEY]
            else:
                hops_value = None

            page[GRAINS_KEY], page[HOPS_KEY] = self.normalize_grains_and_hops(grain_value, hops_value, 1.0)

            # This isn't serializable so get rid of it.
            if ID_KEY in page:
                del page[ID_KEY]

            all_data.append(page)
        
        return json.dumps(all_data)

    def list_styles(self, db):
        all_styles = set()
        all_pages = db.retrieve_all_pages()

        for page in all_pages:
            if STYLE_KEY in page:
                all_styles.add(page[STYLE_KEY])

        return all_styles

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
        writer.generate_avg_recipe(db, args.style, 3.0)

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
