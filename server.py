import logging
from flask import Flask, request, jsonify
import requests
import base64
import json
import os
from tqdm import tqdm
from io import BytesIO
import time
from PIL import Image


# logger, environment
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# flask
app = Flask(__name__)
AI_HORDE_API_URL = 'https://aihorde.net'

def get_aihorde_api_key():
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split("Bearer ")[1]
    return "0000000000"

@app.route('/images/generations', methods=['POST'])
def generate_image():
    try:
        data = request.get_json()
        model, *params = data.get("model", "stable_diffusion").split("*")
        form_data = {
            "prompt": data.get("prompt"),
            "n": int(data.get("n", 1)),
            "size": data.get("size", "512x512"),
            "model": model,
        }
        created_time = time.time()
        logging.debug(form_data)
        payload = {
            "prompt": form_data["prompt"],
            "models": [form_data["model"]],
            "params": {
                "n": form_data["n"],
                "width": int(form_data["size"].split('x')[0]),
                "height": int(form_data["size"].split('x')[1]),
                "steps": 50,
                "sampler_name": "k_euler_a",
                "cfg_scale": 7.5,
                "denoising_strength": 0.6,
                "hires_fix_denoising_strength": 0.5,
            },
            "trusted_workers": False,
            "nsfw": "nsfw" in params,
            "censor_nsfw": "censor_nsfw" in params,
            "shared": "shared" in params,
            "r2": False,
        }
        logging.debug(payload)
        print(payload["prompt"])
        pbar_queue_position = tqdm(desc="queue position: N/A | Wait Time: N/A", bar_format="{desc}")
        pbar_progress = tqdm(total=form_data['n'], desc="progress")
        headers = {
            "apikey": get_aihorde_api_key(),
            "Client-Agent": "openwebui-image-generator"
        }
        response = requests.post(
            f"{AI_HORDE_API_URL}/api/v2/generate/async",
            json=payload,
            headers=headers
        )
        logging.info(response)
        try:
            logging.debug(response.json())
        except ValueError:
            logging.debug("Response body is not JSON")
        if not response.ok:
            logging.error(response.json())
            return jsonify({"error": "Failed to generate image"}), 500
        results = response.json()
        req_id = results.get('id')
        if not req_id:
            return jsonify({"error": "No request ID found in response"}), 400
        status_url = f"{AI_HORDE_API_URL}/api/v2/generate/check/{req_id}"
        retry = 0
        is_done = False
        while not is_done:
            try:
                chk_req = requests.get(status_url)
                if not chk_req.ok:
                    logging.error(f"Not ok starus response: {chk_req.status_code}")
                    logging.error(chk_req.json())
                    return jsonify({"error": "Not ok starus response"}), 500
                chk_results = chk_req.json()
                pbar_progress.desc = (
                    f"Wait:{chk_results.get('waiting')} "
                    f"Proc:{chk_results.get('processing')} "
                    f"Res:{chk_results.get('restarted')} "
                    f"Fin:{chk_results.get('finished')}"
                )
                pbar_queue_position.desc = f"Queue Position: {chk_results.get('queue_position')} | ETA: {chk_results.get('wait_time')}s"
                pbar_progress.n = chk_results.get('finished')
                pbar_queue_position.refresh()
                pbar_progress.refresh()
                is_done = chk_results['done']
                time.sleep(2)
            except ConnectionError as e:
                retry += 1
                logging.error(
                    f"Error {e} when retrieving status. Retry {retry}/10")
                if retry < 10:
                    time.sleep(10)
                    continue
                return jsonify({"error": "Failed to check image status"}), 500
        results_url = f"{AI_HORDE_API_URL}/api/v2/generate/status/{req_id}"
        results_response = requests.get(results_url, headers=headers)
        if not results_response.ok:
            logging.error(f"Failed to retrieve image results: {results_response.status_code}")
            logging.error(results_response.json())
            return jsonify({"error": "Failed to retrieve image results"}), 500
        results_data = results_response.json()
        try:
            logging.debug(results_response.json())
        except ValueError:
            logging.debug("Response body is not JSON")
        images = []
        pbar_queue_position.close()
        pbar_progress.close()
        for result in results_data['generations']:
            img_b64 = result["img"]
            images.append("data:image/webp," + result["img"])
        response = {
                "created": created_time,
                "data": [{"b64_json": x} for x in images],
        }
        return jsonify(response)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
