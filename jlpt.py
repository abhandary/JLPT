#!/opt/homebrew/bin/python3

import csv
import sys
import wave
import io
import numpy as np
import time

import google.cloud.texttospeech as tts


csv_data = ""  # Initialize the CSV data variable

def remove_trailing_zeros(data):
    index = len(data)
    while index > 0 and data[index - 1] == 0:
        index -= 1
    return data[:index]

def text_to_wav(text: str, language_code: str, voice_name: str):
    text_input = tts.SynthesisInput(text=text)
    voice_params = tts.VoiceSelectionParams(
        language_code=language_code, name=voice_name
    )
    client = tts.TextToSpeechClient()
    response = client.synthesize_speech(
        input=text_input,
        voice=voice_params,
        audio_config=audio_config,
    )
    return response

# Check if the correct number of command,line arguments is provided
if len(sys.argv) != 3:
    print("Usage: python read_file.py <input filename> <output filename>")
    sys.exit(1)

# Get the filename from the command,line argument
input_filename = sys.argv[1]

# Try to open and read the file
try:
    with open(input_filename, 'r') as file:
        csv_data = file.read()
except FileNotFoundError:
    print(f"File '{input_filename}' not found.")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {str(e)}")
    sys.exit(1)

# Split the CSV data into rows
rows = csv_data.strip().split('\n')

# Extract the second and third columns into a list
result_list = [row.split(',')[1:3] for row in rows]

# Print the result list
for item in result_list:
    print(item)

output_csv = sys.argv[2]

# Write the result list to a CSV file
try:
    with open(output_csv, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        for item in result_list:
            csvwriter.writerow(item)
    print(f"Data written to {output_csv}")
except Exception as e:
    print(f"An error occurred: {str(e)}")
    sys.exit(1)


japanese_voice = "ja-JP-Standard-A"
english_voice = "en-US-Standard-E"

japanese_language_code = "-".join(japanese_voice.split("-")[:2])
english_language_code = "-".join(english_voice.split("-")[:2])

audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)



pause_duration_seconds = 5

combined_audio = wave.open("ouput.wav", 'wb')
combined_audio_params_set = False

count = 1
for item in result_list:
    japanese_audio = text_to_wav(item[0], japanese_language_code, japanese_voice)
    english_audio = text_to_wav(item[1], english_language_code, english_voice)    

    with open("temp_jap", "wb") as out:
        out.write(japanese_audio.audio_content)
        out.close()
    with open("temp_english", "wb") as out:
        out.write(english_audio.audio_content)
        out.close()

   # time.sleep(5)

    japanese_stream = io.BytesIO(japanese_audio.audio_content)
    english_stream = io.BytesIO(english_audio.audio_content)

    japanese_audio_wav = wave.open("temp_jap", 'rb')
    english_audio_wav = wave.open("temp_english", 'rb')

    japanese_audio_data = japanese_audio_wav.readframes(1000024)
    english_audio_data = english_audio_wav.readframes(1000024)    

    reference_params = japanese_audio_wav.getparams()

    pause_frames = int(reference_params.framerate * pause_duration_seconds)    
    zero_frames = np.zeros(reference_params.nchannels * reference_params.sampwidth * pause_frames, dtype=np.uint8)

    if combined_audio_params_set == False:
        combined_audio.setparams(reference_params)                  # Set the parameters for the output WAV file
        combined_audio_params_set = True
    combined_audio.writeframes(japanese_audio_data)     # write the japanese audio
    combined_audio.writeframes(zero_frames.tobytes())   # add 5 seconds of silence
    combined_audio.writeframes(english_audio_data)      # write the english audio 
    combined_audio.writeframes(zero_frames.tobytes())   # add 5 seconds of silence

    japanese_audio_wav.close()
    japanese_audio_wav.close()
    print(f"finished writing {item[0]}:{item[1]}")
    count = count + 1

combined_audio.close()    
