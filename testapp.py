from fastapi import FastAPI
import uvicorn
import hashlib,time
import asyncio



app = FastAPI()

def proof_of_work(data, difficulty):
    nonce = 0
    prefix = '0' * difficulty
    while True:
        text = f"{data}{nonce}".encode()
        hash_result = hashlib.sha256(text).hexdigest()
        if hash_result.startswith(prefix):
            return nonce, hash_result
        nonce += 1

    
@app.get("/")
async def read_root(): 
    
    print("Request received")
    return {"Hello": uvicorn.Config(app).port}


@app.get("/pow")
async def get_pow():
    start_time = time.time()
    time.sleep(1)
    time_taken = time.time() - start_time
    return time_taken