# -*- coding: utf-8 -*-
from __future__ import unicode_literals
# -*- coding: utf-8 -*-
from scrapy.http.request import Request
from location.models import Offer, Source, OfferCategory
from datetime import datetime
from location.spiders.offer_spider import offerSpider
import logging
import re
import urlparse

log = logging.getLogger(__name__)

class ExplorimmoSpider(offerSpider):
    name = "explorimmo"
    start_urls = ["http://www.explorimmo.com/resultat/annonces.html?transaction=location&location=Paris&priceMax=&type=maison%2Cvilla%2Cferme%2Cmoulin%2Cchalet&type=appartement%2Cchambre&type=atelier%2Cloft%2Cduplex&type=hotel+particulier%2C+propriete%2Cchateau%2Cmanoir&roomMin=&page=1"]

    offer_category_id = OfferCategory.objects.filter(name='location')[0].id
    source_id = Source.objects.filter(name=name)[0].id

    def parse_next_page(self, response):
        try:
            for elmt in response.xpath('.//div[@id="vue"]/div[@data-classified-id]'):
                try:
                    html_id = elmt.xpath('.//*/@data-classified-id').extract()[0]
                except:
                    log.warning("No html_id for this element. Skipping it.")
                    continue

                check_offer = Offer.objects.filter(html_id=html_id).distinct()
                if Offer.objects.filter(html_id=html_id).count() == 0:
                    offer = Offer()
                    offer.first_crawl_date = datetime.now()
                else:
                    offer = check_offer[0]
                offer.html_id = html_id
                offer.source_id = self.source_id
                offer.offer_category_id = self.offer_category_id
                offer.url = 'http://www.explorimmo.com' + elmt.xpath('.//h2[@itemprop="name"]/a[@class="js-item-title"]/@href').extract()[0]
                offer.title = elmt.xpath('.//h2[@itemprop="name"]/a[@class="js-item-title"]/text()').extract()[0].strip()
                try:
                    offer.price = elmt.xpath('.//span[@class="price-label"]/text()').extract()[0].strip().replace(u'\xa0','')[:-1]
                except:
                    offer.price = None

                arrdssmt = (' '.join(elmt.xpath('.//span[@class="localisation-label"]/strong/text()').extract())).strip()
                metro = (' '.join(elmt.xpath('.//span[@class="item-localisation"]/text()').extract())).strip()
                offer.address = arrdssmt + ' ' + metro
                offer.last_crawl_date = datetime.now()
                offer.save()
                yield Request(offer.url, callback=self.parse_one_annonce, meta={'offer':offer})
        except UnboundLocalError:
            print "Crawling done. Exiting..."
            exit()
        parse = urlparse.urlparse(response.url)
        t = True

        try:
            n = urlparse.parse_qs(parse.query)['page'][0]
        except KeyError:
            t = False
            next_page = response.url + '&page=2'
            yield Request(next_page,
                                callback=self.parse_next_page)

        if t:
            parsed = int(n)
            next_page = response.url[:-len(n)] + str(parsed + 1)

            yield Request(next_page,
                                callback=self.parse_next_page)


    def parse_one_annonce(self, response):
        offer = super(ExplorimmoSpider, self).parse_one_annonce(response)
        surface = response.xpath('//li/span[@class="name"][text()="Surface"]/following-sibling::span/text()').extract()
        descriptionDetaillee = response.xpath('//div[@itemprop="description"]/p[@class="description"]/text()').extract()
        offer.area = re.compile('(\D+)').sub('', surface[0])
        try:
            offer.description = descriptionDetaillee[0]
        except:
            log.warning("No description for this item")
            offer.description = ""
        offer.save()
