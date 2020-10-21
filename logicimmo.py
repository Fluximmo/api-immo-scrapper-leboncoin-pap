from __future__ import unicode_literals
# -*- coding: utf-8 -*-
from scrapy.http.request import Request
from location.models import Offer, Source, OfferCategory
from datetime import datetime
from location.spiders.offer_spider import offerSpider
import re

class LogicimmoSpider(offerSpider):
    name = "logicimmo"
    start_urls = ['http://www.logic-immo.com/location-immobilier-paris-75,100_1/options/groupprptypesids=1,2,6,7,12,15']


    offer_category_id = OfferCategory.objects.filter(name='location')[0].id
    source_id = Source.objects.filter(name="logicimmo")[0].id

    def parse_next_page(self, response):
        try:
            for elmt in response.xpath('.//div[@itemscope=""][@itemtype="http://schema.org/ApartmentComplex"]'):
                html_id = elmt.xpath('.//div[@id]/@id').extract()[0]
                check_offer = Offer.objects.filter(html_id=html_id).distinct()
                if Offer.objects.filter(html_id=html_id).count() == 0:
                    offer = Offer()
                    offer.first_crawl_date = datetime.now()
                else:
                    offer = check_offer[0]

                offer.html_id = html_id
                offer.source_id = self.source_id
                offer.offer_category_id = self.offer_category_id
                offer.url = elmt.xpath('.//a[@class="offer-link"]/@href').extract()[0]
                # offer.title = elmt.xpath('.//section[@class="item_infos"]/h3/text()').extract()[0].strip()
                try:
                    offer.price = elmt.xpath('.//p[@class="offer-price"]/span/text()').extract()[0].strip()[:-2].replace(' ', '')
                except:
                    offer.price = None
                offer.address = ""
                arrdssmt = elmt.xpath('.//div[@class="offer-places-block"]/h2/span/text()').extract()
                thorough_place = elmt.xpath('.//a[@class="offer-block offer-link"]/@title').extract()
                if len(arrdssmt):
                    offer.address += arrdssmt[0]
                if len(thorough_place):
                    offer.address += thorough_place[0]
                offer.last_crawl_date = datetime.now()
                offer.save()
                yield Request(offer.url, callback=self.parse_one_annonce, meta={'offer':offer})
        except UnboundLocalError:
            print "Crawling done. Exiting..."
            exit()
        t = True

        try:
            if 'page=' in response.url:
                url = response.url.split('/')
                for i, elmt in enumerate(url):
                    if 'page' in elmt:
                        n = elmt.split('=')[1]
                        url[i] = ''
            else:
                raise
        except:
            t = False
            next_page = response.url + '/page=2'
            yield Request(next_page,
                                callback=self.parse_next_page)

        if t:
            parsed = int(n)
            next_page = '/'.join(url) + 'page=' + str(parsed + 1)

            yield Request(next_page,
                                callback=self.parse_next_page)


    def parse_one_annonce(self, response):
        offer = super(LogicimmoSpider, self).parse_one_annonce(response)
        surface = response.xpath('//span[@class="offer-area-number"]/text()').extract()
        descriptionDetaillee = response.xpath('//div[@class="offer-description-text"]').extract()
        try:
            offer.area = re.compile('(\D+)').sub('', surface[0])
        except:
            offer.area = None
        try:
            offer.description = descriptionDetaillee[0].strip()
        except:
            offer.description = "Not specified"
        offer.save()
