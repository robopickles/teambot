FROM ubuntu:xenial

MAINTAINER Alexey Zankevich <zancudero@gmail.com>

ENV LANG C.UTF-8
ENV LANGUAGE C.UTF-8
ENV LC_ALL C.UTF-8
ENV CONTAINER_TYPE teambot
ENV SUPERVISOR_CONFIG app.conf

RUN apt update && \
    apt install -y binutils \
                   curl \
                   postgresql-client \
                   python3-pip \
                   software-properties-common \
                   sudo \
                   supervisor \
                   uwsgi \
                   uwsgi-plugin-python3

# add ES repo and install filebeat
RUN curl https://packages.elasticsearch.org/GPG-KEY-elasticsearch | sudo apt-key add -
RUN echo "deb http://packages.elastic.co/beats/apt stable main" |  sudo tee -a /etc/apt/sources.list.d/beats.list
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y filebeat


RUN mkdir -p /var/run/celerybeat/
VOLUME /var/run/celerybeat/

ENV DJANGO_SETTINGS_MODULE teambot.settings

# install python dependencies
ADD requirements.txt /home/docker/

# RUN pip2 install -U pip setuptools six==1.10.0
RUN pip3 install -r /home/docker/requirements.txt

# install project sources
ADD . /home/docker/code/

WORKDIR /home/docker/code/

VOLUME /var/log/teambot/

# -: optimize
RUN python3 manage.py collectstatic -c --noinput

EXPOSE 80
CMD ["bash", "-c", "test -f /etc/supervisor/conf.d/$SUPERVISOR_CONFIG || ln -s /home/docker/code/ext_configs/supervisor/$SUPERVISOR_CONFIG /etc/supervisor/conf.d/ && supervisord -n" ]
