from pathlib import PurePath

# Define the absolute path to the config directory
config_dir = PurePath("/etc/face-unlock")

# Define the absolute path to the DLib models data directory
dlib_data_dir = PurePath("/usr/share/face-unlock/dlib-data")

# Define the absolute path to the Howdy user models directory
user_models_dir = PurePath("/var/lib/face-unlock/models")

# Define path to any howdy logs
log_path = PurePath("/var/log/face-unlock")

# Define the absolute path to the Howdy data directory
data_dir = PurePath("/usr/share/howdy")