# utils/config_handler.py
import json

def load_uplift_config(uploaded_file):
    return json.load(uploaded_file)
