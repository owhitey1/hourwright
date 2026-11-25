"""Download ElevenLabs generations (voice-overs, music) into assets/ using ELEVENLABS_API_KEY.

Usage: elevenlabs_fetch.py "match text=file.mp3" ...  -> downloads the newest history item whose text
contains `match text`. With no arguments, lists recent history items (no secrets printed).
Music: "music:<title>=file.mp3" searches music generations by title.
"""
import json, os, pathlib, sys, urllib.request, urllib.error

KEY = os.environ["ELEVENLABS_API_KEY"]
API = "https://api.elevenlabs.io"


def call(path, raw=False):
    req = urllib.request.Request(API + path, headers={"xi-api-key": KEY, "accept": "*/*"})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    return body if raw else json.loads(body)


def history():
    return call("/v1/history?page_size=100").get("history", [])


def music_items():
    for path in ("/v1/music/chats?page=0&per_page=50", "/v1/music/history?page_size=50"):
        try:
            data = call(path)
            print("music listing from", path, "keys:", list(data)[:6] if isinstance(data, dict) else type(data))
            return data
        except urllib.error.HTTPError as e:
            print("music listing", path, "->", e.code)
    return None


def main(args):
    out = pathlib.Path("assets"); out.mkdir(exist_ok=True)
    items = history()
    for h in items[:15]:
        print(h.get("history_item_id"), h.get("source"), h.get("date_unix"), (h.get("text") or "")[:70])
    for a in args:
        match, name = a.rsplit("=", 1)
        if match.startswith("id:"):
            (out / name).write_bytes(call(f"/v1/history/{match[3:]}/audio", raw=True))
            print("saved", name, (out / name).stat().st_size); continue
        if match.startswith("tts:"):
            voice = next((h["voice_id"] for h in items if h.get("voice_id")), "JBFqnCBsd6RMkjVDRZzb")
            body = json.dumps({"text": match[4:], "model_id": "eleven_multilingual_v2",
                               "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35}}).encode()
            req = urllib.request.Request(f"{API}/v1/text-to-speech/{voice}?output_format=mp3_44100_128", data=body,
                                         method="POST", headers={"xi-api-key": KEY, "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                (out / name).write_bytes(r.read())
            print("saved", name, (out / name).stat().st_size, "voice", voice); continue
        if match.startswith("compose:"):
            body = json.dumps({"prompt": match[8:], "music_length_ms": 30000, "force_instrumental": True}).encode()
            req = urllib.request.Request(API + "/v1/music", data=body, method="POST",
                                         headers={"xi-api-key": KEY, "content-type": "application/json", "accept": "audio/mpeg"})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    (out / name).write_bytes(r.read())
                print("saved", name, (out / name).stat().st_size)
            except urllib.error.HTTPError as e:
                print("compose failed", e.code, e.read()[:300])
            continue
        if match.startswith("music:"):
            data = music_items()
            print(json.dumps(data)[:3000] if data else "no music listing")
            continue
        hit = next((h for h in items if match.lower() in (h.get("text") or "").lower()), None)
        if not hit:
            print("NOT FOUND:", match); continue
        (out / name).write_bytes(call(f"/v1/history/{hit['history_item_id']}/audio", raw=True))
        print("saved", name, (out / name).stat().st_size)


if __name__ == "__main__":
    main(sys.argv[1:])
