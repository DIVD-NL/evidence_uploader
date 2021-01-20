FROM kalilinux/kali-rolling:latest

LABEL maintainer="f.breedijk@divd.nl"

RUN apt-get update ; apt-get upgrade -y 
RUn apt-get install -y python g++ make checkinstall fakeroot

WORKDIR /root/project

#RUN gem install bundler && \
#mkdir -p .bundle-cache && \
#gem install github-pages

#EXPOSE 4000

COPY entrypoint.sh /root

ENTRYPOINT [ "/root/entrypoint.sh" ]

