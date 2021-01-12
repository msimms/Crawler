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
"""Database implementation"""

import sys
import traceback
import uuid
from bson.objectid import ObjectId
import pymongo
import Database
import Keys

class MongoDatabase(Database.Database):

    def __init__(self):
        Database.Database.__init__(self)

    def connect(self, db_addr):
        """Connects/creates the database"""
        try:
            self.conn = pymongo.MongoClient(db_addr)
            self.database = self.conn['crawlerdb']
            self.pages_collection = self.database['pages']
            return True
        except pymongo.errors.ConnectionFailure as e:
            self.log_error("Could not connect to MongoDB: %s" % e)
        return False

    def create_page(self, url, last_visit_time, raw_content, extracted_content):
        """Create method for a webpage."""
        try:
            post = { Keys.URL_KEY: url, Keys.LAST_VISIT_TIME_KEY: last_visit_time, Keys.PAGE_SOURCE_KEY: raw_content }
            if extracted_content is not None:
                post.update(extracted_content)
            self.pages_collection.insert(post)
            return True
        except:
            self.log_error(traceback.format_exc())
            self.log_error(sys.exc_info()[0])
        return False

    def retrieve_page(self, url):
        """Retrieve method for a webpage."""
        try:
            return self.pages_collection.find_one({Keys.URL_KEY: url})
        except:
            self.log_error(traceback.format_exc())
            self.log_error(sys.exc_info()[0])
        return None

    def retrieve_all_pages(self):
        """Retrieve method for a webpage."""
        try:
            return self.pages_collection.find()
        except:
            self.log_error(traceback.format_exc())
            self.log_error(sys.exc_info()[0])
        return None

    def update_page(self, url, last_visit_time, raw_content, extracted_content):
        """Update method for a webpage."""
        try:
            post = self.pages_collection.find_one({Keys.URL_KEY: url})
            if post is not None:
                post[Keys.LAST_VISIT_TIME_KEY] = last_visit_time
                post[Keys.PAGE_SOURCE_KEY] = raw_content
                if extracted_content is not None:
                    post.update(extracted_content)
                self.pages_collection.save(post)
                return True
        except:
            self.log_error(traceback.format_exc())
            self.log_error(sys.exc_info()[0])
        return False
