#!/usr/bin/env python3
"""
Flask wrapper for Diriyah Brain AI deployment
"""
import os
import sys
import subprocess
import threading
import time
from flask import Flask, request, jsonify, send_from_directory, redirect
import requests

app = Flask(__name__)

# Global variable to store FastAPI process
fastapi_process = None

def start_fastapi():
    """Start FastAPI server in background"""
    global fastapi_process
    try:
        fastapi_process = subprocess.Popen([
            sys.executable, "main.py"
        ], cwd="/src")
        print("FastAPI server started")
    except Exception as e:
        print(f"Error starting FastAPI: {e}")

def wait_for_fastapi():
    """Wait for FastAPI to be ready"""
    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get("http://localhost:8080/", timeout=1)
            if response.status_code == 200:
                print("FastAPI is ready")
                return True
        except:
            pass
        time.sleep(1)
    return False

# Start FastAPI in background thread
threading.Thread(target=start_fastapi, daemon=True).start()

@app.route('/')
def index():
    """Proxy to FastAPI"""
    if not wait_for_fastapi():
        return "FastAPI server not ready", 503
    
    try:
        response = requests.get("http://localhost:8080/")
        return response.content, response.status_code, response.headers.items()
    except Exception as e:
        return f"Error connecting to FastAPI: {e}", 500

@app.route('/<path:path>')
def proxy(path):
    """Proxy all other requests to FastAPI"""
    if not wait_for_fastapi():
        return "FastAPI server not ready", 503
    
    try:
        url = f"http://localhost:8080/{path}"
        
        if request.method == 'GET':
            response = requests.get(url, params=request.args)
        elif request.method == 'POST':
            response = requests.post(url, json=request.get_json(), params=request.args)
        else:
            response = requests.request(request.method, url, 
                                      data=request.get_data(), 
                                      params=request.args)
        
        return response.content, response.status_code, response.headers.items()
    except Exception as e:
        return f"Error proxying to FastAPI: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

