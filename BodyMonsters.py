import requests
import os
import time
import base64
import replicate
import signal
import sys
from PIL import Image
import uuid

########################################################
########################################################
# A folder on your computer that can download the raw body images
download_dir = "C:/Users/thewi/Documents/Collaborations/Uli/PythonPhotos/test"
# A folder on your computer that will be opened also in touchdesigner
touchdesigner_directory = "C:/Users/thewi/Documents/Collaborations/Uli/bodymonstertouchdesigner"
# A folder to keep the AI generated images
local_directory = "C:/Users/thewi/Documents/Collaborations/Uli/SAVED_FILES/BODYMONSTERSGENERATED"
# A folder to keep the AI generated images
original_photos = "C:/Users/thewi/Documents/Collaborations/Uli/SAVED_FILES/BODYMONSTERSORIGINALS"
# STRENGTH - 1 = NO IMAGE RECOGNITION, 0 = ORIGINAL IMAGE
strength = 0.7
########################################################
########################################################


# Server URL and Directories
server_url = 'https://upload.uliap.art/'
counter_file = 'image_counter2.txt'

# Replicate API Token
os.environ['REPLICATE_API_TOKEN'] = "r8_NFNGbqrZa4qoAd1e4eUkRaEfV637VDZ3e2uOE"

# Check if the directories exist, if not, create them
for directory in [download_dir, touchdesigner_directory, local_directory, original_photos]:
    if not os.path.exists(directory):
        os.makedirs(directory)


def resize_image(image_path, output_size=(512, 512)):
    """
    Resize the image to a specific size and save it.
    """
    with Image.open(image_path) as img:
        img = img.resize(output_size)
        img.save(image_path)

def read_counter(file_path):
    """ Read the current counter value from a file """
    if not os.path.exists(file_path):
        return ('a', 'a', 1)  # Start from 'aa1' if the file doesn't exist
    with open(file_path, 'r') as file:
        data = file.read().strip().split(',')
        if len(data) == 2:  # Old format with a single letter
            return (data[0], 'a', int(data[1]))  # Treat as primary letter, start secondary at 'a'
        elif len(data) == 3:  # New format with two letters
            return (data[0], data[1], int(data[2]))
        else:
            raise ValueError("Invalid counter file format")

def increment_counter(primary_letter, secondary_letter, number):
    """ Increment the counter with a two-letter system """
    number += 1
    if number > 9:
        number = 1
        if secondary_letter == 'z':  # Check if the secondary letter is 'z'
            secondary_letter = 'a'  # Reset secondary letter to 'a'
            if primary_letter == 'z':  # Check if the primary letter is 'z'
                primary_letter = 'a'  # Reset primary letter to 'a'
            else:
                primary_letter = chr(ord(primary_letter) + 1)  # Increment primary letter
        else:
            secondary_letter = chr(ord(secondary_letter) + 1)  # Increment secondary letter
    return primary_letter, secondary_letter, number
# Function to convert image to base64

def resize_image(image_path, output_size=(512, 512)):
    with Image.open(image_path) as img:
        img = img.resize(output_size)
        img.save(image_path)

def update_counter(file_path, primary_letter, secondary_letter, number):
    """ Update the counter value in a file """
    with open(file_path, 'w') as file:
        file.write(f"{primary_letter},{secondary_letter},{number}")

# Function to convert image to base64
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def delete_images_with_keyword(directory, keyword):
    """Delete all files in the given directory that contain the specified keyword."""
    for filename in os.listdir(directory):
        if keyword in filename:
            os.remove(os.path.join(directory, filename))
            print(f"Deleted {filename}")

def signal_handler(sig, frame):
    """Handle interrupt signals and perform cleanup."""
    print('Interrupt received, cleaning up...')

    # Reset the counter
    primary_letter, secondary_letter, number = 'a', 'a', 1
    update_counter(counter_file, primary_letter, secondary_letter, number)
    print("Counter reset to initial values.")

    delete_images_with_keyword(touchdesigner_directory, 'image')
    sys.exit(0)


# Register the signal handler for clean interruption
signal.signal(signal.SIGINT, signal_handler)


def process_and_save_images(image_paths):
    for image_path in image_paths:
        resize_image(image_path)
        image_base64 = image_to_base64(image_path)
        data_uri = f"data:image/jpg;base64,{image_base64}"

        output = replicate.run(
            "erinrrobinson/bodymonsters1000:14ed44aa5190c33843eb0e648d427da0e8d6202999da39a39221ea6605e41f34",
            input={
                "image": data_uri,
                "width": 512,
                "height": 512,
                "prompt": "style of bdymnstr",
                "scheduler": "DDIM",
                "num_outputs": 1,
                "guidance_scale": 12,
                "prompt_strength": strength,
                "num_inference_steps": 20,
                "disable_safety_check": True
            }
        )

        primary_letter, secondary_letter, number = read_counter(counter_file)

        if isinstance(output, list) and output:
            for i, url in enumerate(output, start=1):
                response = requests.get(url)
                if response.status_code == 200:
                    # Counter-based filename for touchdesigner_directory
                    counter_file_name = f"image_{primary_letter}{secondary_letter}{number}.png"

                    # Random string filename for local_directory
                    random_file_name = f"{uuid.uuid4()}.png"

                    # Save in the touchdesigner directory
                    with open(os.path.join(touchdesigner_directory, counter_file_name), 'wb') as f:
                        f.write(response.content)

                    # Save in the local directory with a random filename
                    with open(os.path.join(local_directory, random_file_name), 'wb') as f:
                        f.write(response.content)

                    primary_letter, secondary_letter, number = increment_counter(primary_letter, secondary_letter,
                                                                                 number)
                    print(
                        f"Downloaded and processed image {counter_file_name} to {touchdesigner_directory} and {random_file_name} to {local_directory}")
                else:
                    print(f"Failed to download and process image {i}")

        update_counter(counter_file, primary_letter, secondary_letter, number)

try:
    while True:
        # Download Images
        response = requests.get(f'{server_url}/list_images.php')
        if response.status_code == 200:
            image_data = response.json()
            downloaded_images = []

            for image_filename in image_data:
                image_url = f'{server_url}/uploads/photos/{image_filename}'
                download_response = requests.get(image_url)
                print(f'downloading image {image_url}')
                if download_response.status_code == 200:
                    image_path = os.path.join(download_dir, image_filename)

                    # Generate a unique filename for the original image
                    unique_original_filename = f"{uuid.uuid4()}.jpg"
                    original_image_path = os.path.join(original_photos, unique_original_filename)

                    with open(image_path, 'wb') as file:
                        file.write(download_response.content)

                    # Save a copy to the original_images directory with a unique filename
                    with open(original_image_path, 'wb') as original_file:
                        original_file.write(download_response.content)

                    resize_image(image_path)  # Resize the image
                    downloaded_images.append(image_path)
                    print(f"Downloaded image and saved original as {unique_original_filename}")
                else:
                    print(f"Failed to download image: {image_filename}")

            # Process and Save Images
            if downloaded_images:
                print("making AI magic...")
                process_and_save_images(downloaded_images)

                # Delete downloaded files from the server
                delete_response = requests.post(f'{server_url}/delete_images.php', json={'files': [os.path.basename(path) for path in downloaded_images]})
                if delete_response.status_code == 200:
                    print("Files deleted successfully on server.")
                else:
                    print("Failed to delete files on server.")
            else:
                print("No new files to download and process.")

        time.sleep(5)  # Wait for 5 seconds before next iteration

except KeyboardInterrupt:
    # Clean up if interrupted
    delete_images_with_keyword(touchdesigner_directory, 'image')
