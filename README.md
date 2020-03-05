# Crawler
A modular web crawler

## Installation
To clone the source code:
```
git clone https://github.com/msimms/Crawler
```

To install the dependencies:
```
cd Crawler
python setup.py
```

## Usage
```
python Crawler.py 
    [--file <name of a file from which to harvest URLs>]
    [--url <URL from which to start crawling>]
    [--rate <crawl rate, in seconds>]
    [--max-depth <maximum crawl depth>]
    [--parse-module <name of the Python module that will parse each page>]
    [--mongodb-addr <URL of the mongodb instance which will store the result, defaults to localhost:27017>]
    [--verbose <true|false>]
```

## License
This library is released under the MIT license, see LICENSE for details.
