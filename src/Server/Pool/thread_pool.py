import os
import threading

import gevent
from gevent import queue
from gevent.monkey import patch_all

from Models.tcp_request import TcpRequest
from Server.request_handler import RequestHandler

patch_all()


class ThreadPool:
    MAX_WORKERS: int
    MAX_FIBERS: int
    request_queue: queue.Queue
    request_handler: RequestHandler

    def __init__(self, max_workers=None, max_fibers=None):
        self.MAX_WORKERS = (
            max_workers
            if max_workers is not None
            else int(os.getenv("MAX_WORKERS"))
            if os.getenv("MAX_WORKERS")
            else 10
        )
        self.MAX_FIBERS = (
            max_fibers
            if max_fibers is not None
            else int(os.getenv("MAX_FIBERS"))
            if os.getenv("MAX_FIBERS")
            else 10
        )

        self.request_queue = queue.Queue(0)
        # print(f">> Initializing {self.MAX_WORKERS} worker threads")
        for _ in range(self.MAX_WORKERS):
            threading.Thread(target=self.read_request_pool).start()

        self.request_handler = RequestHandler()

    def read_request_pool(self):
        while True:
            try:
                # blocks the working thread until an item is available on the queue
                request = self.request_queue.get(block=True, timeout=None)
                # print(">> dequeuing item")
                gevent.spawn(self.request_handler.handle_client, request)
            except queue.Empty:
                pass

    def get_backlog_length(self):
        # backlog stands for the max amount of sockets with open connections on the server
        return self.MAX_FIBERS * self.MAX_WORKERS

    def enqueue_request(self, request: TcpRequest):
        # dequeue function is not necessary because request_pool.get() already pops the request from the Queue.
        try:
            # print(">> enqueuing request")
            # raises `queue.Full` exception if no free slot is immediately available
            self.request_queue.put(request, block=False)
        except queue.Full:
            pass
