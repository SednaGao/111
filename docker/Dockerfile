############################################################
# Dockerfile to build CentOS,Nginx installed  Container
# Based on CentOS
#For suzhou project 
############################################################

# Base image
FROM flask-mvc-base

# File Author / Maintainer

# Arguments with default value
ARG ui_code_version=master
ENV UI_CODE_VERSION=$ui_code_version
ARG ui_git_url=https://dongjiangjiang:Shurong2019@bitbucket.org/fusiontree/scc.ui.git
ENV UI_GIT_URL=$ui_git_url

ARG fe_code_version=master
ENV FE_CODE_VERSION=$fe_code_version
ARG fe_git_url=https://dongjiangjiang:Shurong2019@bitbucket.org/fusiontree/scc.fe.git
ENV FE_GIT_URL=$fe_git_url

# Update library
#RUN yum -y update

#create softlink of logfile of project for monitor logfile
RUN touch /var/log/nginx/error.log \
    && mkdir -p /log/nginx \
    && chmod -R 777 /log/nginx \
    && chown -R nginx:nginx /var/log/nginx/error.log \
    && ln -s /var/log/nginx/error.log /log/nginx/error.log \

    && touch /var/log/nginx/access.log \
    && chown -R nginx:nginx /var/log/nginx/access.log \
    && ln -s /var/log/nginx/access.log /log/nginx/access.log \

    && touch /var/log/nginx/scc-fe_access.log \
    && chown -R nginx:nginx /var/log/nginx/scc-fe_access.log \
    && ln -s /var/log/nginx/scc-fe_access.log /log/nginx/scc-fe_access.log \

    && touch /var/log/nginx/scc-fe_error.log \
    && chown -R nginx:nginx /var/log/nginx/scc-fe_error.log \
    && ln -s /var/log/nginx/scc-fe_error.log /log/nginx/scc-fe_error.log \

    && touch /log/scc-fe.log \
    && chmod 777 /log/scc-fe.log

WORKDIR  /home/docker/code
# setup all the configfiles

# get FE-code
RUN git clone  -b $FE_CODE_VERSION $FE_GIT_URL


# when making  docker compose file ,set context ../
# Adding the configuration file of the nginx
ADD  docker/nginx.conf /etc/nginx/nginx.conf
ADD  docker/sc-fe-nginx.conf /etc/nginx/conf.d/sc-fe-nginx.conf

# Adding the configuration file of the Supervisor
ADD  docker/supervisord.conf /etc/

#uwsgi config for managing flaskProject
COPY docker/uwsgi.ini /home/docker/code/

# add (the rest of) our code
#COPY flask-sz/* /home/docker/code/app
#COPY . /home/docker/code/
#COPY . /home/docker/code/scc.fe

#get scc.ui code
# change dir
WORKDIR /home/docker/code/
# get UI-code
RUN git clone  -b $UI_CODE_VERSION $UI_GIT_URL

# copy dir :node_modules of baseimage into scc.ui

RUN cp  -r node_modules/  scc.ui/

# get into scc.ui
WORKDIR /home/docker/code/scc.ui

#COPY package.json ./
RUN npm install --silent --no-cache --registry=https://registry.npm.taobao.org
# 报异常，单独装
RUN npm install --save react-json-tree
RUN npm run build

WORKDIR /home/docker/code/
#COPY ./ ./
#8088 for scc.ui
EXPOSE 8088
#80 for scc.fe
EXPOSE 80

CMD ["supervisord", "-n"]