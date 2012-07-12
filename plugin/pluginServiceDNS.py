import plugin
import dnsServer

class pluginServiceDNS(plugin.PluginThread):
	name = 'dns'
	options = {
		'start':	['launch at startup', 1],
		'host':		['listen on ip', '127.0.0.1'],
		'port':		['listen on port', 53],
		'resolver':	['forward standard requests to', '8.8.8.8,8.8.4.4']
	}
	srv = None

	def pStart(self):
		if self.srv is None:
			self.srv = dnsServer.DnsServer()
			self.srv.start(self.app)
		return True
	
	def pStop(self):
		if self.srv is not None:
			self.srv.stop()
		print "Plugin %s stopped" %(self.name)
		return True

