#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
. prep-ubuntu-no-gif.sh
#
# For GIF support
#
apt-get install -y asciinema npm nodejs imagemagick gifsicle
.jekyll-metadata/
(mkdir -p /opt/asciicast2gif;cd /opt/asciicast2gif/;npm install asciicast2gif)
cat >/usr/local/bin/asciicast2gif <<END
#!/bin/sh
/opt/asciicast2gif/node_modules/.bin/asciicast2gif \$@
END

chmod 755 /usr/local/bin/asciicast2gif
