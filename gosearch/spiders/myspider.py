import scrapy
import re
from scrapy.http import HtmlResponse

from goose import Goose
from stemming.porter2 import stem
from collections import Counter


class PythonSpider(scrapy.Spider):
    name = "python"
    start_urls = ["https://docs.python.org/3/"]
    allowed_domains = ["docs.python.org"]

    def parse(self, response, pr=None):
        for i in response.xpath('//a/@href').extract():
            if 'https://' in i or 'http://' in i:
                continue
            c = 0
            if re.match(r'(.*)\/(.*\.html)', response.url):
                c = 1
            urls = response.url.split("/")

            urls = '/'.join(urls[0:len(urls) - c - i.count("../")])
            if urls[-1] == '/':
                target = urls + i.split("../")[-1]
            else:
                target = urls + '/' + i.split("../")[-1]
            # print "target:", target
            if target == pr:
                continue
            yield scrapy.Request(target, callback=lambda res: self.parse(res, response.url))

        article = Goose().extract(raw_html=response.body)
        if response.url == 'https://docs.python.org/3/_sources/library/random.txt':
            print article
            input()
        yield {
            "url": response.url,
            "article": article
        }
