# Incomplete Torrent Downloads Merger
This program can be used to merge incomplete files from different torrent downloads (of a same file). It detects the missing chunks in the main file and tries to fill the blanks using the secondary file.

### Prerequisites

[torrent_parser](https://github.com/7sDream/torrent_parser) and [colorama](https://github.com/tartley/colorama) are required.

```
pip install torrent_parser
pip install colorama
```

### Recommended usage

The program will ask for file locations and provide the instructions along the way.

With multi-file torrents, some neighboring files are usually needed to verify checksums of the first and/or last chunk of the main file. The program will look for these files in the same directory as the main file (or a correspoding subdirectory, if it's placed in one in the torrent), so it's most convenient to leave the main file in the original torrent download directory and point the program to it.

Existing files are left intact and the resulting file is saved with '[merged]' prefix into the same directory as the main file.

### Binaries

Windows binary is available in Releases.
