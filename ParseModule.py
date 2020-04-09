# -*- coding: utf-8 -*-
# 
# # MIT License
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

import bs4

class ParseModule(object):
    """Base class for describing a parse module."""

    def __init__(self):
        super(ParseModule, self).__init__()

    def find_html_tag(self, soup):
        for child_item in list(soup.children):
            if type(child_item) == bs4.element.Tag:
                return child_item
        return None

    def find_body_tag(self, html_tag):
        return html_tag.find('body')

    def is_interesting_url(self, url):
        """Returns TRUE if this URL is something this class can parse. Returns FALSE otherwise."""
        """To be overridden in the child class."""
        return False

    def make_cookies(self, url):
        """Builds the cookies dictionary that will be passed with the HTTP GET requests."""
        """To be overridden in the child class."""
        return False

    def parse(self, url, soup):
        """Parses the contents downloaded from the URL, extracts the recipe, and stores it in the database."""
        """To be overridden in the child class."""
        return False
