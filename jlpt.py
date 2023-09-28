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

import google.cloud.texttospeech as tts

def main():
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="JLPT script.")

    csv_data = ""  # Initialize the CSV data variable

    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose Mode')
    parser.add_argument('-f', '--file',  nargs='+', help='Input filename')
    parser.add_argument('-c', '--csv', action='store_true', help='Enable csv generation')
    parser.add_argument('-a', '--audio', action='store_true', help='Enable audio generation')

    args = parser.parse_args()

    for input_filename in args.file:
    
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

        if args.verbose is True:
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

def generate_audio(result_list: list, ouput_file_name_without_extension: str): 
    japanese_voice = "ja-JP-Standard-A"
    english_voice = "en-US-News-K"

    japanese_language_code = "-".join(japanese_voice.split("-")[:2])
    english_language_code = "-".join(english_voice.split("-")[:2])

    pause_duration_seconds = 5

    print(f"Generating audio for {ouput_file_name_without_extension}")
    combined_audio = wave.open(f"wav/{ouput_file_name_without_extension}.wav", 'wb')
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
        count = count + 1

    combined_audio.close()    

    # remove the temp_jap and temp_english files
    os.remove("temp_jap")
    os.remove("temp_english")

    # convert wav file to mp4
    sound = pd.AudioSegment.from_wav(f"wav/{ouput_file_name_without_extension}.wav")
    sound.export(f"mp4/{ouput_file_name_without_extension}.mp4", format="mp4")
    printf(f"finished generating mp4 file - mp4/{ouput_file_name_without_extension}.mp4")

if __name__ == "__main__":
    main()