#Auto Stream Recording Twitch v1.2.1 https://github.com/EnterGin/Auto-Stream-Recording-Twitch

import requests
import os
import time
import json
import sys
import subprocess
import datetime
import getopt
import pytz

class TwitchRecorder:
    def __init__(self):
        
        # deleting previous processed streams from recorded folder
        print('Do you want to delete previous processed streams from recorded folder? y/n')
        delete_recorded_ans=str(input())
        if delete_recorded_ans == 'y' or delete_recorded_ans == 'Y':
            self.cleanrecorded = 1
        else:
            self.cleanrecorded = 0
            
        # global configuration
        self.client_id = "kimne78kx3ncx6brgo4mv6wki5h1ko" # Don't change this
        self.ffmpeg_path = r"D:\\twitch" # path to ffmpeg.exe
        self.refresh = 1.0 # Time between checking (1.0 is recommended)
        self.root_path = r"D:\\twitch" # path to recorded and processed streams
        self.timezoneName = 'Europe/Moscow' # name of timezone (list of timezones: https://stackoverflow.com/questions/13866926/is-there-a-list-of-pytz-timezones)
        self.chatdownload = 1 #0 - disable chat downloading, 1 - enable chat downloading
        self.cmdstate = 2 #0 - not minimazed cmd close after processing, 1 - minimazed cmd close after processing, 2 - minimazed cmd don't close after processing
        self.downloadVOD = 1 #0 - disable VOD downloading after stream's ending, 1 - enable VOD downloading after stream's ending
        
        
        # user configuration
        self.username = "gamesdonequick"
        self.quality = "best"
        
        # cmdstatecommand
        if self.cmdstate == 2:
            self.cmdstatecommand = "/min cmd.exe /k".split()
        elif self.cmdstate == 1:
            self.cmdstatecommand = "/min".split()
        else:
            self.cmdstatecommand = "".split()
        
        # start text
        print('Configuration:')
        print('Root path: ' + self.root_path)
        print('Ffmpeg path: ' + self.ffmpeg_path)
        self.timezone = int(pytz.timezone(self.timezoneName).localize(datetime.datetime.now()).tzinfo._utcoffset.seconds/60/60)
        print('Timezone: ' + self.timezoneName + ' ' + '(' + str(self.timezone) + ')')
        if self.chatdownload == 1:
            print('Chat downloading Enabled')
        else:
            print('Chat downloading Disabled')
        if self.downloadVOD == 0:
            print('VOD downloading Enabled')
        else:
            print('VOD downloading Disabled')
        
    def run(self):
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
                if f[0] == 'V':
                    recorded_filename = os.path.join(self.recorded_path, f)
                    dirname = f[:-4]
                    dirname = dirname[4:]
                    dirname = dirname[:8] + dirname[26:]
                    dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                    stream_dir_path = self.processed_path + '/' + dirname
                    if(os.path.isdir(stream_dir_path) is False):
                        os.makedirs(stream_dir_path)
                        recorded_filename = os.path.join(self.recorded_path, f)
                        print('Fixing ' + recorded_filename + '.')
                        try:
                            os.chdir(self.ffmpeg_path)
                            processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                            subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                        except Exception as e:
                            print(e)
                    elif(os.path.exists(os.path.join(stream_dir_path, f)) is False):
                        print('Fixing ' + recorded_filename + '.')
                        processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                        subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                    elif self.cleanrecorded == 1:
                        recorded_filename = os.path.join(self.recorded_path, f)
                        print('Fixing ' + recorded_filename + '.')
                        os.remove(recorded_filename)                    
                elif f[11] == 'h':
                    dirname = f[:-4]
                    dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                    stream_dir_path = self.processed_path + '/' + dirname
                    if(os.path.isdir(stream_dir_path) is False):
                        os.makedirs(stream_dir_path)
                        recorded_filename = os.path.join(self.recorded_path, f)
                        print('Fixing ' + recorded_filename + '.')
                        try:
                            os.chdir(self.ffmpeg_path)
                            processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                            subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                        except Exception as e:
                            print(e)
                    elif(os.path.exists(os.path.join(stream_dir_path,f)) is False):
                        recorded_filename = os.path.join(self.recorded_path, f)
                        print('Fixing ' + recorded_filename + '.')
                        processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                        subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                    elif self.cleanrecorded == 1:
                        recorded_filename = os.path.join(self.recorded_path, f)
                        print('Fixing ' + recorded_filename + '.')
                        os.remove(recorded_filename)
                else:
                    recorded_filename = os.path.join(self.recorded_path, f)
                    dirname = f[:8] + f[26:]
                    dirname = dirname[:-4]
                    dirname = "".join(x for x in dirname if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                    stream_dir_path = self.processed_path + '/' + dirname
                    if(os.path.isdir(stream_dir_path) is False):
                        os.makedirs(stream_dir_path)
                        recorded_filename = os.path.join(self.recorded_path, f)
                        print('Fixing ' + recorded_filename + '.')
                        try:
                            os.chdir(self.ffmpeg_path)
                            processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                            subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                        except Exception as e:
                            print(e)
                    elif(os.path.exists(os.path.join(stream_dir_path, f)) is False):
                        print('Fixing ' + recorded_filename + '.')
                        processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                        subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(stream_dir_path,f)])
                    elif self.cleanrecorded == 1:
                        recorded_filename = os.path.join(self.recorded_path, f)
                        print('Fixing ' + recorded_filename + '.')
                        os.remove(recorded_filename)
        except Exception as e:
            print(e)
        
        print("Checking for", self.username, "every", self.refresh, "seconds. Record with", self.quality, "quality.")
        self.loopcheck()

    def check_user(self):
        # 0: online, 
        # 1: offline, 
        # 2: not found, 
        # 3: error
        
        url = 'https://api.twitch.tv/kraken/channels/' + self.username
        info = None
        status = 3
        try:
            r = requests.get(url, headers = {"Client-ID" : self.client_id}, timeout = 15)
            r.raise_for_status()
            info = r.json()
            status = 0
        except requests.exceptions.RequestException as e:
            if e.response != None:
                if e.response.reason == 'Not Found' or e.response.reason == 'Unprocessable Entity':
                    status = 2

        return status, info

    def loopcheck(self):
        while True:
            status, info = self.check_user()
            if status == 2:
                print("Username not found. Invalid username or typo.")
                time.sleep(self.refresh)
            elif status == 3:
                print(datetime.datetime.now().strftime("%Hh%Mm%Ss")," ","unexpected error. Try to check internet connection or client-id. Will try again in", self.refresh, "seconds.")
                time.sleep(self.refresh)
            elif status == 1:
                print(self.username, "currently offline, checking again in", self.refresh, "seconds.")
                time.sleep(self.refresh)
            elif status == 0:
                filename = datetime.datetime.now().strftime("%Y%m%d_%Hh%Mm%Ss") + "_" + self.username + "_" + str(info['status']) + '_' + str(info['game']) + ".mp4"
                present_date=datetime.datetime.now().strftime("%Y%m%d")
                
                # clean filename from unecessary characters
                filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                
                recorded_filename = os.path.join(self.recorded_path, filename)
                
                # start streamlink process
                subprocess.call(["streamlink", "--twitch-disable-reruns", "--twitch-disable-hosting", "twitch.tv/" + self.username, self.quality, "-o", recorded_filename])
                
                if(os.path.exists(recorded_filename) is True):
                    try:
                        channel_id=info["_id"]
                        vodurl = 'https://api.twitch.tv/kraken/channels/' + str(channel_id) + '/videos?broadcast_type=archive'
                        vods = requests.get(vodurl, headers = {"Accept" : 'application/vnd.twitchtv.v5+json', "Client-ID" : self.client_id}, timeout = 1)
                        vodsinfodic = json.loads(vods.text)
                        if vodsinfodic["_total"] > 0:
                            vod_id = vodsinfodic["videos"][0]["_id"]
                            vod_id = vod_id[:0] + vod_id[1:]
                            created_at = vodsinfodic["videos"][0]["created_at"]
                            created_day = present_date
                            created_time_hour = created_at[11:]
                            created_time_hour = created_time_hour[:2]
                            created_time_hourTimezone = int(created_time_hour)+self.timezone
                            if created_time_hourTimezone >= 24:
                                created_time_hourTimezone -= 24
                            elif created_time_hourTimezone < 0:
                                created_time_hourTimezone += 24
                            if created_time_hourTimezone < 10:
                                created_time_hourTimezone = "0" + str(created_time_hourTimezone)
                            created_time_minutes = created_at[13:]
                            created_time_minutes = created_time_minutes[:3]
                            created_time = "(" + str(created_time_hourTimezone) + "-" + created_time_minutes + ")"
                            processed_stream_folder = created_day + "_" + vodsinfodic["videos"][0]["title"] + '_' + vodsinfodic["videos"][0]["game"] + '_' + self.username
                            processed_stream_folder = "".join(x for x in processed_stream_folder if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                            processed_stream_path = self.processed_path + "/" + processed_stream_folder
                            if(os.path.isdir(processed_stream_path) is False):
                                os.makedirs(processed_stream_path)
                            temp_filename = filename
                            filename = created_day + "_" + created_time + "_" + vod_id + "_" + vodsinfodic["videos"][0]["title"] + '_' + vodsinfodic["videos"][0]["game"] + '_' + self.username + ".mp4"
                            filename = "".join(x for x in filename if x.isalnum() or not x in ["/","\\",":","?","*",'"',">","<","|"])
                            filenameError = 0
                            try:
                                os.rename(recorded_filename,os.path.join(self.recorded_path, filename))
                                recorded_filename = os.path.join(self.recorded_path, filename)
                            except Exception as e:
                                filename = temp_filename
                                filenameError = 1
                                print(e)
                                print('An error has occurred. VOD and chat will not be downloaded. Please check them manually.')
                            if self.chatdownload == 1 and filenameError == 0:
                                subtitles_window = "cmd.exe /c start".split() + self.cmdstatecommand
                                subprocess.call(subtitles_window + ["tcd", "-v", vod_id, "--timezone", self.timezoneName, "-f", "irc,ssa,json", "-o", processed_stream_path])
                            if self.downloadVOD == 1 and filenameError == 0:
                                vod_filename = "VOD_" + filename
                                vod_window = "cmd.exe /c start".split() + self.cmdstatecommand
                                subprocess.call(vod_window + ["streamlink", "twitch.tv/videos/" + vod_id, self.quality, "-o", os.path.join(self.recorded_path,vod_filename)])
                        else:
                            processed_stream_path = self.processed_path + "/" + filename[:-4]
                            if(os.path.isdir(processed_stream_path) is False):
                                os.makedirs(processed_stream_path)
                    except Exception as e:
                        print(e)
                
                print("Recording stream is done. Fixing video file.")
                if(os.path.exists(recorded_filename) is True):
                    try:
                        os.chdir(self.ffmpeg_path)
                        processing_window = "cmd.exe /c start".split() + self.cmdstatecommand
                        subprocess.call(processing_window + ['ffmpeg', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-start_at_zero', '-copyts', '-bsf:a', 'aac_adtstoasc', os.path.join(processed_stream_path,filename)])
                    except Exception as e:
                        print(e)
                else:
                    print("Skip fixing. File not found.")
                    
                print("Fixing is done. Going back to checking..")
                time.sleep(self.refresh)

def main(argv):
    twitch_recorder = TwitchRecorder()
    usage_message = 'record.py -u <username> -q <quality>'
    try:
        opts, args = getopt.getopt(argv,"hu:q:",["username=","quality="])
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

    twitch_recorder.run()

if __name__ == "__main__":
    main(sys.argv[1:])
