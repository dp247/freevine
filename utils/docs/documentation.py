from utils import __version__

main_help = f"""
    \b
    Freevine {__version__}
    Author: stabbedbybrick

    \b
    Requirements:
        Python 3.9+
        Valid Widevine Device file
        N_m3u8DL-RE
        ffmpeg
        mkvmerge
        mp4decrypt
        shaka-packager
        hola-proxy (optional)
    \b
    Installation:
        1. Install Python (check 'Add to PATH' if on Windows)
        2. Clone or download Freevine repository
        3. Place required tools inside Freevine folder OR add to system PATH(recommended)
        4. Create /utils/wvd/ folder and place either .wvd file or private_key and client blob inside
        5. Install necessary packages: `pip install -r requirements.txt`
    \b
    Settings:
        Open config.yaml in your favorite text editor to configure global settings
    \b
        Copy config.yaml file to a service folder in order to configure that specific service
        This config, if it exists, will override the main config
    \b
        Using config settings in command will override everything else (see options below for examples)
    \b
        Default values for all services:
            Video: Best available
            Audio: Best available
            Subtitles: Cleaned SRT muxed with final output
    \b
    Login credentials:
        A user profile with credentials can be set for services that require it:
    \b
            freevine.py profile --username "USERNAME" --password "PASSWORD" --service "SERVICE"
    \b
            NOTES:
            Setting a user profile will create a profile.yaml in the service folder
            It will store credentials along with cached auth and refresh tokens
    \b
    Cookies:
        Some services can be used with a cookie file:
    \b
            Use a browser extension to download cookies as .txt file format:
            Firefox: https://addons.mozilla.org/addon/export-cookies-txt
            Chrome: https://chrome.google.com/webstore/detail/gdocmgbfkjnnpapoeobnolbbkoibbcif
    \b
            Name it "cookies.txt" and place it in service folder
    \b
    Download Instructions:
        This program has got two methods of downloading:
    \b
        Method 1: (singles and batch)
            Provide the series main URL and request what to download from it:
    \b
                freevine.py get --episode  S01E01 URL
                freevine.py get --episode  "Name of episode" URL
                freevine.py get --season   S01 URL
                freevine.py get --episode  S01E01-S01E10 URL
                freevine.py get --episode  S01E01,S03E07,S10E12 URL
                freevine.py get --season   S01,S03,S10 URL
                freevine.py get --complete URL
    \b
            NOTES:
            Always use main URL of series for this method, not episode URLs
            Use the S01E01 format, or "episode name", to request episodes
            Use --episode S01E01-S01E10 to request a range of episodes (from the same season)
            Use --episode S01E01,S03E07,S10E12 (no spaces!) to request a mix of episodes
            Use --season S01,S03,S10 (no spaces!) to request a mix of seasons
    \b
            If a season is displaying duplicate numbering and/or no numbers at all, you can use -fn to force numbering
            This will add numbers based on its placement on site, making it easier to download
    \b     
            freevine.py --titles -fn https://www.example.com/series_url
    \b
        Method 2: (singles)
            Provide URL to episode or movie to download it directly:
    \b
                freevine.py get --episode EPISODE_URL
                freevine.py get --movie MOVIE_URL
    \b
            NOTES:
            If the episode is a standalone, you might have more success by using --movie
            Grabbing the URLs straight from the frontpage often comes with extra
            garbage attached. It's recommended to get the URL from title page
    \b
    Options:
            List all available episodes from a series:
                freevine.py get --titles URL
            Print available quality streams and info about a single title:
                freevine.py get --info --episode URL
                freevine.py get --info --movie URL
            Request video quality to be downloaded: (default: best)
                freevine.py get --select-video res=720 --episode/--season URL
                freevine.py get --select-video res=1080 --movie URL
            Request audio tracks to be downloaded: (default: best)
                freevine.py get --select-audio name=English --episode/--season URL
                freevine.py get --select-audio id=Descriptive --movie URL
            Request only subtitles from title(s):
                freevine.py get --sub-only --episode/--movie URL
    \b
            NOTES:
            See "N_m3u8DL-RE --morehelp select-video/audio/subtitle" for possible selection patterns
    \b
    Searching:
        You can use the search option to search for titles in the command line:
    \b
            freevine.py search all4 "QUERY"
            freevine.py search all4,ctv,itv "QUERY"
    \b
            NOTES:
            You can search one or multiple services at the same time
            The results should produce usable URL to series or movie
            Some services have geo block even for searching
    \b
    Proxy:
        You can request or specify a proxy server to be used for API and license requests:
    \b
            freevine.py --proxy US
            freevine.py --proxy "01.234.56.789:10"
    \b
            NOTES:
            Requesting a proxy by country code requires https://github.com/Snawoot/hola-proxy
            Download the exectutable from the releases page and rename it to "hola-proxy"
            Place it in the same location as the other required tools. System PATH is recommended
    \b
            The proxy currently only affects API and license requests, not downloads
    \b
    Final notes:
    \b
        This program is just a hobby project made for fun
        Expect bugs and odd behavior, and consider it to be in forever beta
    \b
        Known bugs:
        Programmes without clear season/episode labels might display odd names and numbers

    \b
        Free streaming services are free for a reason and usually comes with gaps and odd labels
        It's STRONGLY recommended to use --titles to view episodes before downloading!
    """
