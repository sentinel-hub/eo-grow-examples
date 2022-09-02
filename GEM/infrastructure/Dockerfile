FROM rayproject/ray:latest-py39-cpu

LABEL maintainer="Sinergise EO research team <eoresearch@sinergise.com>"

ARG SH_CLIENT_ID
ARG SH_CLIENT_SECRET
ARG EOGROW_EXAMPLES_BRANCH

RUN sudo apt-get update && sudo apt-get install -y software-properties-common
RUN sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y
RUN sudo apt-get update && sudo apt-get install -y \
        libspatialindex-dev gcc libgeos-c1v5 libgeos-dev curl screen nano htop unzip \
        cmake graphviz proj-bin libproj-dev gdal-bin libgdal-dev build-essential libpython3.9 vim \
    && sudo apt-get clean && sudo apt-get autoremove -y && sudo rm -rf /var/lib/apt/lists/*

RUN curl https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip \
    && unzip awscliv2.zip && sudo ./aws/install && rm -rf ./aws*

RUN pip install --no-cache-dir pip --upgrade
RUN pip install boto3 ipdb --upgrade --no-cache-dir

RUN conda clean --all --force-pkgs-dirs -y

RUN mkdir packages
WORKDIR /home/ray/packages

RUN pip install eo-grow --no-cache-dir

RUN pip install gdal==$(gdalinfo --version | awk -F "," '{print $1}' | awk '{print $2}') --no-cache-dir

RUN git clone --depth 1 -b ${EOGROW_EXAMPLES_BRANCH} https://github.com/sentinel-hub/eo-grow-examples/
RUN pip install -e ./eo-grow-examples/GEM/ --no-cache-dir

WORKDIR /home/ray/

RUN sentinelhub.config --sh_client_id ${SH_CLIENT_ID} --sh_client_secret ${SH_CLIENT_SECRET}