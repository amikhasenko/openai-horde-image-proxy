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

import re

def extract_command(command, used, text):
    pattern = "/" + command + r'\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))'
    match = re.search(pattern, text)
    if match:
        model_string = next(group for group in match.groups() if group is not None)
        # Remove the matched /model part from the text
        cleaned_text = re.sub(pattern, '', text, count=1).strip()
        return model_string, cleaned_text
    return used, text  # No match found

def extract_bool_command(command, used, text):
    if "/"+command not in text:
        return used, text
    return True, text.replace("/"+command, "")

def get_aihorde_api_key():
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split("Bearer ")[1]
    return "0000000000"

@app.route('/images/generations', methods=['POST'])
def generate_image():
    try:
        data = request.get_json()
        form_data = {
            "prompt": data.get("prompt"),
            "n": str(data.get("n", "1")),
            "size": data.get("size", "512x512"),
            "model": data.get("model", "stable_diffusion"),
            "steps": "50",
            "sampler_name": "k_euler_a",
            "nsfw": False,
            "shared": False,
            "censor_nsfw": False,
            "trusted_workers": False,
            "tilting": False,
            "sampler_name": "k_euler_a",
            "cfg_scale": 7.5,
            "denoising_strength": 0.6,
            "hires_fix_denoising_strength": 0.5,
            "post_processing": None,
        }
        form_data["model"], form_data["prompt"] = extract_command("model", form_data["model"], form_data["prompt"])
        form_data["model"], *params = form_data["model"].split("*")

        for name in ["size", "steps", "sampler_name", "denoising_strength", "hires_fix_denoising_strength", "cfg_scale", "post_processing", "n"]:
            form_data[name], form_data["prompt"] = extract_command(name, form_data[name], form_data["prompt"])
        for name in ["nsfw", "censor_nsfw", "shared", "trusted_workers", "transparent", "tiling"]:
            form_data[name], form_data["prompt"] = extract_bool_command(name, name in params, form_data["prompt"])
        
        
        created_time = time.time()
        logging.debug(form_data)
        payload = {
            "prompt": form_data["prompt"],
            "models": [form_data["model"]],
            "params": {
                "n": int(form_data["n"]),
                "width": int(form_data["size"].split('x')[0]),
                "height": int(form_data["size"].split('x')[1]),
                "steps": int(form_data["steps"]),
                "transparent": form_data["transparent"],
                "sampler_name": form_data["sampler_name"],
                "cfg_scale": float(form_data["cfg_scale"]),
                "denoising_strength": float(form_data["denoising_strength"]),
                "hires_fix_denoising_strength": float(form_data["hires_fix_denoising_strength"]),
                "post_processing": form_data["post_processing"].split("->") if form_data["post_processing"] != None else [],
                "tilting": form_data["tilting"],
            },
            "trusted_workers": form_data["trusted_workers"],
            "nsfw": form_data["nsfw"],
            "censor_nsfw": form_data["censor_nsfw"],
            "shared": form_data["shared"],
            "r2": False,
        }
        logging.debug(payload)
        print(payload["prompt"])
        pbar_queue_position = tqdm(desc="queue position: N/A | Wait Time: N/A", bar_format="{desc}")
        pbar_progress = tqdm(total=int(form_data['n']), desc="progress")
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
