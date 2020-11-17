# Auto Stream Recording Twitch v1.6.8 https://github.com/EnterGin/Auto-Stream-Recording-Twitch

# Please install latest streamlink release for proper work of the script
# https://github.com/streamlink/streamlink/releases

import requests
import os
import time
import json
import sys
import platform
import subprocess
import datetime
import getopt
import pytz

class TwitchRecorder:
    def __init__(self):
        # global configuration
        self.client_id          = ""                               # If you don't have client id then register new app: https://dev.twitch.tv/console/apps
        self.client_secret      = ""                               # Manage application -> new secret
        self.ffmpeg_path        = r"D:\\twitch"                    # Path to ffmpeg.exe. Leave blank if Linux or ffmpeg in env PATH
        self.refresh            = 1.0                              # Time between checking (1.0 is recommended)
        self.root_path          = r"D:\\twitch"                    # Path to recorded and processed streams
        self.timezoneName       = 'Europe/Moscow'                  # Name of timezone (list of timezones: https://stackoverflow.com/questions/13866926/is-there-a-list-of-pytz-timezones)
        self.chatdownload       = 1                                # 0 - disable chat downloading, 1 - enable chat downloading
        self.cmdstate           = 2                                # Windows: 0 - not minimazed cmd close after processing, 1 - minimazed cmd close after processing, 2 - minimazed cmd don't close after processing, 3 - no terminal, do in background
                                                                   # Linux:   0 - not minimazed terminal close after processing, 1 - not minimazed terminal don't close after processing, 2 - no terminal, do in background
        self.downloadVOD        = 0                                # 0 - disable VOD downloading after stream's ending, 1 - enable VOD downloading after stream's ending
        self.dont_ask_to_delete = 0                                # 0 - always ask to delete previous processed streams from recorded folder, 1 - don't ask, don't delete, 2 - don't ask, delete
        self.make_stream_folder = 1                                # 0 - don't make folders for each processed stream, 1 - make folders for each processed stream
        self.short_folder       = 0                                # 0 - date, title, game and username in processed VOD folder, 1 - only date in processed VOD folder
        self.hls_segments       = 3                                # 1-10 for live stream, it's possible to use multiple threads to potentially increase the throughput. 2-3 is enough
        self.hls_segmentsVOD    = 10                               # 1-10 for downloading vod, it's possible to use multiple threads to potentially increase the throughput
        self.streamlink_debug   = 0                                # 0 - don't show streamlink debug, 1 - show streamlink debug
        self.warning_windows    = 1                                # 0 - don't show warning windows (warnings will only be printed in terminal), 1 - show warning windows

        # user configuration
        self.username = "gamesdonequick"
        self.quality  = "best"

    def run(self):
        # detect os
        if sys.platform.startswith('win32'):
            self.osCheck = 0
        elif sys.platform.startswith('linux'):
            self.osCheck = 1
            if self.cmdstate == 3:
                self.cmdstate = 2
        else:
            print('Your OS might not be supported.\n')
            return

        # cmdstatecommand
        if self.osCheck == 0:
            if self.cmdstate == 2:
                self.cmdstatecommand = "/min cmd.exe /k".split()
            elif self.cmdstate == 1:
                self.cmdstatecommand = "/min".split()
            else:
                self.cmdstatecommand = "".split()
            self.main_cmd_window = "cmd.exe /c start".split()
        else:
            if self.cmdstate == 1:
                self.linuxstatecomma = "; exec bash'"
            elif self.cmdstate == 0:
                self.linuxstatecomma = "'"
            self.main_cmd_window = "gnome-terminal --".split()

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

        if self.client_id == "" or self.client_secret == "":
            print("If you don't have client-id then register new app on following page:")
            print("https://dev.twitch.tv/console/apps")
            print("You have to set both client-id and client-secret.")
            return

        # start text
        print('Auto Stream Recording Twitch v1.6.8')
        print('Configuration:')
        print('OS: ' + "Windows " + platform.release() if self.osCheck == 0 else 'OS: ' + "Linux " + platform.release())
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

        # get oauth token
        self.oauth_token = self.get_oauth_token()

        # get user id
        self.get_channel_id()

        # path to recorded stream
        self.recorded_path = os.path.join(self.root_path, "recorded", self.username)

        # path to finished video, errors removed
        self.processed_path = os.path.join(self.root_path, "processed", self.username)

        # create directory for recordedPath and processedPath if not exist
        if(os.path.isdir(self.recorded_path) is False):
            os.makedirs(self.recorded_path)
        if(os.path.isdir(self.processed_path) is False):
            os.makedirs(self.processed_path)

        # make sure the interval to check user availability is not less than 1 second
        if(self.refresh < 1):
            print("Check interval should not be lower than 1 second.")
            self.refresh = 1
            print("System set check interval to 1 second.")

        # Checking for previous files
        try:
            video_list = [f for f in os.listdir(self.recorded_path) if os.path.isfile(os.path.join(self.recorded_path, f))]
            if(len(video_list) > 0):
                print('Fixing previously recorded files.')
            for f in video_list:
                too_long_path = 0
                if f[0] == 'V':
                    shorta = 4
                    shortb = 12
                    longc  = 30
                elif f[11] == 'h':
                    shorta = None
                    shortb = 8
                    longc  = 18
                else:
                    shorta = None
                    shortb = 8
                    longc  = 26
                longa  = shorta
                longb  = shortb
                recorded_filename = os.path.join(self.recorded_path, f)
                if self.short_folder == 1:
                    dirname = f[shorta:shortb]
                    dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                else:
                    dirname = f[longa:longb] + f[longc:-4]
                    dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                if self.make_stream_folder == 1:
                    stream_dir_path = self.processed_path + '/' + dirname
                else:
                    stream_dir_path = self.processed_path

                if len(os.path.join(stream_dir_path, f)) >= 260:
                    if self.warning_windows == 1:
                        if self.osCheck == 0:
                            subprocess.call(self.main_cmd_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Stream will not be processed, please check root path.'])
                        else:
                            subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'" + 'echo', '"Path to stream is too long. (Max path length is 259 symbols) Stream will not be processed, please check root path."; exec bash' + "'"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    print("Path to stream is too long. (Max path length is 259 symbols) Stream will not be processed, please check root path.")
                    too_long_path = 1

                if(os.path.isdir(stream_dir_path) is False and too_long_path == 0):
                    os.makedirs(stream_dir_path)
                    print('Fixing ' + recorded_filename + '.')
                    try:
                        if self.ffmpeg_path != "" and self.osCheck == 0:
                            os.chdir(self.ffmpeg_path)
                        if self.osCheck == 0:
                            processing_window = self.main_cmd_window + self.cmdstatecommand
                            if self.cmdstate == 3:
                                subprocess.Popen(['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path, f)], stdout=None, stderr=None)
                            else:
                                subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path, f)])
                        else:
                            if self.cmdstate == 2:
                                subprocess.Popen(['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path, f)], stdout=None, stderr=None)
                            else:
                                subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'ffmpeg", '-y', '-i', '"' + recorded_filename + '"', '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', '"' + os.path.join(stream_dir_path, f) + '"' + self.linuxstatecomma]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    except Exception as e:
                        print(e)
                elif(os.path.exists(os.path.join(stream_dir_path, f)) is False and too_long_path == 0):
                    print('Fixing ' + recorded_filename + '.')
                    try:
                        if self.ffmpeg_path != "" and self.osCheck == 0:
                            os.chdir(self.ffmpeg_path)
                        if self.osCheck == 0:
                            processing_window = self.main_cmd_window + self.cmdstatecommand
                            if self.cmdstate == 3:
                                subprocess.Popen(['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path, f)], stdout=None, stderr=None)
                            else:
                                subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path, f)])
                        else:
                            if self.cmdstate == 2:
                                subprocess.Popen(['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path, f)], stdout=None, stderr=None)
                            else:
                                subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'ffmpeg", '-y', '-i', '"' + recorded_filename + '"', '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', '"' + os.path.join(stream_dir_path, f) + '"' + self.linuxstatecomma]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    except Exception as e:
                        print(e)
                elif self.cleanrecorded == 1:
                    print('Deleting ' + recorded_filename + '.')
                    os.remove(recorded_filename)
        except Exception as e:
            print(e)

        print("Checking for", self.username, "every", self.refresh, "seconds. Record with", self.quality, "quality.")
        self.loopcheck()
    
    def get_oauth_token(self):
        try:
            return requests.post(f"https://id.twitch.tv/oauth2/token"
                                f"?client_id={self.client_id}"
                                f"&client_secret={self.client_secret}"
                                f"&grant_type=client_credentials").json()['access_token']
        except:
            return None

    def get_channel_id(self):
        self.getting_channel_id_error = 0
        self.user_not_found           = 0

        url = 'https://api.twitch.tv/helix/users?login=' + self.username
        try:
            r = requests.get(url, headers = {"Authorization" : "Bearer " + self.oauth_token, "Client-ID": self.client_id}, timeout = 15)
            r.raise_for_status()
            info = r.json()
            if info["data"] != []:
                self.channel_id = info["data"][0]["id"]
            else:
                self.user_not_found = 1
        except requests.exceptions.RequestException as e:
            self.getting_channel_id_error = 1
            print(f'\n{e}\n')

    def check_user(self):
        # 0: online,
        # 1: not found,
        # 2: error,
        # 3: channel id error

        info = None
        if self.user_not_found != 1 and self.getting_channel_id_error != 1:
            url    = 'https://api.twitch.tv/helix/channels?broadcaster_id=' + str(self.channel_id)
            status = 2
            try:
                r = requests.get(url, headers = {"Authorization" : "Bearer " + self.oauth_token, "Client-ID": self.client_id}, timeout = 15)
                r.raise_for_status()

                info   = r.json()
                status = 0
            except requests.exceptions.RequestException as e:
                if r.status_code == 401:
                    print(
                        'Request to Twitch returned an error %s, trying to get new oauth_token...'
                        % (r.status_code)
                    )
                    self.getting_channel_id_error = 1
                else:
                    print(
                        'Request to Twitch returned an error %s, the response is:\n%s'
                        % (r.status_code, r.text)
                    )
        elif self.user_not_found == 1:
            status = 1
        else:
            self.oauth_token = self.get_oauth_token()
            self.get_channel_id()
            status = 3

        return status, info

    def loopcheck(self):
        while True:
            uncrop = 0
            status, info = self.check_user()
            if status == 1:
                print("Username not found. Invalid username or typo.")
                time.sleep(self.refresh)
            elif status == 2:
                print(datetime.datetime.now().strftime("%Hh%Mm%Ss")," ","Unexpected error. Try to check internet connection or client-id. Will try again in", self.refresh, "seconds.")
                time.sleep(self.refresh)
            elif status == 3:
                print(datetime.datetime.now().strftime("%Hh%Mm%Ss")," ","Error with channel id or oauth token. Try to check internet connection or client-id and client-secret. Will try again in", self.refresh, "seconds.")
                time.sleep(self.refresh)
            elif status == 0:
                stream_title = str(info["data"][0]['title'])
                stream_title = "".join(x for x in stream_title if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                present_date     = datetime.datetime.now().strftime("%Y%m%d")
                present_datetime = datetime.datetime.now().strftime("%Y%m%d_%Hh%Mm%Ss")

                filename = present_datetime + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username + ".mp4"

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
                        filename          = present_datetime + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username + ".mp4"
                        filename          = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                        recorded_filename = os.path.join(self.recorded_path, filename)

                # start streamlink process
                subprocess.call(["streamlink", "--hls-segment-threads", str(self.hls_segments), "--twitch-disable-hosting", "twitch.tv/" + self.username, self.quality, "--retry-streams", str(self.refresh)] + self.debug_cmd + ["-o", recorded_filename])

                if(os.path.exists(recorded_filename) is True):
                    status, info = self.check_user()
                    try:
                        vodurl      = 'https://api.twitch.tv/helix/videos?user_id=' + str(self.channel_id) + '&type=archive'
                        vods        = requests.get(vodurl, headers = {"Authorization" : "Bearer " + self.oauth_token, "Client-ID": self.client_id}, timeout = 5)
                        vodsinfodic = json.loads(vods.text)

                        if vodsinfodic["data"] != []:
                            vod_id = vodsinfodic["data"][0]["id"]

                            stream_title = str(vodsinfodic["data"][0]["title"])
                            stream_title = "".join(x for x in stream_title if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                            created_at = vodsinfodic["data"][0]["created_at"]

                            vod_year   = int(created_at[:4])
                            vod_month  = int(created_at[5:7])
                            vod_day    = int(created_at[8:10])
                            vod_hour   = int(created_at[11:13])
                            vod_minute = int(created_at[14:16])

                            vod_date    = datetime.datetime(vod_year, vod_month, vod_day, vod_hour, vod_minute)
                            vod_date_tz = vod_date + datetime.timedelta(hours=self.timezone)

                            if self.short_folder == 1:
                                processed_stream_folder = vod_date_tz.strftime("%Y%m%d")
                            else:
                                processed_stream_folder = vod_date_tz.strftime("%Y%m%d") + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + '_' + self.username
                                processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                            if self.make_stream_folder == 1:
                                processed_stream_path = self.processed_path + "/" + processed_stream_folder
                            else:
                                processed_stream_path = self.processed_path

                            filename = vod_date_tz.strftime("%Y%m%d_(%H-%M)") + "_" + vod_id + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + '_' + self.username + ".mp4"
                            filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                            if len(os.path.join(self.recorded_path, filename)) >= 260:
                                difference = len(stream_title) - len(os.path.join(self.recorded_path, filename)) + 250
                                if difference < 0:
                                    if self.warning_windows == 1:
                                        if self.osCheck == 0:
                                            subprocess.call(self.main_cmd_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.'])
                                        else:
                                            subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'" + 'echo', '"Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed."; exec bash' + "'"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    print("Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.")
                                    uncrop = 1
                                else:
                                    stream_title = stream_title[:difference]

                                    filename = vod_date_tz.strftime("%Y%m%d_(%H-%M)") + "_" + vod_id + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + '_' + self.username + ".mp4"
                                    filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                                    if self.warning_windows == 1:
                                        if self.osCheck == 0:
                                            subprocess.call(self.main_cmd_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title will be cropped, please check root path.'])
                                        else:
                                            subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'" + 'echo', '"Path to stream is too long. (Max path length is 259 symbols) Title will be cropped, please check root path."; exec bash' + "'"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    print("Path to stream is too long. (Max path length is 259 symbols) Title will be cropped, please check root path.")

                            if len(os.path.join(processed_stream_path, filename)) >= 260:
                                if self.short_folder == 1 or self.make_stream_folder == 0:
                                    difference = len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 250
                                else:
                                    difference = int((2*len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 250)/2)

                                if difference < 0:
                                    if self.warning_windows == 1:
                                        if self.osCheck == 0:
                                            subprocess.call(self.main_cmd_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.'])
                                        else:
                                            subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'" + 'echo', '"Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed."; exec bash' + "'"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    print("Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.")
                                    uncrop = 1
                                else:
                                    stream_title = stream_title[:difference]

                                    filename = vod_date_tz.strftime("%Y%m%d_(%H-%M)") + "_" + vod_id + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + '_' + self.username + ".mp4"
                                    filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                    if self.short_folder == 1:
                                        processed_stream_folder = vod_date_tz.strftime("%Y%m%d")
                                    else:
                                        processed_stream_folder = vod_date_tz.strftime("%Y%m%d") + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + '_' + self.username
                                        processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                    if self.make_stream_folder == 1:
                                        processed_stream_path = self.processed_path + "/" + processed_stream_folder
                                    else:
                                        processed_stream_path = self.processed_path
                                    if self.warning_windows == 1:
                                        if self.osCheck == 0:
                                            subprocess.call(self.main_cmd_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title will be cropped, please check root path.'])
                                        else:
                                            subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'" + 'echo', '"Path to stream is too long. (Max path length is 259 symbols) Title will be cropped, please check root path."; exec bash' + "'"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    print("Path to stream is too long. (Max path length is 259 symbols) Title will be cropped, please check root path.")

                            if(os.path.isdir(processed_stream_path) is False):
                                os.makedirs(processed_stream_path)

                            filenameError = 0

                            try:
                                os.rename(recorded_filename,os.path.join(self.recorded_path, filename))
                                recorded_filename  = os.path.join(self.recorded_path, filename)
                                processed_filename = os.path.join(processed_stream_path, filename)
                            except Exception as e:
                                stream_title = str(info["data"][0]['title'])
                                stream_title = "".join(x for x in stream_title if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                filename = present_datetime + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username + ".mp4"
                                filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                if self.short_folder == 1:
                                    processed_stream_folder = present_date
                                    processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                                else:
                                    processed_stream_folder = present_date + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username
                                    processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                if self.make_stream_folder == 1:
                                    processed_stream_path = self.processed_path + "/" + processed_stream_folder
                                else:
                                    processed_stream_path = self.processed_path

                                if len(os.path.join(processed_stream_path, filename)) >= 260:
                                    if self.short_folder == 1 or self.make_stream_folder == 0:
                                        difference = len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242
                                    else:
                                        difference = int((2*len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242)/2)

                                    if difference < 0:
                                        if self.warning_windows == 1:
                                            if self.osCheck == 0:
                                                subprocess.call(self.main_cmd_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.'])
                                            else:
                                                subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'" + 'echo', '"Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed."; exec bash' + "'"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                        print("Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.")
                                        uncrop = 1
                                    else:
                                        stream_title = stream_title[:difference]

                                        filename = present_datetime + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username + ".mp4"
                                        filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                        if self.short_folder == 1:
                                            processed_stream_folder = present_date
                                        else:
                                            processed_stream_folder = present_date + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username
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
                                if self.warning_windows == 1:
                                    if self.osCheck == 0:
                                        subprocess.call(self.main_cmd_window + ['echo', 'An error has occurred. VOD and chat will not be downloaded. Please check them manually.'])
                                    else:
                                        subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'" + 'echo', '"An error has occurred. VOD and chat will not be downloaded. Please check them manually."; exec bash' + "'"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                print('An error has occurred. VOD and chat will not be downloaded. Please check them manually.')

                            if self.chatdownload == 1 and filenameError == 0:
                                if self.osCheck == 0:
                                    subtitles_window = self.main_cmd_window + self.cmdstatecommand
                                    if self.cmdstate == 3:
                                        subprocess.Popen(['tcd', "-v", vod_id, "--timezone", self.timezoneName, "-f", "irc,ssa,json", "-o", processed_stream_path], stdout=None, stderr=None)
                                    else:
                                        subprocess.call(subtitles_window + ['tcd', "-v", vod_id, "--timezone", self.timezoneName, "-f", "irc,ssa,json", "-o", processed_stream_path])
                                else:
                                    if self.cmdstate == 2:
                                        subprocess.Popen(['tcd', "-v", vod_id, "--timezone", self.timezoneName, "-f", "irc,ssa,json", "-o", processed_stream_path], stdout=None, stderr=None)
                                    else:
                                        subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'tcd", "-v", vod_id, "--timezone", self.timezoneName, "-f", "irc,ssa,json", "-o", '"' + processed_stream_path + '"' + self.linuxstatecomma]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                            if self.downloadVOD == 1 and filenameError == 0:
                                vod_filename = "VOD_" + filename
                                if self.osCheck == 0:
                                    vod_window   = self.main_cmd_window + self.cmdstatecommand
                                    if self.cmdstate == 3:
                                        subprocess.Popen(['streamlink', "--hls-segment-threads", str(self.hls_segmentsVOD), "twitch.tv/videos/" + vod_id, self.quality] + self.debug_cmd + ["-o", os.path.join(self.recorded_path, vod_filename)], stdout=None, stderr=None)
                                    else:
                                        subprocess.call(vod_window + ['streamlink', "--hls-segment-threads", str(self.hls_segmentsVOD), "twitch.tv/videos/" + vod_id, self.quality] + self.debug_cmd + ["-o", os.path.join(self.recorded_path, vod_filename)])
                                else:
                                    if self.cmdstate == 2:
                                        subprocess.Popen(['streamlink', "--hls-segment-threads", str(self.hls_segmentsVOD), "twitch.tv/videos/" + vod_id, self.quality] + self.debug_cmd + ["-o", os.path.join(self.recorded_path, vod_filename)], stdout=None, stderr=None)
                                    else:
                                        subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'streamlink", "--hls-segment-threads", str(self.hls_segmentsVOD), "twitch.tv/videos/" + vod_id, self.quality] + self.debug_cmd + ["-o", '"' + os.path.join(self.recorded_path, vod_filename) + '"' + self.linuxstatecomma]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        else:
                            stream_title = str(info["data"][0]['title'])
                            stream_title = "".join(x for x in stream_title if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                            filename = present_datetime + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username + ".mp4"
                            filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                            if self.short_folder == 1:
                                processed_stream_folder = present_date
                            else:
                                processed_stream_folder = present_date + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username
                                processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                            if self.make_stream_folder == 1:
                                processed_stream_path = self.processed_path + "/" + processed_stream_folder
                            else:
                                processed_stream_path = self.processed_path

                            if len(os.path.join(processed_stream_path, filename)) >= 260:
                                if self.short_folder == 1 or self.make_stream_folder == 0:
                                    difference = len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242
                                else:
                                    difference = int((2*len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242)/2)

                                if difference < 0:
                                    if self.warning_windows == 1:
                                        if self.osCheck == 0:
                                            subprocess.call(self.main_cmd_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.'])
                                        else:
                                            subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'" + 'echo', '"Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed."; exec bash' + "'"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    print("Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.")
                                    uncrop = 1
                                else:
                                    stream_title = stream_title[:difference]

                                    filename = present_datetime + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username + ".mp4"
                                    filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                    if self.short_folder == 1:
                                        processed_stream_folder = present_date
                                    else:
                                        processed_stream_folder = present_date + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username
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
                        stream_title = str(info["data"][0]['title'])
                        stream_title = "".join(x for x in stream_title if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                        filename = present_datetime + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username + ".mp4"
                        filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                        if self.short_folder == 1:
                            processed_stream_folder = present_date
                        else:
                            processed_stream_folder = present_date + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username
                            processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                        if self.make_stream_folder == 1:
                            processed_stream_path = self.processed_path + "/" + processed_stream_folder
                        else:
                            processed_stream_path = self.processed_path

                        if len(os.path.join(processed_stream_path, filename)) >= 260:
                            if self.short_folder == 1 or self.make_stream_folder == 0:
                                difference = len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242
                            else:
                                difference = int((2*len(stream_title) - len(os.path.join(processed_stream_path, filename)) + 242)/2)

                            if difference < 0:
                                if self.warning_windows == 1:
                                    if self.osCheck == 0:
                                        subprocess.call(self.main_cmd_window + ['echo', 'Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.'])
                                    else:
                                        subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'" + 'echo', '"Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed."; exec bash' + "'"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                print("Path to stream is too long. (Max path length is 259 symbols) Title cannot be cropped, please check root path. Stream will not be processed.")
                                uncrop = 1
                            else:
                                stream_title = stream_title[:difference]

                                filename = present_datetime + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username + ".mp4"
                                filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])

                                if self.short_folder == 1:
                                    processed_stream_folder = present_date
                                else:
                                    processed_stream_folder = present_date + "_" + stream_title + '_' + str(info["data"][0]['game_name']) + "_" + self.username
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
                        if self.warning_windows == 1:
                            if self.osCheck == 0:
                                subprocess.call(self.main_cmd_window + ['echo', 'An error has occurred. VOD and chat will not be downloaded. Please check them manually.'])
                            else:
                                subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'" + 'echo', '"An error has occurred. VOD and chat will not be downloaded. Please check them manually."; exec bash' + "'"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        print('An error has occurred. VOD and chat will not be downloaded. Please check them manually.')

                print("Recording stream is done. Fixing video file.")
                if(os.path.exists(recorded_filename) is True and uncrop == 0):
                    try:
                        if self.ffmpeg_path != "" and self.osCheck == 0:
                            os.chdir(self.ffmpeg_path)
                        if self.osCheck == 0:
                            processing_window = self.main_cmd_window + self.cmdstatecommand
                            if self.cmdstate == 3:
                                subprocess.Popen(['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', processed_filename], stdout=None, stderr=None)
                            else:
                                subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', processed_filename])
                        else:
                            if self.cmdstate == 2:
                                subprocess.Popen(['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', processed_filename], stdout=None, stderr=None)
                            else:
                                subprocess.call(' '.join(self.main_cmd_window + ['bash', '-c', "'ffmpeg", '-y', '-i', '"' + recorded_filename + '"', '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', '"' + processed_filename + '"' + self.linuxstatecomma]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    except Exception as e:
                        print(e)
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
