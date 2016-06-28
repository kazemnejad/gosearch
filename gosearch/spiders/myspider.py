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

        yield {
            "url": response.url,
            "article": article
        }
class StackSpider(scrapy.Spider):
    name = "stack"
    start_urls = ["http://stackoverflow.com/questions/tagged/python"]
    allowed_domains = ["stackoverflow.com"]
    def parse(self, response):
        questionlink = response.xpath('//a[@class="question-hyperlink"]/@href').extract()

        if len(questionlink) == 0:
            return
        for i in questionlink:
            question_url="http://stackoverflow.com"+i
            yield scrapy.Request(question_url,callback=self.extractquestion)
        if  ("page" in response.url):
            page_url,page_num=response.url.split("?page=")
            page_url+="?page="+str(int(page_num)+1)

            yield scrapy.Request(page_url,callback=self.parse)
        else:
            yield scrapy.Request(response.url+"?page=2",callback=self.parse)

    def extractquestion(self,response):
        article = Goose().extract(raw_html=response.body)
        yield {
            "url": response.url,
            "article": article
        }

class tutorialspointSpider(scrapy.Spider):
    name = "tutorialspoint"
    start_urls = ["http://www.tutorialspoint.com/python/index.htm"]
    allowed_domains = ["tutorialspoint.com"]
    def parse(self, response):
        url = response.xpath('//a/@href').extract()

        for i in url:
            if "python" in i:
                yield scrapy.Request("http://www.tutorialspoint.com"+i,callback=self.parse)

        article=Goose().extract(raw_html=response.body)
        yield{
             "url": response.url,
             "article": article
        }