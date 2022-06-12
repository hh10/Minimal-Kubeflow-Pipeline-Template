FROM ubuntu:20.04

RUN apt update && apt install apt-utils -y && apt install python3 apt-transport-https ca-certificates gnupg curl git -y
COPY known_hosts /tmp/known_hosts
RUN mkdir -p /root/.ssh && cat /tmp/known_hosts >> /root/.ssh/known_hosts
COPY id_rsa /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-cli -y
COPY grand-kingdom-352313-8f82637b0415.json /home/
RUN gcloud auth activate-service-account --key-file /home/grand-kingdom-352313-8f82637b0415.json
RUN gcloud config set project grand-kingdom-352313
