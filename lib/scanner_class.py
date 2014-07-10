#!/usr/bin/python2.7
#coding:utf-8
import os
import sys
import re
import socket
import threading
import urllib2

from nmap_class import NmapScanner
from pluginLoader_class import PluginLoader
from mysql_class import MySQLHelper
from dummy import PLUGINDIR, BASEDIR
# ----------------------------------------------------------------------------------------------------
# 
# ----------------------------------------------------------------------------------------------------
class MutiScanner(threading.Thread):
	def __init__(self, lock, threadName,pluginheader):  
		'''@summary: 初始化对象。 	
	 	@param lock: 琐对象。 
		@param threadName: 线程名称。 
		'''
		super(MutiScanner, self).__init__(name = threadName)  #注意：一定要显式的调用父类的初始 化函数。  
		self.lock = lock
		self.threadName = threadName

		if type(pluginheader) == PluginLoader:
			self.pl = pluginheader
		else:
			print 'pl is not a pluginLoader_class.PluginLoader class'

	def run(self):  
		''''''  
		self.lock.acquire() 
		print self.threadName, 'staring'
		self.lock.release()

		self.pl.loadPlugins()
		self.pl.runPlugins()

# ----------------------------------------------------------------------------------------------------
# 
# ----------------------------------------------------------------------------------------------------
class Scanner(object):
	"""docstring for Scanner"""
	def __init__(self, url):
		super(Scanner, self).__init__()
		#url
		if url[-1] != '/':
			url += '/'
		self.url = url
		m = re.match('(http[s]?)://([^:^/]+):?([^/]*)/',url)
		if m:
			self.http_type = m.group(1)
			self.host = m.group(2)
			self.ports = m.group(3)
			self.ip = socket.gethostbyname(self.host)
			self.domain = self.host[self.host.find('.')+1:]
		else:
			print 'not a valid url',url
			sys.exit(0)
		commonports = '21,22,23,25,110,53,67,80,443,1521,1526,3306,3389,8080,8580'
		if self.ports != '':
			self.ports = commonports + ',' +ports
		else:
			self.ports = commonports

		# every plugin's input argument services
		self.services = {}
		self.services['url'] = self.url
		self.services['host'] = self.host
		self.services['ports'] = [self.ports]
		self.services['http'] = []
		
		# scan result
		self.result = {}

		# thread arguments
		self.lock = threading.Lock()  

	def getServices(self) :
		''' '''
		# services type: dict
		# services = {
		# 	url:'http://www.leesec.com/',
		# 	ip:'106.187.37.47',
		# 	port:[22,80,3306],
		# 	host: 'www.leesec.com',
		# 	cms:'wordpress',
		# 	cmsversion:'3.9.1'
		# }
		# if host is a neiboorhost
		# services ={
		# 	'host':'***.***.***'
		# 	'mainhost':'www.leesec.com',
		# 	...
		# }
		# if domain is a sondomain
		# services ={
		# 	'host':'mail.leesec.com',
		# 	'fardomain':'www.leesec.com',
		# 	...
		# }		# 
		print '>>>getting services'
		np = NmapScanner(self.host,self.ports)
		sc = np.scanPorts()
		try:
			self.services['url'] = self.url
			self.services['host'] = self.host
			self.services['ip'] = sc.keys()[0]
			self.services['ports'] = []
			self.services['detail'] = {}
			if sc[sc.keys()[0]].has_key('tcp'):
				self.services['detail'].update(sc[sc.keys()[0]]['tcp'])
				for eachport in sc[sc.keys()[0]]['tcp']:
					self.services['ports'].append(eachport)
			if sc[sc.keys()[0]].has_key('udp'):
				self.services['detail'].update(sc[sc.keys()[0]]['udp'])
				for eachport in sc[sc.keys()[0]]['udp']:
					self.services['ports'].append(eachport)
			
			# neiborhood weisites
			self.services['http'] = []

			print 'services:\t',self.services
		except KeyError,e:
			pass

	def getSubDomains(self,host=None):
		if host == None:
			host = self.host
		services={}
		services['host'] = host
		pl = PluginLoader(None,services)
		pl.runEachPlugin(PLUGINDIR+'/Info_Collect/subdomain.py')
		subdomains = pl.services['subdomains']
		return subdomains

	def getNeiboorHosts(self,ip=None):
		if ip == None:
			ip = self.ip
		services={}
		services['ip'] = ip
		pl = PluginLoader(None,services)
		pl.runEachPlugin(PLUGINDIR+'/Info_Collect/neighborhost.py')
		neighborhosts = pl.services['neighborhosts']
		return neighborhosts

	def getHttpPorts(self,ip=None):
		if ip == None:
			ip = self.ip
		services={}
		services['ip'] = ip
		# get all opened ports
		pl = PluginLoader(None,services)
		pl.runEachPlugin(PLUGINDIR+'/Info_Collect/portscan.py')
		ports = {}
		if pl.services.has_key('detail'):
			ports = pl.services['detail']

		# get http ports
		httpports = []
		for eachport in ports.keys():
			if ports[eachport]['name'] == 'http':
				httpports.append(eachport)
		print 'httpports:\t',httpports
		return httpports

	def generateUrl(self,ip=None,hosts=None,ports=None):
		''''''
		# url redict  hasn't been considered
		urls = []
		if hosts == None:
			pass
		else:
			for eachhost in hosts:
				url = 'http://' + eachhost
				try:
					urllib2.urlopen(url)
					urls.append(url)
					continue
				except urllib2.URLError,e:
					print 'urllib2.URLError',e,url
				except urllib2.HTTPError,e:
					print 'urllib2.HTTPError',e,url
				except urllib2.socket.timeout,e:
					print 'urllib2.socket.timeout',e,url
				except urllib2.socket.error,e:
					print 'urllib2.socket.error',e,url

				url = 'https://' + eachhost
				try:
					urllib2.urlopen(url)
					urls.append(url)
				except urllib2.URLError,e:
					print 'urllib2.URLError',e,url
				except urllib2.HTTPError,e:
					print 'urllib2.HTTPError',e,url
				except urllib2.socket.timeout,e:
					print 'urllib2.socket.timeout',e,url
				except urllib2.socket.error,e:
					print 'urllib2.socket.error',e,url

		if ip == None or ports == None:
			pass
		else:
			for eachport in ports:
				url = 'http://' + ip + ':' + str(eachport)
				try:
					urllib2.urlopen(url)
					urls.append(url)
					continue
				except urllib2.URLError,e:
					print 'urllib2.URLError',e,url
				except urllib2.HTTPError,e:
					print 'urllib2.HTTPError',e,url
				except urllib2.socket.timeout,e:
					print 'urllib2.socket.timeout',e,url
				except urllib2.socket.error,e:
					print 'urllib2.socket.error',e,url

				url = 'https://' + ip + ':' + str(eachport)
				try:
					urllib2.urlopen(url)
					urls.append(url)
				except urllib2.URLError,e:
					print 'urllib2.URLError',e,url
				except urllib2.HTTPError,e:
					print 'urllib2.HTTPError',e,url
				except urllib2.socket.timeout,e:
					print 'urllib2.socket.timeout',e,url
				except urllib2.socket.error,e:
					print 'urllib2.socket.error',e,url

		return urls

	def startScan(self,services=None):
		''' '''
		print '>>>starting scan'
		# get subdomains
		print '>>>collecting subdomain info'
		subdomains = self.getSubDomains(self.host)
		print 'subdomains:\t',subdomains
		
		# get hosts
		hosts={}
		print '>>>for each subdomain, collecting neiborhood host info'
		for eachdomain in subdomains:
			tmp={}
			tmpip = socket.gethostbyname(eachdomain)
			if tmpip not in hosts.keys():
				tmphosts = self.getNeiboorHosts(tmpip)
				hosts[tmpip] = tmphosts
				if eachdomain not in tmphosts:
					hosts[tmpip].append(eachdomain)
				
			else:
				if eachdomain not in hosts[tmpip]:
					hosts[tmpip].append(eachdomain)

		print 'hosts:\t',hosts

		# get urls
		urls = {}
		for eachip in hosts.keys():
			ip_hosts = hosts[eachip]
			httpports = self.getHttpPorts(eachip)
			urls[eachip] = self.generateUrl(eachip,ip_hosts,httpports)

		print 'urls\t',urls
		# get services

		print '>>>starting scan each host'
		
		pls = []
		# ip type scan
		for eachip in urls.keys():
			services = {}
			if eachip !=  self.ip:
				services['issubdomain'] = True
			services['ip'] = eachip
			pl = PluginLoader(None,services)
			pls.append(pl)
			print 'scan start:\t',pl.services

		# http type scan
		for eachip in urls.keys():
			for eachurl in urls[eachip]:
				services = {}
				# not subdomain
				if self.domain not in eachurl:
					services['isneighborhost'] = True
				
				services['url'] = eachurl

				pl = PluginLoader(None,services)
				pls.append(pl)
				print 'scan start:\t',pl.services

		#print pls
		mthpls=[]
		for eachpl in pls:
			#print eachpl.services
			if eachpl.services.has_key('ip'):
				threadName = eachpl.services['ip']
			elif eachpl.services.has_key('url'):
				threadName = eachpl.services['url']
			else:
				threadName = 'Unknow'
				print 'An unknow scanner services found:\t',eachpl.services
				sys.exit(0)

			mthpl = MutiScanner(self.lock,threadName,eachpl)
			mthpls.append(mthpl)

		for eachmthpl in mthpls:
			eachmthpl.start()

		for eachmthpl in mthpls:
			eachmthpl.join()

		for eachpl in pls:
			if eachpl.services.has_key('ip'):
				threadName = eachpl.services['ip']
			elif eachpl.services.has_key('url'):
				threadName = eachpl.services['url']
		 	self.result[threadName] = eachpl.retinfo
		 	print '>>>>>>scan:\t',threadName,'\t<<<<<<'
		 	print '>>>scan output:'
		 	print eachpl.output
		 	print '>>>scan services:'
		 	print eachpl.services
		 	print '>>>scan result:'
		 	print eachpl.retinfo

	def saveResult(self, sqlcur):
		''' '''
		print '>>>saving scan result'
		sqlcmd = 'INSERT INTO '

# ----------------------------------------------------------------------------------------------------
# 
# ----------------------------------------------------------------------------------------------------
if __name__=='__main__':
	sn =Scanner('http://www.leesec.com/')
	sn.startScan()
	print ">>>scan result:"
	#print sn.result