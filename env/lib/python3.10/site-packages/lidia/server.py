from argparse import Namespace
import queue
import eventlet
from msgpack import packb
from multiprocessing import Queue
from os import path
import socket
import socketio
from typing import Dict, Optional


from .config import Config


def background_loop(q: Queue, sio: socketio.Server, args: Namespace):
    udp_host, udp_port = args.passthrough_host, args.passthrough_port
    udp_sock = None
    if udp_host is not None and udp_port is not None:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        try:
            while not q.empty():
                event, data = q.get()
                sio.emit(event, data)
                if args.verbosity >= 2:
                    print(f"socketio.emit('{event}', {data})")
                if event == 'smol' and udp_sock is not None:
                    sent_len = udp_sock.sendto(
                        packb(data), (udp_host, udp_port))
                    if args.verbosity >= 2:
                        print(
                            f"sent {sent_len} bytes to udp:{udp_host}:{udp_port}")
        except queue.Empty:
            pass
        eventlet.sleep(0.02)


def run_server(q: Queue, args: Namespace, config: Config):
    # specifying just local path breaks when run as a module
    root_path = path.abspath(path.dirname(__file__))
    pages_path = path.join(root_path, 'pages')
    static_files = {
        # @deprecated: change to info.html
        '/': {'content_type': 'text/html', 'filename': path.join(pages_path, 'controls.html')},
        '/info': {'content_type': 'text/html', 'filename': path.join(pages_path, 'info.html')},
        '/controls': {'content_type': 'text/html', 'filename': path.join(pages_path, 'controls.html')},
        '/pfd': {'content_type': 'text/html', 'filename': path.join(pages_path, 'pfd.html')},
        '/approach': {'content_type': 'text/html', 'filename': path.join(pages_path, 'approach.html')},
        '/static': path.join(root_path, 'pages/static'),
    }

    sio = socketio.Server()

    @sio.on('config_request')
    def config_request(_sid, _environ):
        q.put(('config', config.dict()))

    app = RedirectingWSGIApp(sio, static_files=static_files, redirects={
        '/rpctask': '/controls'
    })
    eventlet.spawn(background_loop, q, sio, args)
    eventlet.wsgi.server(eventlet.listen((args.http_host, args.http_port)),
                         app, log_output=args.verbosity >= 3)


class RedirectingWSGIApp(socketio.WSGIApp):
    
    def __init__(self, socketio_app, static_files=None, redirects: Optional[Dict[str, str]]=dict()):
        super(RedirectingWSGIApp, self).__init__(socketio_app, static_files=static_files)
        self.redirects = redirects

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        if path in self.redirects:
            start_response('301 Moved Permanently', [
                ('Location', self.redirects[path]),
                ('Cache-Control', 'max-age=2592000'),  # 30 days, from example on MDN
                ('Content-Type', 'text/plain'),
            ])
            return [f'Path {path} is deprecated, redirecting to {self.redirects[path]}'.encode()]

        return super(RedirectingWSGIApp, self).__call__(environ, start_response)