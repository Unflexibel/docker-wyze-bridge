import json
from os import environ
from typing import Optional

import requests

import wyzecam
from wyzebridge.logging import logger


def setup_hass(hass_token: Optional[str]) -> None:
    """Home Assistant related config."""
    if not hass_token:
        return

    logger.info("🏠 Home Assistant Mode")

    with open("/data/options.json") as f:
        conf = json.load(f)

    auth = {"Authorization": f"Bearer {hass_token}"}
    try:
        assert "WB_IP" not in conf, f"Using WB_IP={conf['WB_IP']} from config"
        net_info = requests.get("http://supervisor/network/info", headers=auth).json()
        for i in net_info["data"]["interfaces"]:
            if i["primary"]:
                environ["WB_IP"] = i["ipv4"]["address"][0].split("/")[0]
    except Exception as e:
        logger.error(f"WEBRTC SETUP: {e}")

    mqtt_conf = requests.get("http://supervisor/services/mqtt", headers=auth).json()
    if "ok" in mqtt_conf.get("result") and (data := mqtt_conf.get("data")):
        environ["MQTT_HOST"] = f'{data["host"]}:{data["port"]}'
        environ["MQTT_AUTH"] = f'{data["username"]}:{data["password"]}'

    if cam_options := conf.pop("CAM_OPTIONS", None):
        for cam in cam_options:
            if not (cam_name := wyzecam.clean_name(cam.get("CAM_NAME", ""))):
                continue
            if "AUDIO" in cam:
                environ[f"ENABLE_AUDIO_{cam_name}"] = str(cam["AUDIO"])
            if "FFMPEG" in cam:
                environ[f"FFMPEG_CMD_{cam_name}"] = str(cam["FFMPEG"])
            if "NET_MODE" in cam:
                environ[f"NET_MODE_{cam_name}"] = str(cam["NET_MODE"])
            if "ROTATE" in cam:
                environ[f"ROTATE_CAM_{cam_name}"] = str(cam["ROTATE"])
            if "QUALITY" in cam:
                environ[f"QUALITY_{cam_name}"] = str(cam["QUALITY"])
            if "LIVESTREAM" in cam:
                environ[f"LIVESTREAM_{cam_name}"] = str(cam["LIVESTREAM"])
            if "RECORD" in cam:
                environ[f"RECORD_{cam_name}"] = str(cam["RECORD"])
            if "SUBSTREAM" in cam:
                environ[f"SUBSTREAM_{cam_name}"] = str(cam["SUBSTREAM"])

    if rtsp_options := conf.pop("RTSP_SIMPLE_SERVER", None):
        for opt in rtsp_options:
            if (split_opt := opt.split("=", 1)) and len(split_opt) == 2:
                key = split_opt[0].strip().upper()
                key = key if key.startswith("RTSP_") else f"RTSP_{key}"
                environ[key] = split_opt[1].strip()

    for k, v in conf.items():
        environ.update({k.replace(" ", "_").upper(): str(v)})
