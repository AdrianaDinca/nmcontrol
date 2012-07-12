import plugin
import rpcClient
import socket, json, threading, StringIO, sys, time

class pluginRpc(plugin.PluginThread):
	name = 'rpc'
	options = {
		'start':	['Launch at startup', 1],
		'host':		['Listen on ip', '127.0.0.1', '<ip>'],
		'port':		['Listen on port', 9000, '<port>'],
	}

	def pStatus(self):
		if self.running:
			return "Plugin " + self.name + " running"

	def pStart(self):
		self.threads = []
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
		 	self.s.bind((self.conf['host'], int(self.conf['port'])))
			self.s.listen(1)
			while self.running:
				try:
					c = rpcClientThread(self.s.accept(), self.app)
					c.start()
					self.threads.append(c)
				except Exception as e:
					if self.app['debug']: print "except:", e

		except:
			print "nmc-manager: unable to listen on port"

		# close all threads
		time.sleep(1)
		if self.app['debug']: print "RPC stop listening"
		self.s.close()
		for c in self.threads:
			c.join()
		self.app['plugins']['main'].stop()

	def pStop(self):
		if self.app['debug']: print "Plugin stop :", self.name
		self.pSend(['exit'])
		print "Plugin %s stopped" %(self.name)

	def pSend(self, args):
		if self.app['debug']: print "RPC - sending cmd :", args
		r = rpcClient.rpcClient(self.conf['host'], int(self.conf['port']))
		error, data = r.sendJson(args)
		return error, data


		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			s.connect((self.conf['host'], int(self.conf['port'])))
			s.sendall(json.dumps(args))
			data = s.recv(4096)
			s.close()
			if self.app['debug']: print 'RPC - received data : ', repr(data)
			data = json.loads(data)
			if self.app['debug'] and 'result' in data and 'prints' in data['result']:
				print data['result']['prints']

			if data['error'] is None:
				return data['result']['reply']
			else:
				return "ERROR: " + data['result']

		except Exception, e:
			print "ERROR: unable to send request. Is program started ?"
			print e
			s.close()
			return False


class rpcClientThread(threading.Thread):
	def __init__(self, (client, address), app):
		self.client = client
		self.client.settimeout(10)
		self.address = address
		self.size = 4096
		self.app = app
		threading.Thread.__init__(self)

	def run(self):
		buff = ""
		start = time.time()
		while True:
			try:
				data = self.client.recv(self.size)
			except socket.timeout as e:
				break
			self.client.settimeout(time.time() - start + 1)
			if not data: break
			buff += data
			if len(data)%self.size != 0: break
		(error, result) = self.computeJsonData(buff)

		self.client.send('{"result":'+json.dumps(result)+',"error":'+json.dumps(error)+',"id":1}')
		self.client.close()

	def computeJsonData(self, data):
		if not data:
			return (True, 'no data')

		#print "computeJsonData:", data
		data = json.loads(data)
		
		if data['method'] == 'exit' or 'exit' in data['params']:
			return (True, 'exit')

		return self.computeData([data['method'], data['params']])

	def computeData(self, args):
		#if self.app['debug']: print "Received data :", data

		# check for default plugin
		if len(args[1]) == 0: args = ['main', [args[0]]]

		plugin = args[0]
		params = args[1]
		#print "Plugin:", plugin
		#print "Params:", params

		if plugin not in self.app['plugins']:
			return (True, 'Plugin "' + plugin + '" not allowed')
		if not self.app['plugins'][plugin].running:
			return (True, 'Plugin "' + plugin + '" not started')

		if params[0] == 'start': params[0] = 'start2'

		# reply before closing connection
		if plugin == 'rpc' and params[0] == 'restart':
			self.client.send('{"result":'+json.dumps({'reply':True, 'prints':'Restarting rpc'})+',"error":'+json.dumps(None)+',"id":1}');

		if params[0][0] == '_':
			if self.app['debug']: print "RPC - forbidden cmd :", args
			return (True, 'Method "' + params[0] + '" not allowed')

		if 'help' in params \
			or params[0] in self.app['plugins'][plugin].helps \
			and len(params)-1 not in range(self.app['plugins'][plugin].helps[params[0]][0], self.app['plugins'][plugin].helps[params[0]][1]+1):
			params.insert(0, 'help')

		args[1] = params
		if self.app['debug']: print "RPC - executing cmd :", args
		exec("Cmd = self.app['plugins'][plugin]." + params[0])

		# capture stdout
		capture = StringIO.StringIO()
		#sys.stdout = capture
	
		try:
			result = Cmd(args)
		except AttributeError, e:
			return (True, 'Method "' + params[0] + '" not supported by plugin "' + plugin + '"')
		except Exception, e:
			return (True, 'Exception : ' + str(e))

		# restore stdout
		sys.stdout = sys.__stdout__
		prints = capture.getvalue()
		capture.close()

		#if result is None:
		#	result = 'No data'

		return (None, {'reply': result, 'prints': prints})

