# from __future__ import unicode_literals
import scrapy

import json

import os

import scrapy

from scrapy.spiders import Spider

from scrapy.http import FormRequest

from scrapy.http import Request

from chainxy.items import ChainItem

from scrapy import signals

from scrapy.xlib.pydispatch import dispatcher

from selenium import webdriver

from lxml import etree

from lxml import html

import random

import pdb

import usaddress


class avvo_all(scrapy.Spider):

	name = 'avvo_all'

	domain = 'https://www.avvo.com'

	history = []

	output = []

	headers = {
		"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
		"accept-encoding": "gzip, deflate, br",
		"upgrade-insecure-requests": "1",
		"cookie": "_persistent_session_id=BAh7BkkiD3Nlc3Npb25faWQGOgZFVEkiKTU5YWExZTMyLTNiN2ItNGNlMy1h%0AMWMzLTI2MDBlNzZkMmJkZQY7AFQ%3D%0A; ibeugdpr=NOTINEU:1538849072; pxvid=7ab64f00-cb15-11e8-8eb6-df92c2817ad6; _pxvid=7ab64f00-cb15-11e8-8eb6-df92c2817ad6; _profile_persistent_session_id=BAh7BkkiD3Nlc3Npb25faWQGOgZFVEkiKTY3MTE3MGMxLTFlNDUtNGE1NC05%0AMzkxLTI2MjE1ZDVlNTkxOQY7AFQ%3D%0A--606a9a83562f36d14ee91363f1cf11081721af5c; avvo-login=BAh7BkkiD3Nlc3Npb25faWQGOgZFVEkiKTNlZDlmN2QxLTAyOGMtNDM2ZC05%0AZDc2LTFmYThkYTdkY2NiOQY7AFQ%3D%0A--efacab1e099f91e22997646a35d4803229207ebe; _session_id=acde2dcb3b195947466a8ede6438c9cf; serp_search_prev_sig=99914b932bd37a50b983c5e7c90ae93b; serp_search_sig=25bcb490f7e93c9a3255c509fbf530d499914b932bd37a50b983c5e7c90ae93b; maxLength=925; aa_session_count=1; aa_persistent_session_id=59aa1e32-3b7b-4ce3-a1c3-2600e76d2bde; aa_session_id=59aa1e32-3b7b-4ce3-a1c3-2600e76d2bde.1",
		"if-none-match": 'W/"95e44b7577988b56cb5880f812b188b4"',
		"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36"
	}


	def __init__(self):

		script_dir = os.path.dirname(__file__)

		file_path = script_dir + '/proxies.txt'

		with open(file_path, 'rb') as text:

			self.proxy_list =  [ "http://" + x.strip() for x in text.readlines()]

	
	def start_requests(self):

		url = "https://www.avvo.com/find-a-lawyer/all-practice-areas"

		yield scrapy.Request(url, 
					callback=self.parse_category, 
					headers=self.headers,
					meta={
						'proxy' : random.choice(self.proxy_list),
					}
				)

	def parse_category(self, response):

		category_list = response.xpath('//div[@id="areas-of-law"]//div[@class="v-content-wrapper"]//a/@href').extract()

		for category in category_list[110: 132]:

			url = self.domain + category

			yield scrapy.Request(url, callback=self.parse_state, 
					headers = self.headers,
					meta={
						'proxy' : random.choice(self.proxy_list),
					})


	def parse_state(self, response):

		state_list = response.xpath('//div[@id="js-top-state-link-farm"]//li[@class="u-margin-bottom-half"]//a/@href').extract()

		for state in state_list:

			state = self.domain + state

			yield scrapy.Request(state, callback=self.parse_list, 
					headers=self.headers,
					meta={
						'proxy' : random.choice(self.proxy_list),
					})


	def parse_list(self, response):

		link_list = response.xpath('//a[@class="v-serp-block-link"]')

		for link in link_list:

			item = ChainItem()

			item['Full_Name'] = self.validate(''.join(link.xpath('.//text()').extract()))

			link = self.domain + link.xpath('./@href').extract_first()

			yield scrapy.Request(link, headers=self.headers, callback=self.parse_profile, meta={ 'item' : item, 'proxy' : random.choice(self.proxy_list) })

		next_link = response.xpath('//li[@class="pagination-next"]//a/@href').extract_first()

		if next_link != None:

			next_link = self.domain + next_link

			yield scrapy.Request(next_link, callback=self.parse_list,
					headers=self.headers,
					meta={
						'proxy' : random.choice(self.proxy_list),
					})


	def parse_profile(self, response):

		item =response.meta['item']

		check = self.validate(''.join(response.xpath('//div[contains(@class, "downgraded-card-title")]//text()').extract()))

		if check == '':

			item['Avatar'] = 'https:' + response.xpath('//div[contains(@class, "v-lawyer-card-wrapper")]//img/@src').extract_first()

			item['Review'] = response.xpath('//span[@itemprop="reviewCount"]/@content').extract_first()

			item['Rating'] = response.xpath('//span[@itemprop="ratingValue"]/@content').extract_first()

			item['Free_or_Advertiser'] = 'Advertiser'

			practice_list = self.eliminate_space(response.xpath('//ol[contains(@class, "v-chart-legend-list")]//li//a//text()').extract())

			item['Practice_Areas'] = ', '.join([ practice.split(':')[0] for practice in practice_list ])

			item['About_Summary'] = self.validate(''.join(response.xpath('//section[@id="about"]//p[contains(@class, "js-specialty-display-container")]//text()').extract()))

			item['About_Description'] = self.validate(''.join(response.xpath('//section[@id="about"]//div[@id="js-truncated-aboutme"]//text()').extract()))

			raw_address = self.validate(' '.join(response.xpath('//address[contains(@class, "js-context js-address js-v-address")]')[0].xpath('.//p//text()').extract()))

			contact_list = response.xpath('//address[contains(@class, "js-context js-address js-v-address")]')[0].xpath('.//div')

			for contact in contact_list:

				detail = contact.xpath('.//span[@class="text-muted"]//text()').extract_first()

				if 'office' in detail.lower():

					item['Office_Phone'] = self.validate(''.join(contact.xpath('.//span[@class="js-v-phone-replace-text"]//text()').extract()))

					item['Mobile_Number'] = self.validate(''.join(contact.xpath('.//span[@class="js-v-phone-replace-text"]//text()').extract()))

				if 'fax' in detail.lower():

					item['Office_Fax'] = self.validate(''.join(contact.xpath('.//span[@class="js-v-phone-replace-text"]//text()').extract()))
					
			item['Website_Address'] =  response.xpath('//div[@class="text-truncate"]//a//text()').extract_first()

			item['Email'] = ''

		else:

			item['Avatar'] = 'https:' + response.xpath('//div[contains(@class, "downgraded-card-body")]//img/@src').extract_first()

			try:
				item['Review'] = self.validate(response.xpath('//section[@id="client_reviews"]//span[@class="text-muted"]//text()').extract_first().replace('(', '').replace(')',''))
			except:
				pass

			item['Rating'] = response.xpath('//div[contains(@class, "downgraded-card-body")]//span[@class="avvo-rating-modal-info"]/@data-rating').extract_first()

			item['Free_or_Advertiser'] = 'Free'	

			item['Practice_Areas'] = self.validate(''.join(response.xpath('//div[@id="practice-areas"]//p//text()').extract()))

			item['About_Description'] = self.validate(''.join(response.xpath('//section[@id="about"]//div[@id="js-truncated-aboutme"]//text()').extract()))

			raw_address = self.validate(' '.join(response.xpath('//address[contains(@class, "js-context js-address js-v-address")]')[0].xpath('.//text()').extract()))

		addr_list = usaddress.parse(raw_address)

		address_1 = ''

		address_2 = '' 

		city = ''

		for addr in addr_list:

			if addr[1] == 'PlaceName':
				city += addr[0]	+ ' '

			elif addr[1] == 'StateName':
				item['State'] = addr[0]

			elif addr[1] == 'ZipCode':
				item['Zip_Code'] = addr[0]

			elif 'Occupancy' in addr[1]:
				address_2 += addr[0] + ' '

			else:
				address_1 += addr[0] + ' '

		item['City'] = self.validate(city)

		item['Address_Street_Line_1'] = self.validate(address_1)

		item['Address_Street_Line_2'] = self.validate(address_2)

		license_list = response.xpath('//table[contains(@class, "table-responsive-flip")]//tr')	

		license_dump = ''

		for idx, license in enumerate(license_list[1:]):

			license_dump += ' , '.join(license.xpath('.//text()').extract()) + ' | '

		item['License'] = self.validate(license_dump[:-2])

		data_list = response.xpath('//div[contains(@class, "v-resume-table-wrapper")]')

		for data in data_list:

			category = data.xpath('.//strong/text()').extract_first()

			sub_data_dump = ''

			sub_data_list = data.xpath('.//table//tr')	

			for idx, sub_data in enumerate(sub_data_list[1:]):

				sub_data_dump += ' : '.join(sub_data.xpath('.//text()').extract()) + ' | '

			sub_data_dump = self.validate(sub_data_dump[:-2])	

			try:		

				item[category.replace(' ', '_').title()] = sub_data_dump

			except:

				pass

		item['Link'] = response.url

		yield item

		# yield scrapy.Request(item['Avatar'], callback=self.download_image)


	def download_image(self, response):

		file_name = 'images/'+response.url.split('/')[-1]

		with open(file_name, 'wb') as f:
			f.write(response.body)


	def validate(self, item):

		try:

			return item.encode('ascii','ignore').replace('\n', '').replace('\t','').replace('\r', '').strip()

		except:

			pass


	def eliminate_space(self, items):

	    tmp = []

	    for item in items:

	        if self.validate(item) != '':

	            tmp.append(self.validate(item))

	    return tmp