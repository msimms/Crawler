# Crawler
A modular, extensible, but otherwise fairly simple, web crawler. The basic idea behind this project is to develop a generic web crawler that allows the user to write plugins for scraping site-specific information.  

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
    [--min-revisit-secs <minimum number of seconds before allowing a URL to be revisited>\
    [--website-modules <command separated list of the Python modules that will parse each page>]
    [--mongodb-addr <URL of the mongodb instance which will store the result, defaults to localhost:27017>]
    [--verbose <true|false>]
```

## Examples

```
python Crawler.py --url https://foo.com --website-modules foo.py --verbose --min-revisit-secs 86400
```

## Extending

As this is a modular web crawler, it supports modules for dealing with specific websites. This is done by subclassing the `ParseModule` class and then passing the name of that class to the crawler using the `website-modules` option. Multiple modules can be supported by separating each module in the list with a comma.

## License
This library is released under the MIT license, see LICENSE for details.
