/* Send http:// visitors to https:// until GitHub Pages enforces it server-side. */
if (location.protocol === "http:" && location.hostname !== "localhost") {
  location.replace("https://" + location.host + location.pathname + location.search + location.hash);
}
