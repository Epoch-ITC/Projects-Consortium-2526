#!/usr/bin/env bash
set -euo pipefail

# Directory containing your audio files
# This assumes the script is placed in the parent directory of Quantum-Bio-Mashup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUSIC_DIR="$SCRIPT_DIR/raw_songs"

if [ ! -d "$MUSIC_DIR" ]; then
  echo "Error: directory '$MUSIC_DIR' does not exist." >&2
  exit 1
fi

cd "$MUSIC_DIR"

# Make sure that *.mp3 expands to nothing (instead of literal "*.mp3") when there are no matches
shopt -s nullglob

echo "Working in: $MUSIC_DIR"
echo "Looking for .mp3 files to convert..."

# Loop over .mp3 files (case-insensitive: .mp3 and .MP3)
for mp3 in *.mp3 *.MP3; do
  # If no files matched, skip
  [ -e "$mp3" ] || continue

  wav="${mp3%.*}.wav"

  # 1) Do not touch existing .wav files (no overwrite)
  if [ -e "$wav" ]; then
    echo "WAV already exists for '$mp3' -> '$wav'. Skipping conversion."
  else
    echo "Converting '$mp3' -> '$wav'..."
    # ffmpeg will fail the script if something goes wrong because of 'set -e'
    ffmpeg -hide_banner -loglevel error -i "$mp3" "$wav"
    echo "Finished converting '$mp3'."
  fi

  # 2) Remove redundant .mp3 ONLY if a valid .wav exists
  if [ -e "$wav" ] && [ -s "$wav" ]; then
    echo "Confirmed valid WAV '$wav'. Deleting original MP3 '$mp3'."
    rm -- "$mp3"
  else
    echo "Warning: No valid WAV for '$mp3'. Keeping MP3."
  fi

  echo
done

echo "All done. 🎧"
