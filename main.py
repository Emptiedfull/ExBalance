import subprocess
import atexit
import logging
import asyncio
import random
import os
from datetime import datetime
import hashlib
import curses
from configParser import App_config,logging_config
from aiohttp import web,ClientSession

concurrent_processes = []


class Server():
    file = App_config["app"]
    free_ports = [str(x)
                   for x in range(8000, 8060)]
    request_counter = 0
    servers_in_prep = 0
    

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
   
        command = ["uvicorn", f'{file}:app',
                   "--host", "0.0.0.0", "--port", str(port)]
        

        with open(f'{logging_config["PortLogPath"]}/{port}.log', "w") as log_file,open(f'{logging_config["ErrorLogPath"]}/error{port}.log', "w") as error_log:
            process = subprocess.Popen(
                command, stdout=log_file, stderr=error_log)

        
        server = cls(name=name, process=process, port=port)
        
        print(f"Server running on port {port}")
        return await cls.wait_for_server(port,server)
      

    
    @classmethod
    async def wait_for_server(cls, port,server):
        cls.servers_in_prep += 1
        url = f"http://localhost:{port}"
        async with ClientSession() as session:
            while True:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            print(f"Server on port {port} is ready")
                            concurrent_processes.append(server)
                            cls.servers_in_prep -= 1
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
            elif proc.active >= 1:
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
    logging.basicConfig(filename=logging_config["AppLogPath"], level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('web_app')

    app = web.Application(logger=logger)
    app.router.add_route('*', '/{tail:.*}',Server.handle_request) 
    return app


async def run_http_server(port):
    app = web_app()
    web.run_app(app, port=port)
    print(f"New server running on port {port}")

async def monitor(stdscr):
    curses.curs_set(0)  
    stdscr.nodelay(1)  
    Descale_pings = 0
    while True:
        await asyncio.sleep(1)
        request_counter = Server.request_counter
        active_servers = len(concurrent_processes)

        requests_per_server = request_counter / active_servers if active_servers > 0 else 0
        current_action = None
        threshold = App_config["threshold"]

        if requests_per_server>threshold:
            current_action = "Creating new server"
            Server.create()

       

        stdscr.clear()
        
        stdscr.addstr(0, 0, f"Total requests: {request_counter}")
        stdscr.addstr(1, 0, f"Active servers: {active_servers}")
        stdscr.addstr(2,0,f"Inactive: {len(Server.free_ports)}")
        stdscr.addstr(3,0,f"Servers in prep: {Server.servers_in_prep}")
        stdscr.addstr(4, 0, f"Requests per server: {requests_per_server:.2f}")
        stdscr.addstr(5,0,f"Current action: {current_action}")
        stdscr.refresh()

        Server.request_counter = 0






async def main(port,stdscr):
    server_task = asyncio.create_task(asyncio.to_thread(run_http_server, port))
    monitor_task = asyncio.create_task(monitor(stdscr))
    await asyncio.gather(server_task, monitor_task)



if __name__ == "__main__":
 
    os.makedirs("logs", exist_ok=True)
    for filename in os.listdir('logs'):
        file_path = os.path.join('logs', filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    if os.path.exists(logging_config["AppLogPath"]):
        os.remove(logging_config["AppLogPath"])
    
    
   
    atexit.register(Server.terminate_all)
    
    asyncio.run(Server.create())
   
    if __name__ == "__main__":
        curses.wrapper(lambda stdscr: asyncio.run(main(App_config["port"],stdscr)))
