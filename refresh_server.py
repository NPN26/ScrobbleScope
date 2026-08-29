import subprocess
from flask import Flask, jsonify

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/refresh', methods=['POST'])
def refresh():
    try:
        print("Running extract.py...")
        # Run extract.py NP26. stdin=subprocess.DEVNULL skips the interactive duration prompts.
        subprocess.run(["python", "extract.py", "NP26"], check=True, stdin=subprocess.DEVNULL)
        
        print("Running evidence sources...")
        # Run npm run sources in music-dashboard
        subprocess.run(["npm", "run", "sources"], cwd="music-dashboard", check=True)
        
        return jsonify({"status": "success", "message": "Data refreshed successfully"})
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": f"Command failed with code {e.returncode}"}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("Starting refresh server on port 5001...")
    app.run(port=5001)
