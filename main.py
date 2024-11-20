import subprocess

import atexit
import argparse

import asyncio
import random
import os
from datetime import datetime
from aiorun import run
import hashlib
import httpx
from http.server import SimpleHTTPRequestHandler, HTTPServer
from aiohttp import web,ClientSession

concurrent_processes = []


class Server():
    file = ""
    free_ports = [str(i) for i in range(8002, 8060)]

    request_counter = 0

    def __init__(self, name, process, port):
        self.name = name
        self.process = process
        self.port = port
        self.active = 0

    @classmethod
    def destroy(cls):
        process = random.choice(concurrent_processes)
        process.terminate()


    @classmethod
    async def create(cls, port=None):
        if len(cls.free_ports) == 0:
            print("No free ports")
            return None

        port = cls.free_ports.pop()
        file = cls.file
        name = hashlib.md5(f"{file}{datetime.now()}".encode()).hexdigest()
        if file.endswith(".py"):
            file = file[:-3]
        command = ["uvicorn", f'{file}:app',
                   "--host", "0.0.0.0", "--port", port]

        with open(f'logs/{port}.log', "w") as log_file,open(f'logs/error{port}.log', "w") as error_log:
            process = subprocess.Popen(
                command, stdout=log_file, stderr=error_log)

        
        server = cls(name=name, process=process, port=port)
        
        print(f"Server running on port {port}")
        return await cls.wait_for_server(port,server)
      

    
    @classmethod
    async def wait_for_server(cls, port,server):
        url = f"http://localhost:{port}"
        async with ClientSession() as session:
            while True:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            print(f"Server on port {port} is ready")
                            concurrent_processes.append(server)
                            return server
                except Exception as e:
                    await asyncio.sleep(0.1)

    def terminate(self):
        print(f"Terminating {self.port}")
        self.process.terminate()
        concurrent_processes.remove(self)
        self.free_ports.append(self.port)

    @classmethod
    def terminate_all(cls):
        print("Terminating all servers")
        for process in concurrent_processes:
            process.terminate()
        concurrent_processes.clear()

    @classmethod
    async def handle_request(cls, request):
    

        cls.request_counter += 1

        i = 0
        
        while i < len(concurrent_processes):
            proc = concurrent_processes[i]
            
            if proc.process.poll() is not None:
                print(f"Server {proc.port} has crashed with code {proc.process.returncode} and {proc.process.stderr}")
                concurrent_processes.remove(proc)
            elif proc.active >= 5:
                i += 1
            else:
                process = proc
                break
        else:
            
            process = await cls.create()
            if process is None:
                process = random.choice(concurrent_processes)

        print(process.port + "requested")

    

        url = f"http://localhost:{process.port}{request.path}"
        
        process.active += 1
       
        try:
          async with ClientSession() as session:
            async with session.get(url) as response:
                response_text = await response.text()
                return web.Response(
                    text=response_text,
                    status=response.status,
                    headers=response.headers
                )
        except Exception as e:
            print(f"Error handling request: {e}")
            return None
        finally:
           
            process.active -= 1

async def web_app():
    app = web.Application()
    app.router.add_route('*', '/{tail:.*}',Server.handle_request) 
    return app


def run_http_server(port):
    app = web_app()
    web.run_app(app, port=port)
    print(f"New server running on port {port}")




async def main(port):
    server_task = asyncio.create_task(asyncio.to_thread(run_http_server, port))
   
    await asyncio.gather(server_task)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Load Balancer')
    parser.add_argument("server", help="Fastapi server containing app object")
    parser.add_argument("port", help="Port to run server on")
    args = parser.parse_args()

    os.makedirs("logs", exist_ok=True)
    for filename in os.listdir('logs'):
        file_path = os.path.join('logs', filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

    Server.file = args.server
    atexit.register(Server.terminate_all)
    
    asyncio.run(Server.create())
   
    asyncio.run(main(int(args.port)))
