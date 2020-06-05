#Auto Stream Recording Twitch v1.5.0 https://github.com/EnterGin/Auto-Stream-Recording-Twitch

# Please install latest development build of streamlink for proper work of the script
# https://github.com/streamlink/streamlink/actions?query=event%3Aschedule+is%3Asuccess+branch%3Amaster

import requests
import os
import time
import json
import sys
import subprocess
import datetime
from datetime import timedelta
import getopt
import pytz

class TwitchRecorder:
    def __init__(self):
        # global configuration
        self.client_id          = "kimne78kx3ncx6brgo4mv6wki5h1ko" # Don't change this
        self.ffmpeg_path        = r"D:\\twitch"                    # path to ffmpeg.exe
        self.refresh            = 1.0                              # Time between checking (1.0 is recommended)
        self.root_path          = r"D:\\twitch"                    # path to recorded and processed streams
        self.timezoneName       = 'Europe/Moscow'                  # name of timezone (list of timezones: https://stackoverflow.com/questions/13866926/is-there-a-list-of-pytz-timezones)
        self.chatdownload       = 1                                # 0 - disable chat downloading, 1 - enable chat downloading
        self.cmdstate           = 2                                # 0 - not minimazed cmd close after processing, 1 - minimazed cmd close after processing, 2 - minimazed cmd don't close after processing
        self.downloadVOD        = 0                                # 0 - disable VOD downloading after stream's ending, 1 - enable VOD downloading after stream's ending
        self.rerun_delete       = 1                                # 0 - disable rerun deleting, 1 - enable rerun deleting
        self.dont_ask_to_delete = 0                                # 0 - always ask to delete previous processed streams from recorded folder, 1 - don't ask, don't delete, 2 - don't ask, delete
        self.make_stream_folder = 1                                # 0 - don't make folders for each processed stream, 1 - make folders for each processed stream
        self.short_folder       = 0                                # 0 - only date in processed VOD folder, 1 - date, title, game and username in processed VOD folder
        self.hls_segments       = 3                                # 1-10 for live stream, it's possible to use multiple threads to potentially increase the throughput. 2-3 is enough
        self.hls_segmentsVOD    = 10                               # 1-10 for downloading vod, it's possible to use multiple threads to potentially increase the throughput
        self.streamlink_debug   = 0                                # 0 - don't show streamlink debug, 1 - show streamlink debug

        # user configuration
        self.username = "gamesdonequick"
        self.quality  = "best"

    def run(self):
        # cmdstatecommand
        if self.cmdstate == 2:
            self.cmdstatecommand = "/min cmd.exe /k".split()
        elif self.cmdstate == 1:
            self.cmdstatecommand = "/min".split()
        else:
            self.cmdstatecommand = "".split()

        # self.timezoneName to number
        self.timezone = pytz.timezone(self.timezoneName).localize(datetime.datetime.now()).tzinfo._utcoffset.seconds/60/60

        # -v check
        if str(self.downloadVOD).isdigit() == False:
            print('-v can be only 0 or 1. Set to 0.\n')
            self.downloadVOD = 0
        else:
            self.downloadVOD = int(self.downloadVOD)

        # deleting previous processed streams from recorded folder
        if self.dont_ask_to_delete == 0:
            print('Do you want to delete previous processed streams from recorded folder? y/n')
            delete_recorded_ans = str(input())
        elif self.dont_ask_to_delete == 2:
            delete_recorded_ans = 'y'
        else:
            delete_recorded_ans = 'n'

        if delete_recorded_ans == 'y' or delete_recorded_ans == 'Y':
            self.cleanrecorded = 1
        else:
            self.cleanrecorded = 0

        # streamlink debug
        if self.streamlink_debug == 1:
            self.debug_cmd = "--loglevel trace".split()
        else:
            self.debug_cmd = "".split()
            
        # get user id
        url    = 'https://api.twitch.tv/kraken/users?login=' + self.username
        try:
            r = requests.get(url, headers = {"Accept" : "application/vnd.twitchtv.v5+json","Client-ID" : self.client_id}, timeout = 15)
            r.raise_for_status()
            info = r.json()
            if info["_total"] > 0:
                self.channel_id     = info["users"][0]["_id"]
                self.user_not_found = 0
            else:
                self.user_not_found = 1
        except requests.exceptions.RequestException as e:
            print(f'\n{e}\n')

        # start text
        print('Auto Stream Recording Twitch v1.5.0')
        print('Configuration:')
        print('Root path: ' + self.root_path)
        print('Ffmpeg path: ' + self.ffmpeg_path)
        print('Timezone: ' + self.timezoneName + ' ' + '(' + str(self.timezone) + ')')
        if self.chatdownload == 1:
            print('Chat downloading Enabled')
        else:
            print('Chat downloading Disabled')
        if self.downloadVOD == 1:
            print('VOD downloading Enabled')
        else:
            print('VOD downloading Disabled')

        # path to recorded stream
        self.recorded_path = os.path.join(self.root_path, "recorded", self.username)

        # path to finished video, errors removed
        self.processed_path = os.path.join(self.root_path, "processed", self.username)

        # create directory for recordedPath and processedPath if not exist
        if(os.path.isdir(self.recorded_path) is False):
            os.makedirs(self.recorded_path)
        if(os.path.isdir(self.processed_path) is False):
            os.makedirs(self.processed_path)

        # make sure the interval to check user availability is not less than 1 seconds
        if(self.refresh < 1):
            print("Check interval should not be lower than 1 seconds.")
            self.refresh = 1
            print("System set check interval to 1 seconds.")

        # Checking for previous files
        try:
            video_list = [f for f in os.listdir(self.recorded_path) if os.path.isfile(os.path.join(self.recorded_path, f))]
            if(len(video_list) > 0):
                print('Fixing previously recorded files.')
            for f in video_list:
                too_long_path = 0
                if f[0] == 'V':
                    recorded_filename = os.path.join(self.recorded_path, f)
                    if self.short_folder == 1:
                        dirname = f[4:12]
                        dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                    else:
                        dirname = f[4:12] + f[30:-4]
                        dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                    if self.make_stream_folder == 1:
                        stream_dir_path = self.processed_path + '/' + dirname
                    else:
                        stream_dir_path = self.processed_path

                    if len(os.path.join(stream_dir_path, f)) >= 260:
                        long_title_window = "cmd.exe /c start".split()
                        subprocess.call(long_title_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Stream will not be processed, please check root path.'])
                        too_long_path = 1

                    if(os.path.isdir(stream_dir_path) is False and too_long_path == 0):
                        os.makedirs(stream_dir_path)
                        print('Fixing ' + recorded_filename + '.')
                        try:
                            os.chdir(self.ffmpeg_path)
                            processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                            subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                        except Exception as e:
                            print(e)
                    elif(os.path.exists(os.path.join(stream_dir_path, f)) is False and too_long_path == 0):
                        print('Fixing ' + recorded_filename + '.')
                        processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                        subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                    elif self.cleanrecorded == 1:
                        print('Deleting ' + recorded_filename + '.')
                        os.remove(recorded_filename)
                elif f[11] == 'h':
                    recorded_filename = os.path.join(self.recorded_path, f)
                    if self.short_folder == 1:
                        dirname = f[:8]
                        dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                    else:
                        dirname = f[:9] + f[19:-4]
                        dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                    
                    if self.make_stream_folder == 1:
                        stream_dir_path = self.processed_path + '/' + dirname
                    else:
                        stream_dir_path = self.processed_path

                    if len(os.path.join(stream_dir_path, f)) >= 260:
                        long_title_window = "cmd.exe /c start".split()
                        subprocess.call(long_title_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Stream will not be processed, please check root path.'])
                        too_long_path = 1

                    if(os.path.isdir(stream_dir_path) is False and too_long_path == 0):
                        os.makedirs(stream_dir_path)
                        print('Fixing ' + recorded_filename + '.')
                        try:
                            os.chdir(self.ffmpeg_path)
                            processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                            subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                        except Exception as e:
                            print(e)
                    elif(os.path.exists(os.path.join(stream_dir_path,f)) is False and too_long_path == 0):
                        print('Fixing ' + recorded_filename + '.')
                        processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                        subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                    elif self.cleanrecorded == 1:
                        print('Deleting ' + recorded_filename + '.')
                        os.remove(recorded_filename)                        
                else:
                    recorded_filename = os.path.join(self.recorded_path, f)
                    if self.short_folder == 1:
                        dirname = f[:8]
                        dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                    else:
                        dirname = f[:8] + f[26:-4]
                        dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                        
                    if self.make_stream_folder == 1:
                        stream_dir_path = self.processed_path + '/' + dirname
                    else:
                        stream_dir_path = self.processed_path
                        
                    if len(os.path.join(stream_dir_path, f)) >= 260:
                        long_title_window = "cmd.exe /c start".split()
                        subprocess.call(long_title_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Stream will not be processed, please check root path.'])
                        too_long_path = 1    

                    if(os.path.isdir(stream_dir_path) is False and too_long_path == 0):
                        os.makedirs(stream_dir_path)
                        print('Fixing ' + recorded_filename + '.')
                        try:
                            os.chdir(self.ffmpeg_path)
                            processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                            subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                        except Exception as e:
                            print(e)
                    elif(os.path.exists(os.path.join(stream_dir_path, f)) is False and too_long_path == 0):
                        print('Fixing ' + recorded_filename + '.')
                        processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                        subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                    elif self.cleanrecorded == 1:
                        print('Deleting ' + recorded_filename + '.')
                        os.remove(recorded_filename)
        except Exception as e:
            print(e)

        print("Checking for", self.username, "every", self.refresh, "seconds. Record with", self.quality, "quality.")
        self.loopcheck()

    def check_user(self):
        # 0: online, 
        # 1: not found, 
        # 2: error
        
        info   = None
        if self.user_not_found != 1:
            url    = 'https://api.twitch.tv/kraken/channels/' + str(self.channel_id)
            status = 2
            try:
                r = requests.get(url, headers = {"Accept" : "application/vnd.twitchtv.v5+json","Client-ID" : self.client_id}, timeout = 15)
                r.raise_for_status()
                info   = r.json()
                status = 0
            except requests.exceptions.RequestException as e:
                print(f'\n{e}\n')
        else:
            status = 1

        return status, info

    def loopcheck(self):
        while True:
            rerun  = 0
            uncrop = 0
            status, info = self.check_user()
            if status == 1:
                print("Username not found. Invalid username or typo.")
                time.sleep(self.refresh)
            elif status == 2:
                print(datetime.datetime.now().strftime("%Hh%Mm%Ss")," ","unexpected error. Try to check internet connection or client-id. Will try again in", self.refresh, "seconds.")
                time.sleep(self.refresh)
            elif status == 0:
                stream_title = str(info['status'])
                stream_title = "".join(x for x in stream_title if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                present_date     = datetime.datetime.now().strftime("%Y%m%d")
                present_datetime = datetime.datetime.now().strftime("%Y%m%d_%Hh%Mm%Ss")

                filename = present_datetime + "_" + stream_title + '_' + str(info['game']) + "_" + self.username + ".mp4"

                # clean filename from unecessary characters
                filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                recorded_filename = os.path.join(self.recorded_path, filename)

                # length check
                if len(recorded_filename) >= 260:
                    difference = len(stream_title) - len(recorded_filename) + 250
                    if difference < 0:
                        uncrop = 1
                    else:
                        stream_title      = stream_title[:difference]
                        filename          = present_datetime + "_" + stream_title + '_' + str(info['game']) + "_" + self.username + ".mp4"
                        filename          = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                        recorded_filename = os.path.join(self.recorded_path, filename)

                # start streamlink process
                subprocess.call(["streamlink", "--hls-segment-threads", str(self.hls_segments), "--twitch-disable-hosting", "twitch.tv/" + self.username, self.quality, "--retry-streams", str(self.refresh)] + self.debug_cmd + ["-o", recorded_filename])

                if(os.path.exists(recorded_filename) is True):
                    status, info = self.check_user()
                    if str(info['broadcaster_software']) == 'watch_party_rerun':
                        if self.rerun_delete == 1:
                            os.remove(recorded_filename)
                            rerun_message = 'be deleted. '
                        else:
                            filename = filename[:19] + self.username + "_" + 'RERUN' + ".mp4"
                            try:
                                os.rename(recorded_filename,os.path.join(self.recorded_path, filename))
                                recorded_filename = os.path.join(self.recorded_path, filename)
                            except Exception as e:
                                print(e)
                            rerun_message = 'not be processed. '
                        rerun_window = "cmd.exe /c start".split()
                        subprocess.call(rerun_window + ['echo', 'Rerun detected. Recorded file will ' + rerun_message + 'Please check streams to ensure that it was not a live stream.'])
                        print('Rerun detected. Recorded file will ' + rerun_message + 'Please check streams to ensure that it was not a live stream.')
                        rerun = 1
                    if(os.path.exists(recorded_filename) is True and rerun == 0):
                        try:
                            vodurl      = 'https://api.twitch.tv/kraken/channels/' + str(self.channel_id) + '/videos?broadcast_type=archive'
                            vods        = requests.get(vodurl, headers = {"Accept" : 'application/vnd.twitchtv.v5+json', "Client-ID" : self.client_id}, timeout = 5)
                            vodsinfodic = json.loads(vods.text)

                            if vodsinfodic["_total"] > 0:
                                vod_id = vodsinfodic["videos"][0]["_id"]
                                vod_id = vod_id[1:]

                                stream_title = str(vodsinfodic["videos"][0]["title"])
                                stream_title = "".join(x for x in stream_title if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                created_at = vodsinfodic["videos"][0]["created_at"]

                                vod_year   = int(created_at[:4])
                                vod_month  = int(created_at[5:7])
                                vod_day    = int(created_at[8:10])
                                vod_hour   = int(created_at[11:13])
                                vod_minute = int(created_at[14:16])

                                vod_date    = datetime.datetime(vod_year, vod_month, vod_day, vod_hour, vod_minute)
                                vod_date_tz = vod_date + timedelta(hours=self.timezone)   

                                if self.short_folder == 1:
                                    processed_stream_folder = vod_date_tz.strftime("%Y%m%d")
                                else:
                                    processed_stream_folder = vod_date_tz.strftime("%Y%m%d") + "_" + stream_title + '_' + vodsinfodic["videos"][0]["game"] + '_' + self.username
                                    processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                                
                                if self.make_stream_folder == 1:
                                    processed_stream_path = self.processed_path + "/" + processed_stream_folder
                                else:
                                    processed_stream_path = self.processed_path

                                filename = vod_date_tz.strftime("%Y%m%d_(%H-%M)") + "_" + vod_id + "_" + stream_title + '_' + vodsinfodic["videos"][0]["game"] + '_' + self.username + ".mp4"
                                filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                if len(os.path.join(self.recorded_path, filename)) >= 260:
                                    long_title_window = "cmd.exe /c start".split()

                                    difference = len(stream_title) - len(os.path.join(self.recorded_path, filename)) + 250
                                    if difference < 0:
                                        subprocess.call(long_title_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.'])
                                        uncrop = 1
                                    else:
                                        stream_title = stream_title[:difference]

                                        filename = vod_date_tz.strftime("%Y%m%d_(%H-%M)") + "_" + vod_id + "_" + stream_title + '_' + vodsinfodic["videos"][0]["game"] + '_' + self.username + ".mp4"
                                        filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                                        subprocess.call(long_title_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title will be cropped, please check root path.'])

                                if len(os.path.join(processed_stream_path, filename)) >= 260:
                                    long_title_window = "cmd.exe /c start".split()

                                    if self.short_folder == 1 or self.make_stream_folder == 0:
                                        difference = len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 250
                                    else:
                                        difference = int((2*len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 250)/2)

                                    if difference < 0:
                                        subprocess.call(long_title_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.'])
                                        uncrop = 1
                                    else:
                                        stream_title = stream_title[:difference]

                                        filename = vod_date_tz.strftime("%Y%m%d_(%H-%M)") + "_" + vod_id + "_" + stream_title + '_' + vodsinfodic["videos"][0]["game"] + '_' + self.username + ".mp4"
                                        filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                        if self.short_folder == 1:
                                            processed_stream_folder = vod_date_tz.strftime("%Y%m%d")
                                        else:
                                            processed_stream_folder = vod_date_tz.strftime("%Y%m%d") + "_" + stream_title + '_' + vodsinfodic["videos"][0]["game"] + '_' + self.username
                                            processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                        if self.make_stream_folder == 1:
                                            processed_stream_path = self.processed_path + "/" + processed_stream_folder
                                        else:
                                            processed_stream_path = self.processed_path
                                        subprocess.call(long_title_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title will be cropped, please check root path.'])

                                if(os.path.isdir(processed_stream_path) is False):
                                    os.makedirs(processed_stream_path)

                                filenameError = 0

                                try:
                                    os.rename(recorded_filename,os.path.join(self.recorded_path, filename))
                                    recorded_filename  = os.path.join(self.recorded_path, filename)
                                    processed_filename = os.path.join(processed_stream_path, filename)
                                except Exception as e:
                                    stream_title = str(info['status'])
                                    stream_title = "".join(x for x in stream_title if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                    filename = present_datetime + "_" + stream_title + '_' + str(info['game']) + "_" + self.username + ".mp4"
                                    filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                    if self.short_folder == 1:
                                        processed_stream_folder = present_date
                                        processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                                    else:
                                        processed_stream_folder = present_date + "_" + stream_title + '_' + str(info['game']) + "_" + self.username
                                        processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                    if self.make_stream_folder == 1:
                                        processed_stream_path = self.processed_path + "/" + processed_stream_folder
                                    else:
                                        processed_stream_path = self.processed_path

                                    if len(os.path.join(processed_stream_path, filename)) >= 260:
                                        long_title_window = "cmd.exe /c start".split()

                                        if self.short_folder == 1 or self.make_stream_folder == 0:
                                            difference = len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242
                                        else:
                                            difference = int((2*len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242)/2)

                                        if difference < 0:
                                            subprocess.call(long_title_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.'])
                                            uncrop = 1
                                        else:
                                            stream_title = stream_title[:difference]

                                            filename = present_datetime + "_" + stream_title + '_' + str(info['game']) + "_" + self.username + ".mp4"
                                            filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                            if self.short_folder == 1:
                                                processed_stream_folder = present_date
                                            else:
                                                processed_stream_folder = present_date + "_" + stream_title + '_' + str(info['game']) + "_" + self.username
                                                processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                                            
                                            if self.make_stream_folder == 1:
                                                processed_stream_path = self.processed_path + "/" + processed_stream_folder
                                            else:
                                                processed_stream_path = self.processed_path

                                    os.rename(recorded_filename,os.path.join(self.recorded_path, filename))
                                    recorded_filename  = os.path.join(self.recorded_path, filename)
                                    processed_filename = os.path.join(processed_stream_path, filename)
                                    if(os.path.isdir(processed_stream_path) is False):
                                        os.makedirs(processed_stream_path)
                                    filenameError = 1
                                    print(e)
                                    error_window = "cmd.exe /c start".split()
                                    subprocess.call(error_window + ['echo', 'An error has occurred. VOD and chat will not be downloaded. Please check them manually.'])
                                    print('An error has occurred. VOD and chat will not be downloaded. Please check them manually.')

                                if self.chatdownload == 1 and filenameError == 0:
                                    subtitles_window = "cmd.exe /c start".split() + self.cmdstatecommand
                                    subprocess.call(subtitles_window + ["tcd", "-v", vod_id, "--timezone", self.timezoneName, "-f", "irc,ssa,json", "-o", processed_stream_path])

                                if self.downloadVOD == 1 and filenameError == 0:
                                    vod_filename = "VOD_" + filename
                                    vod_window   = "cmd.exe /c start".split() + self.cmdstatecommand
                                    subprocess.call(vod_window + ["streamlink", "--hls-segment-threads", str(self.hls_segmentsVOD), "twitch.tv/videos/" + vod_id, self.quality] + self.debug_cmd + ["-o", os.path.join(self.recorded_path,vod_filename)])
                            else:
                                stream_title = str(info['status'])
                                stream_title = "".join(x for x in stream_title if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                                
                                filename = present_datetime + "_" + stream_title + '_' + str(info['game']) + "_" + self.username + ".mp4"
                                filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                                
                                if self.short_folder == 1:
                                    processed_stream_folder = present_date
                                else:
                                    processed_stream_folder = present_date + "_" + stream_title + '_' + str(info['game']) + "_" + self.username
                                    processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                                
                                if self.make_stream_folder == 1:
                                    processed_stream_path = self.processed_path + "/" + processed_stream_folder
                                else:
                                    processed_stream_path = self.processed_path
                                
                                if len(os.path.join(processed_stream_path, filename)) >= 260:
                                    long_title_window = "cmd.exe /c start".split()

                                    if self.short_folder == 1 or self.make_stream_folder == 0:
                                        difference = len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242
                                    else:
                                        difference = int((2*len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242)/2)

                                    if difference < 0:
                                        subprocess.call(long_title_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.'])
                                        uncrop = 1
                                    else:
                                        stream_title = stream_title[:difference]

                                        filename = present_datetime + "_" + stream_title + '_' + str(info['game']) + "_" + self.username + ".mp4"
                                        filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                        if self.short_folder == 1:
                                            processed_stream_folder = present_date
                                        else:
                                            processed_stream_folder = present_date + "_" + stream_title + '_' + str(info['game']) + "_" + self.username
                                            processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                        if self.make_stream_folder == 1:
                                            processed_stream_path = self.processed_path + "/" + processed_stream_folder
                                        else:
                                            processed_stream_path = self.processed_path

                                if(os.path.isdir(processed_stream_path) is False):
                                        os.makedirs(processed_stream_path)

                                os.rename(recorded_filename,os.path.join(self.recorded_path, filename))        
                                recorded_filename  = os.path.join(self.recorded_path, filename)
                                processed_filename = os.path.join(processed_stream_path, filename)

                        except Exception as e:
                            stream_title = str(info['status'])
                            stream_title = "".join(x for x in stream_title if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                            filename = present_datetime + "_" + stream_title + '_' + str(info['game']) + "_" + self.username + ".mp4"
                            filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                            if self.short_folder == 1:
                                processed_stream_folder = present_date
                            else:
                                processed_stream_folder = present_date + "_" + stream_title + '_' + str(info['game']) + "_" + self.username
                                processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                            if self.make_stream_folder == 1:
                                processed_stream_path = self.processed_path + "/" + processed_stream_folder
                            else:
                                processed_stream_path = self.processed_path

                            if len(os.path.join(processed_stream_path, filename)) >= 260:
                                long_title_window = "cmd.exe /c start".split()

                                if self.short_folder == 1 or self.make_stream_folder == 0:
                                    difference = len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242
                                else:
                                    difference = int((2*len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242)/2)

                                if difference < 0:
                                    subprocess.call(long_title_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.'])
                                    uncrop = 1
                                else:
                                    stream_title = stream_title[:difference]

                                    filename = present_datetime + "_" + stream_title + '_' + str(info['game']) + "_" + self.username + ".mp4"
                                    filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                    if self.short_folder == 1:
                                        processed_stream_folder = present_date
                                    else:
                                        processed_stream_folder = present_date + "_" + stream_title + '_' + str(info['game']) + "_" + self.username
                                        processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                                    
                                    if self.make_stream_folder == 1:
                                        processed_stream_path = self.processed_path + "/" + processed_stream_folder
                                    else:
                                        processed_stream_path = self.processed_path

                            if(os.path.isdir(processed_stream_path) is False):
                                    os.makedirs(processed_stream_path)

                            os.rename(recorded_filename,os.path.join(self.recorded_path, filename))        
                            recorded_filename  = os.path.join(self.recorded_path, filename)
                            processed_filename = os.path.join(processed_stream_path, filename)

                            print(e)
                            error_window = "cmd.exe /c start".split()
                            subprocess.call(error_window + ['echo', 'An error has occurred. VOD and chat will not be downloaded. Please check them manually.'])
                            print('An error has occurred. VOD and chat will not be downloaded. Please check them manually.')

                print("Recording stream is done. Fixing video file.")
                if(os.path.exists(recorded_filename) is True and rerun == 0 and uncrop == 0):
                    try:
                        os.chdir(self.ffmpeg_path)
                        processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                        subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(processed_stream_path,filename)])
                    except Exception as e:
                        print(e)
                elif rerun == 1:
                    print("Skip fixing. File is marked as a rerun.")
                else:
                    print("Skip fixing. File not found.")

                print("Fixing is done. Going back to checking..")
                time.sleep(self.refresh)

def main(argv):
    twitch_recorder = TwitchRecorder()
    usage_message = 'Auto_Recording_Twitch.py -u <username> -q <quality> -v <download VOD 1/0>'
    try:
        opts, args = getopt.getopt(argv,"hu:q:v:",["username=","quality=", "vod="])
    except getopt.GetoptError:
        print (usage_message)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(usage_message)
            sys.exit()
        elif opt in ("-u", "--username"):
            twitch_recorder.username = arg
        elif opt in ("-q", "--quality"):
            twitch_recorder.quality = arg
        elif opt in ("-v", "--vod"):
            twitch_recorder.downloadVOD = arg

    twitch_recorder.run()

if __name__ == "__main__":
    main(sys.argv[1:])
