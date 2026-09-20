#!/bin/bash

INPUT_DIR="raw_songs"
OUTPUT_DIR="raw_wav"

mkdir -p $OUTPUT_DIR

for file in $INPUT_DIR/*.mp4
do
    base=$(basename "$file" .mp4)
    echo "Converting $base"

    ffmpeg -i "$file" \
        -ac 1 \
        -ar 22050 \
        -vn \
        "$OUTPUT_DIR/$base.wav"
done

echo "Conversion complete."