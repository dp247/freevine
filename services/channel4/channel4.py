"""
Credit to Diazole and rlaphoenix for paving the way

Author: stabbedbybrick

Info:
This program will grab higher 1080p bitrate (if available)

"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import click
import yaml
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from bs4 import BeautifulSoup

from utils.args import get_args
from utils.cdm import LocalCDM
from utils.config import Config
from utils.options import get_downloads
from utils.titles import Episode, Movie, Movies, Series
from utils.utilities import (
    expiration,
    get_heights,
    get_wvd,
    kid_to_pssh,
    set_filename,
    set_save_path,
    string_cleaning,
    force_numbering,
    add_subtitles,
    in_cache,
    update_cache,
)



class CHANNEL4(Config):
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)

        self.lic_url = self.config["license"]
        self.login = self.config["login"]
        self.username = self.config.get("credentials", {}).get("username")
        self.password = self.config.get("credentials", {}).get("password")

        with self.config["download_cache"].open("r") as file:
            self.cache = json.load(file)

        self.client.headers = {
            "x-c4-platform-name": "android",
            "x-c4-device-type": "mobile",
            "x-c4-app-version": "android_app:9.4.2",
            "x-c4-device-name": "Sony C6903 (C6903)",
            "x-c4-optimizely-datafile": "2908",
        }

        self.get_options()

    def get_auth_token(self):
        cache = self.config.get("cache")

        if not cache:
            self.log.info("Cache is empty, aquiring new tokens...")
            token = self.authenticate()
        elif cache and cache.get("expiry") < datetime.now():
            self.log.info("Refreshing expired tokens...")
            token = self.refresh_token()
        else:
            self.log.info("Using cached tokens")
            token = cache.get("token")

        return token

    def get_license(self, challenge: bytes, lic_url: str, assets: tuple) -> str:
        manifest, token, asset = assets
        payload = {
            "message": base64.b64encode(challenge).decode("utf8"),
            "token": token,
            "request_id": asset,
            "video": {"type": "ondemand", "url": manifest},
        }

        r = self.client.post(lic_url, json=payload)
        if not r.ok:
            raise ConnectionError(
                f"License request failed: {r.json()['status']['type']}"
            )

        return r.json()["license"]

    def get_keys(self, pssh: str, lic_url: str, assets: tuple):
        wvd = get_wvd(Path.cwd())
        widevine = LocalCDM(wvd)
        challenge = widevine.challenge(pssh)
        response = self.get_license(challenge, lic_url, assets)
        return widevine.parse(response)

    def decrypt_token(self, token: str, client: str) -> tuple:
        if client == "android":
            key = self.config["android"]["key"]
            iv = self.config["android"]["iv"]

        if client == "web":
            key = self.config["web"]["key"]
            iv = self.config["web"]["iv"]

        if isinstance(token, str):
            token = base64.b64decode(token)
            cipher = AES.new(
                key=base64.b64decode(key),
                iv=base64.b64decode(iv),
                mode=AES.MODE_CBC,
            )
            data = unpad(cipher.decrypt(token), AES.block_size)
            dec_token = data.decode().split("|")[1]
            return dec_token.strip()

    def get_data(self, url: str) -> dict:
        r = self.client.get(url)
        init_data = re.search(
            "<script>window.__PARAMS__ = (.*)</script>",
            "".join(
                r.content.decode()
                .replace("\u200c", "")
                .replace("\r\n", "")
                .replace("undefined", "null")
            ),
        )
        data = json.loads(init_data.group(1))
        return data["initialData"]

    def get_series(self, url: str) -> Series:
        data = self.get_data(url)

        return Series(
            [
                Episode(
                    id_=episode.get("programmeId"),
                    service="ALL4",
                    title=data["brand"]["title"],
                    season=episode["seriesNumber"],
                    number=episode["episodeNumber"],
                    name=episode["originalTitle"],
                    year=None,
                    data=episode.get("assetId"),
                    description=episode.get("summary"),
                )
                for episode in data["brand"]["episodes"]
                if episode["showPlayLabel"] is True
            ]
        )

    def get_movies(self, url: str) -> Movies:
        data = self.get_data(url)

        return Movies(
            [
                Movie(
                    id_=movie.get("programmeId"),
                    service="ALL4",
                    title=data["brand"]["title"],
                    year=data["brand"]["summary"].split(" ")[0].strip().strip("()"),
                    name=data["brand"]["title"],
                    data=None,
                    synopsis=movie.get("summary"),
                )
                for movie in data["brand"]["episodes"]
            ]
        )

    def refresh_token(self):
        self.client.headers.update(
            {
                "authorization": f"Basic {self.config['android']['auth']}",
            }
        )

        data = {
            "grant_type": "refresh_token",
            "username": self.username,
            "password": self.password,
            "refresh_token": self.config["cache"]["refresh"],
        }

        r = self.client.post(self.login, data=data)
        if not r.ok:
            raise ConnectionError(f"{r} {r.text}")

        auth = json.loads(r.content)
        token = auth.get("accessToken")
        refresh = auth.get("refreshToken")

        expiry = expiration(auth.get("expiresIn"), auth.get("issuedAt"))

        profile = Path("services") / "channel4" / "profile.yaml"
        with open(profile, "r") as f:
            data = yaml.safe_load(f)

        data["cache"]["token"] = token
        data["cache"]["refresh"] = refresh
        data["cache"]["expiry"] = expiry

        with open(profile, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)

        self.log.info("+ Tokens refreshed")

        return token

    def authenticate(self):
        if not self.username and not self.password:
            self.log.error(
                "Required credentials were not found. See 'freevine.py profile --help'"
            )
            sys.exit(1)

        self.log.info("Authenticating with service...")

        self.client.headers.update(
            {
                "authorization": f"Basic {self.config['android']['auth']}",
            }
        )

        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
        }

        r = self.client.post(self.login, data=data)
        if not r.ok:
            raise ConnectionError(f"{r} {r.text}")

        auth = json.loads(r.content)
        token = auth.get("accessToken")
        refresh = auth.get("refreshToken")

        expiry = expiration(auth.get("expiresIn"), auth.get("issuedAt"))

        profile = Path("services") / "channel4" / "profile.yaml"
        with open(profile, "r") as f:
            data = yaml.safe_load(f)

        data["cache"] = {"token": token, "expiry": expiry, "refresh": refresh}

        with open(profile, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)

        self.log.info("+ New tokens placed in cache")

        return token

    def android_playlist(self, video_id: str, bearer: str, quality: str) -> tuple:
        url = self.config["android"]["vod"].format(video_id=video_id)
        self.client.headers.update({"authorization": f"Bearer {bearer}"})

        r = self.client.get(url=url)
        if not r.ok:
            raise ConnectionError(f"{r} {r.text}")

        data = json.loads(r.content)
        manifest = data["videoProfiles"][0]["streams"][0]["uri"]
        token = data["videoProfiles"][0]["streams"][0]["token"]

        return manifest, token

    def web_playlist(self, video_id: str) -> tuple:
        url = self.config["web"]["vod"].format(programmeId=video_id)
        r = self.client.get(url)
        if not r.ok:
            raise ConnectionError(f"{r} {r.json().get('message')}")

        data = json.loads(r.content)

        for item in data["videoProfiles"]:
            if item["name"] == "dashwv-dyn-stream-1":
                token = item["streams"][0]["token"]
                manifest = item["streams"][0]["uri"]

        subtitle = [
            x["url"] for x in data["subtitlesAssets"] if x["url"].endswith(".vtt")
        ][0]
        if subtitle is not None:
            r = self.client.get(manifest)
            r.raise_for_status()

            soup = BeautifulSoup(r.content, "xml")
            self.web = add_subtitles(soup, subtitle)
            self.base_url = manifest.split("stream.mpd")[0]
            with open(self.tmp / "manifest.mpd", "w") as f:
                f.write(str(self.web.prettify()))

        return manifest, token

    def get_mediainfo(self, video_id: str, quality: str, bearer: str) -> str:
        self.web = None

        manifest, token = self.android_playlist(video_id, bearer, quality)
        lic_token = self.decrypt_token(token, client="android")
        heights, self.soup = get_heights(self.client, manifest)
        resolution = heights[0]

        if heights[0] < 1080:
            manifest, token = self.web_playlist(video_id)
            lic_token = self.decrypt_token(token, client="web")
            heights, self.soup = get_heights(self.client, manifest)
            resolution = heights[0]

        if quality is not None:
            if int(quality) in heights:
                resolution = quality
            else:
                resolution = min(heights, key=lambda x: abs(int(x) - int(quality)))

        return resolution, manifest, lic_token

    def get_content(self, url: str) -> object:
        if self.movie:
            with self.console.status("Fetching movie titles..."):
                content = self.get_movies(self.url)
                title = string_cleaning(str(content))

            self.log.info(f"{str(content)}\n")

        else:
            with self.console.status("Fetching series titles..."):
                content = self.get_series(url)

                title = string_cleaning(str(content))
                seasons = Counter(x.season for x in content)
                num_seasons = len(seasons)
                num_episodes = sum(seasons.values())

                if self.force_numbering:
                    content = force_numbering(content)

            self.log.info(
                f"{str(content)}: {num_seasons} Season(s), {num_episodes} Episode(s)\n"
            )

        return content, title

    def get_episode_from_url(self, url: str):
        with self.console.status("Getting episode from URL..."):
            brand = self.get_data(url)

            episode = Series(
                [
                    Episode(
                        id_=brand["selectedEpisode"]["programmeId"],
                        service="ALL4",
                        title=brand["brand"]["title"],
                        season=brand["selectedEpisode"]["seriesNumber"] or 0,
                        number=brand["selectedEpisode"]["episodeNumber"] or 0,
                        name=brand["selectedEpisode"]["originalTitle"],
                        year=None,
                        data=brand["selectedEpisode"].get("assetId"),
                        description=brand["selectedEpisode"].get("summary"),
                    )
                ]
            )

        title = string_cleaning(str(episode))

        return [episode[0]], title

    def get_options(self) -> None:
        bearer = self.get_auth_token()
        downloads, title = get_downloads(self)

        for download in downloads:
            if in_cache(self.cache, download):
                continue

            if self.slowdown:
                with self.console.status(f"Slowing things down for {self.slowdown} seconds..."):
                    time.sleep(self.slowdown)

            self.download(download, title, bearer)

    def download(self, stream: object, title: str, bearer: str) -> None:
        self.res, manifest, token = self.get_mediainfo(stream.id, self.quality, bearer)
        pssh = kid_to_pssh(self.soup)
        assets = manifest, token, stream.data

        keys = self.get_keys(pssh, self.lic_url, assets)
        with open(self.tmp / "keys.txt", "w") as file:
            file.write("\n".join(keys))

        self.filename = set_filename(self, stream, self.res, audio="AAC2.0")
        self.save_path = set_save_path(stream, self, title)
        self.manifest = self.tmp / "manifest.mpd" if self.web else manifest
        self.key_file = self.tmp / "keys.txt"
        self.sub_path = None

        click.echo("")
        self.log.info(f"{str(stream)}")
        click.echo("")

        args, file_path = get_args(self)

        try:
            subprocess.run(args, check=True)
        except Exception as e:
            self.sub_path.unlink() if self.sub_path else None
            raise ValueError(f"{e}")
        
        if not self.skip_download and file_path.exists():
            update_cache(self.cache, self.config, stream)
