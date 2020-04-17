# Auto Stream Recording Twitch
Python script for auto recording streams.
Thanks for source script to [junian](https://gist.github.com/junian/b41dd8e544bf0e3980c971b0d015f5f6)

# Requirements

* [Python 3](https://www.python.org/downloads/)
* [Twitch Chat Downloader](https://github.com/PetterKraabol/Twitch-Chat-Downloader) (optional)
* [Streamlink](https://github.com/streamlink/streamlink)
* [FFmpeg](http://ffmpeg.org/download.html)

# Features

* Recording live streams automatically using streamlink without delay (stream will not be cut at the beginning)
* Downloading chat using Twitch Chat Downloader (optional)
* Converting streams using FFmpeg [(thanks to Twitch Leecher)](https://github.com/Franiac/TwitchLeecher)
* Creating folders for each stream

# Installing

1. Install Python 3
2. Instal Twitch Chat Downloader and Streamlink
3. Download ffmpeg
4. Download script and open it using [notepad++](https://notepad-plus-plus.org/downloads/) (it is much better)
5. Change options to preferred
6. You can also use this script using command line: ```Auto_Recording_Twitch.py -u <username> -q <quality> -v <download VOD 1/0>```
