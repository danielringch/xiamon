import json
import http.server
import threading
from ...core import Plugin


class Messagerelay(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Messagerelay, self).__init__(config, outputs)

        self.__host = self.config.get('localhost', 'host')
        self.__port = int(self.config.get('8080', 'port'))

        self.__server_thread = None

        scheduler.add_startup_job(f'{self.name}-startup', self.startup)

    async def startup(self):
        self.__server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.__server_thread.start()

    def run_server(self):
        httpd = http.server.HTTPServer((self.__host, self.__port), lambda x, y, z: self.MessagerelayHandler(self, x, y, z))
        self.print(f'Listening to {self.__host}:{self.__port}...')
        httpd.serve_forever()            

    class MessagerelayHandler(http.server.BaseHTTPRequestHandler):
        __channels = {
            'alert': Plugin.Channel.alert,
            'info': Plugin.Channel.info,
            'verbose': Plugin.Channel.verbose,
            'report': Plugin.Channel.report,
            'error': Plugin.Channel.error,
            'debug': Plugin.Channel.debug
        }

        def __init__(self, plugin, *args):
            self.__plugin = plugin
            super().__init__(*args)

        def do_POST(self):
            content_length = int(self.headers['Content-Length'])
            payload = self.rfile.read(content_length)
            try:
                data = json.loads(payload)

                sender = data['sender']
                channel = self.__channels[data['channel']]
                message = data['message']

                self.__plugin.send(channel, message, sender)
            except:
                self.__plugin.msg.error(f'Invalid incoming message: {data}')

                self.send_response(400)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Content-Length', 16)
                self.end_headers()
                self.wfile.write(b'invalid message')
                return
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Content-Length', 7)
            self.end_headers()
            self.wfile.write(b'success')

        def log_message(self, format, *args):
            return
