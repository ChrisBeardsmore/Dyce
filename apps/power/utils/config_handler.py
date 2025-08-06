import json

def save_uplift_config_dict(config_dict, file_path):
    with open(file_path, "w") as f:
        json.dump(config_dict, f, indent=2)

def load_uplift_config(uploaded_file):
    return json.load(uploaded_file)
