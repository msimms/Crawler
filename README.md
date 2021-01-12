# Crawler
A modular, extensible, but otherwise fairly simple, web crawler. The basic idea behind this project is to develop a generic web crawler that that has the optional capability of running user-specified modules to parse the data as it is crawled.

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

## Results

Have a MongoDB installation handy as results are stored in MongoDB.

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
    [--crawl-other-websites]
    [--verbose]
```

Seeding the crawler is done with either the `--file` or `--url` parameter.

## Extending

As this is a modular web crawler, it supports modules for dealing with specific websites. This is done by subclassing the `ParseModule` class and then passing the name of that class to the crawler using the `website-modules` option. Multiple modules can be supported by separating each module in the list with a comma. Data returned by a module is stored in the database, along with the raw page source.

## Examples

```
python Crawler.py --url https://foo.com --website-modules foo.py --verbose --min-revisit-secs 86400
```
The above example will crawl links from foo.com, parsing the results using the foo.py module, while printing verbose output. Pages will not be revisited unless it has been more than one day since the last visit.

```
python Crawler.py --url https://foo.com --website-modules foo.py --verbose --crawl-other-websites --min-revisit-secs 86400
```
The above example will crawl links from foo.com as well as any page linked to from foo.com. Otherwise, it is the same as the previous example.

## License
This library is released under the MIT license, see LICENSE for details.
