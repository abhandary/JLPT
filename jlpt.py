#!/opt/homebrew/bin/python3.10

import csv
import sys
import wave
import io
import numpy as np
import os
import pydub as pd
import imageio_ffmpeg as ffmpeg
import argparse
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import cv2
import subprocess

import google.cloud.texttospeech as tts

japanese_voice = "ja-JP-Standard-A"
english_voice = "en-US-News-K"

japanese_language_code = "-".join(japanese_voice.split("-")[:2])
english_language_code = "-".join(english_voice.split("-")[:2])


def main():
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="JLPT script.")

    csv_data = ""  # Initialize the CSV data variable

    parser.add_argument('-d', '--debug', action='store_true', help='Verbose Mode')
    parser.add_argument('-f', '--file',  nargs='+', help='Input filename')
    parser.add_argument('-c', '--csv', action='store_true', help='Enable csv generation')
    parser.add_argument('-a', '--audio', action='store_true', help='Enable audio generation')
    parser.add_argument('-v', '--video', action='store_true', help='Enable audio generation')

    args = parser.parse_args()

    for input_filename in args.file:
        print("==============================================================================")
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

        # Extract the kana to english data
        kana_to_english_result_list = [row.split(',')[1:3] for row in rows]

        # extract the kanji to kana data
        kanji_to_kana_result_list = [row.split(',')[0:2] for row in rows]

        if args.debug is True:
            # Print the result list
            for item in kana_to_english_result_list:
                print(item)
            for item in kanji_to_kana_result_list:
                print(item)      

        input_filename_without_extension = os.path.splitext(os.path.basename(input_filename))[0]

        if args.csv is True:
            generate_output_csv("kana_to_english_csv/" + input_filename_without_extension, kana_to_english_result_list)
            generate_output_csv("kanji_to_kana_csv/" + input_filename_without_extension, kanji_to_kana_result_list)

        if args.audio is True:
            generate_audio(kana_to_english_result_list, input_filename_without_extension)    

        if args.video is True:
            generate_video(kana_to_english_result_list, kanji_to_kana_result_list, input_filename_without_extension)    

def text_to_wav(text: str, language_code: str, voice_name: str):
    audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)
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


def generate_output_csv(output_file_path: str, result_list: list):

    # Extract the directory path from the file path
    directory_path = os.path.dirname(output_file_path)

    # Check if the directory exists, and create it if it doesn't
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    # Write the result list to a CSV file
    try:
        with open(output_file_path + ".csv", 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            for item in result_list:
                csvwriter.writerow(item)
        print(f"Generated - {output_file_path}.csv")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)


def generate_image(text: str):
    # Create a blank image with a white background
    width, height = 800, 600  # Adjust the dimensions as needed
    background_color = (255, 255, 255)  # White
    image = Image.new("RGB", (width, height), background_color)

    # Create a drawing context
    draw = ImageDraw.Draw(image)

    # Choose a font and font size
    font_path = "path/to/your/font.ttf"  # Specify the path to your font file
    font_size = 36
   # font = ImageFont.truetype(font_path, font_size)

    # Choose text color
    text_color = (0, 0, 0)  # Black

    # Calculate the position to center the text
    text_width, text_height = draw.textsize(text)
    x = (width - text_width) / 2
    y = (height - text_height) / 2

    # Write the text on the image
    draw.text((x, y), text, fill=text_color, align="center")

    # Save the image
    output_filename = "text_image.png"  # Specify the output filename
    image.save(output_filename)

def generate_input_file_to_ffmpeg(list_length):
    with open("temp/ffmpeg_list", "wb") as out: 
        for index in range(list_length):
            out.write(f"file 'output_{index}.mp4'\n".encode())


def generate_word_and_translation_sequenced_audio_clip(jap_text: str, english_text: str):
    japanese_audio = text_to_wav(jap_text, japanese_language_code, japanese_voice)
    english_audio = text_to_wav(english_text, english_language_code, english_voice)  

    with open("temp/temp_jap.wav", "wb") as out:
        out.write(japanese_audio.audio_content)
        out.close()
    with open("temp/temp_english.wav", "wb") as out:
        out.write(english_audio.audio_content)

    # open the temp jap file and temp english audio files and combine the two audio files into a single mp4 file which has
    # the image showing in it as video
    # Load the two audio files
    jap_audio = AudioFileClip("temp/temp_jap.wav")
    english_audio = AudioFileClip("temp/temp_english.wav")
    silence_audio = AudioFileClip("temp/silence.m4a")

    # Concatenate the audio clips with the gap
    return concatenate_audioclips([jap_audio, silence_audio, english_audio, silence_audio])

def generate_text_clip(word_text, duration):
    font_size = 50
    font_color = 'white'
    position = 'center' 
    font = "wqy-microhei.ttc"

    # kanji_txt_clip = TextClip(word_text, fontsize=font_size, color=font_color, font=font)
    kanji_txt_clip = TextClip(word_text, size=(0, 100), color=font_color, font=font)
    kanji_txt_clip = kanji_txt_clip.set_position(position).set_duration(duration)
    #if len(word_text) == 1:
    #    kanji_txt_clip = kanji_txt_clip.set_start(20)
    return kanji_txt_clip


def generate_empty_text_clip():
    font_size = 50
    font_color = 'white'
    position = 'center' 
    font = "wqy-microhei.ttc"

    empty_txt_clip = TextClip("~", fontsize=font_size, color=font_color, font=font)
    silence_audio = AudioFileClip("temp/silence.m4a")
    empty_txt_clip = empty_txt_clip.set_position(position).set_duration(silence_audio.duration)
    return empty_txt_clip

def run_ffmpeg_command(ouput_file_name_without_extension):

    file_path = f"video/{ouput_file_name_without_extension}.mp4"
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"File {file_path} has been removed.")

    command = f'ffmpeg -f concat -safe 0 -i temp/ffmpeg_list -c copy {file_path}'
    # Run the command in a subprocess
    try:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        # Print the standard output of the command
        print("Command output:")
        print(result.stdout)
    
    except subprocess.CalledProcessError as e:
        # If the command returns a non-zero exit code, it will raise a CalledProcessError
        print("Error running the command:")
        print(e)

def generate_video(kana_to_english_result_list: list, kanji_to_kana_result_list: list, ouput_file_name_without_extension: str): 
    ix = 0

    for item in kana_to_english_result_list:

        sequenced_audio = generate_word_and_translation_sequenced_audio_clip(item[0], item[1])
        kanji_text = kanji_to_kana_result_list[ix][0]
        kanji_txt_clip = generate_text_clip(kanji_text, sequenced_audio.duration)

        # Combine the text and audio clips into a single video track
        combined_video = CompositeVideoClip([kanji_txt_clip.set_audio(sequenced_audio)])
        combined_video.write_videofile(f"temp/output_{ix}.mp4", fps=25)    

        print(f"Done with video for {kanji_text}")

        ix = ix + 1    

    generate_input_file_to_ffmpeg(len(kana_to_english_result_list))
    run_ffmpeg_command(ouput_file_name_without_extension)


def generate_audio(kana_to_english_result_list: list,ouput_file_name_without_extension: str): 

    pause_duration_seconds = 5

    print(f"Generating audio for {ouput_file_name_without_extension}")
    combined_audio = wave.open(f"wav/{ouput_file_name_without_extension}.wav", 'wb')
    combined_audio_params_set = False

    ix = 0
    for item in kana_to_english_result_list:
        japanese_audio = text_to_wav(item[0], japanese_language_code, japanese_voice)
        english_audio = text_to_wav(item[1], english_language_code, english_voice)  

        with open("temp_jap", "wb") as out:
            out.write(japanese_audio.audio_content)
            out.close()
        with open("temp_english", "wb") as out:
            out.write(english_audio.audio_content)
            out.close()

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
            combined_audio.writeframes(zero_frames.tobytes())   # add 5 seconds of silence
        combined_audio.writeframes(japanese_audio_data)     # write the japanese audio
        combined_audio.writeframes(zero_frames.tobytes())   # add 5 seconds of silence
        combined_audio.writeframes(english_audio_data)      # write the english audio 
        combined_audio.writeframes(zero_frames.tobytes())   # add 5 seconds of silence

        japanese_audio_wav.close()
        japanese_audio_wav.close()
        print(f"finished writing {item[0]}:{item[1]}")
        ix = ix + 1

    combined_audio.close()    

    # remove the temp_jap and temp_english files
    os.remove("temp_jap")
    os.remove("temp_english")

    # convert wav file to mp4
    sound = pd.AudioSegment.from_wav(f"wav/{ouput_file_name_without_extension}.wav")
    sound.export(f"audio/{ouput_file_name_without_extension}.mp4", format="mp4")
    print(f"finished generating mp4 file - mp4/{ouput_file_name_without_extension}.mp4")

if __name__ == "__main__":
    main()