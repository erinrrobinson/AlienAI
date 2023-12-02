import requests
import asyncio
from computerender import Computerender
import os
import time
from pythonosc.udp_client import SimpleUDPClient
import uuid

##########################################################
##########################################################
##################### FOR ULI ############################
# LOOP LENGTH 1800 = 30 minutes in seconds, change accordingly (seconds only)
loop_length = 1800
# THE PATH TO WHERE THE PHOTOS WILL BE STORED. YOU NEED THIS IN THE TOUCHDESIGNER FILE TOO.
images_directory = "C:/Users/thewi/Documents/Collaborations/Uli/PythonPhotos/automated/"
# THE PATH TO WHERE THE TEXT FILE IS FOR SAVING PROMPTS
text_file = "C:/Users/thewi/Documents/Collaborations/Uli/SAVED_FILES/saved_prompts.txt"
# PATH FOR PERMANENT SAVED IMAGES
permanent_images_directory = "C:/Users/thewi/Documents/Collaborations/Uli/SAVED_FILES/TEXT2IMAGE"
# KEYWORDS FOR IMAGE GENERATION
keywords = "bright yellow, yellow background, weird, high definition, 8k"
##########################################################
##########################################################

# Constants
ENDPOINT_URL = 'https://upload.uliap.art/text_api.php'
LOCAL_FILE_PATH = 'local_user_text.txt'
COUNTER_FILE_PATH = 'image_counter.txt'

# OSC Client Setup
osc_ip = "127.0.0.1"
osc_port = 12345
osc_client = SimpleUDPClient(osc_ip, osc_port)


if not os.path.exists(permanent_images_directory):
    os.makedirs(permanent_images_directory)

def save_downloaded_prompts(prompts, file_path):
    try:
        with open(file_path, 'a', encoding='utf-8') as file:
            for prompt in prompts:
                file.write(prompt + '\n')
        print(f"Prompts successfully saved to {file_path}")
    except IOError as e:
        print(f"Error saving prompts to file: {e}")

# Function to send OSC message
def send_osc_message(message):
    osc_client.send_message("/trigger", message)
    print(f"OSC message {message} sent to {osc_ip}:{osc_port}")

# Function to delete files in a directory
def clear_directory(directory):
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Deleted file: {file_path}")

# Initialize Computerender
cr = Computerender(api_key=os.environ.get("COMPUTERENDER_API_KEY", "sk_38oobfLFVlaTaojv5udmH"))

if not os.path.exists(images_directory):
    os.makedirs(images_directory)

def check_endpoint(url):
    """ Check if the text file at the endpoint is empty """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("found lines")
            content = response.text.strip()
            print(content)
            return content
        else:
            print(f"Error: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def clear_remote_file(url):
    """ Send a POST request to the endpoint to clear the file """
    try:
        response = requests.post(url, json={"command": "clear"})
        if response.status_code == 200:
            print("Remote file cleared successfully.")
        else:
            print(f"Failed to clear remote file. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Request to clear file failed: {e}")

def write_to_local_file(content, file_path):
    try:
        items = eval(content)
        with open(file_path, 'w', encoding='utf-8') as file:
            for item in items:
                clean_item = clean_prompt(item)
                file.write(clean_item + '\n')
    except SyntaxError as e:
        print(f"Error parsing content: {e}")
    except IOError as e:
        print(f"Error writing to file: {e}")

async def generate_image(prompt, save_directory, permanent_directory, primary_letter, secondary_letter, number, save_to_permanent):
    """Generate an image using Computerender and save it in two locations."""
    try:
        file_name = f"{primary_letter}{secondary_letter}{number}.jpg"
        print(f"Generating image: {prompt} as {file_name}")
        prompt = clean_prompt(prompt)
        img_bytes = await cr.generate(prompt + keywords, w=512, h=512)

        # Save in the usual directory
        usual_path = os.path.join(save_directory, f'image_{file_name}')
        with open(usual_path, 'wb') as file:
            file.write(img_bytes)

        # Save to the permanent directory only if indicated
        if save_to_permanent:
            unique_file_name = f"{uuid.uuid4()}.jpg"
            permanent_path = os.path.join(permanent_directory, unique_file_name)
            with open(permanent_path, 'wb') as file:
                file.write(img_bytes)
            print(f"Image also saved as {unique_file_name} in the permanent directory")

        print(f"Generated image {file_name} for prompt '{prompt}'")
    except Exception as e:
        print(f"Error generating image for prompt '{prompt}': {e}")


async def process_lines_and_get_images(file_path, save_directory, letter, number):
    tasks = []
    with open(file_path, 'r') as file:
        for line in file:
            task = generate_image(line.strip(), save_directory, letter, number)
            tasks.append(task)
            letter, number = increment_counter(letter, number)  # Increment the counter after scheduling each task
    await asyncio.gather(*tasks)
    return letter, number  # Return the updated counter values

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

def clean_prompt(prompt):
    # Remove surrogate characters and return a clean string
    return prompt.encode('utf-16', 'surrogatepass').decode('utf-16')
async def cleanup_on_exit():
    #start animation
    send_osc_message(0)
    await asyncio.sleep(20)
    clear_directory(images_directory)
    primary_letter, secondary_letter, number = 'a', 'a', 1  # Reset counter
    update_counter(COUNTER_FILE_PATH, primary_letter, secondary_letter, number)
    await asyncio.sleep(2)
    #stop animation
    send_osc_message(1)
    print("Cleanup completed: OSC message sent, files deleted, and counter reset.")

def update_counter(file_path, primary_letter, secondary_letter, number):
    """ Update the counter value in a file """
    with open(file_path, 'w') as file:
        file.write(f"{primary_letter},{secondary_letter},{number}")


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


# Main function with repeated process and cleanup on interruption
async def main():
    primary_letter, secondary_letter, number = read_counter(COUNTER_FILE_PATH)
    last_prompt = None
    processed_prompts = set()  # Set to keep track of processed prompts

    try:
        while True:  # Outer loop for restarting the process
            start_time = time.time()
            while True:  # Inner loop for loop_length cycles
                current_time = time.time()
                if current_time - start_time >= loop_length:
                    await cleanup_on_exit()
                    break  # Break out of the inner loop to restart the image generation process

                content = check_endpoint(ENDPOINT_URL)
                prompts_to_process = []

                if content:
                    write_to_local_file(content, LOCAL_FILE_PATH)
                    with open(LOCAL_FILE_PATH, 'r') as file:
                        prompts_to_process = [line.strip() for line in file if line.strip()]

                    if prompts_to_process:
                        # Save downloaded prompts
                        save_downloaded_prompts(prompts_to_process, text_file)

                        for prompt in prompts_to_process:
                            # Check if the prompt is new and should be saved to permanent directory
                            save_to_permanent = prompt not in processed_prompts
                            processed_prompts.add(prompt)

                            await generate_image(prompt, images_directory, permanent_images_directory, primary_letter, secondary_letter, number, save_to_permanent)
                            primary_letter, secondary_letter, number = increment_counter(primary_letter, secondary_letter, number)
                            last_prompt = prompt
                        update_counter(COUNTER_FILE_PATH, primary_letter, secondary_letter, number)
                    elif last_prompt:
                        await generate_image(last_prompt, images_directory, permanent_images_directory, primary_letter, secondary_letter, number, False)  # False since it's not the first occurrence
                        primary_letter, secondary_letter, number = increment_counter(primary_letter, secondary_letter, number)
                        update_counter(COUNTER_FILE_PATH, primary_letter, secondary_letter, number)
                    else:
                        print("No new prompts and no last prompt available. Waiting 3 seconds.")
                        await asyncio.sleep(7)

                await asyncio.sleep(7)  # Wait before the next check

            # Reset primary_letter, secondary_letter, number after cleanup
            primary_letter, secondary_letter, number = 'a', 'a', 1

    except KeyboardInterrupt:
        print("Script interrupted by user.")
    finally:
        await cleanup_on_exit()

try:
    asyncio.run(main())
except Exception as e:
    print(f"Script stopped due to an unexpected error: {e}")
finally:
    cleanup_on_exit()
