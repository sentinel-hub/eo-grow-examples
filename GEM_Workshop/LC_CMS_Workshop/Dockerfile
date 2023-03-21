FROM sentinelhub/gem:gdal_base

# This base image contains GDAL V3.2.3 and Python 3.10

RUN apt-get update && apt-get install -y git && apt-get install -y wget && apt-get install unzip

RUN pip install jupyterlab

COPY . /gem-workshop/

# Install SentinelHub libraries
RUN pip install sentinelhub>=3.6.3
RUN pip install eo-learn==1.3.1

WORKDIR /sentinelhub_libs
RUN git clone https://github.com/aashishd/eo-grow.git
RUN pip install -e /sentinelhub_libs/eo-grow


RUN pip install gdal==3.2.3
# $(gdalinfo --version | awk -F "," '{print $1}' | awk '{print $2}') --no-cache-dir
RUN pip install -r /gem-workshop/requirements.txt

ENTRYPOINT exec jupyter-lab --ip 0.0.0.0 --no-browser --port 8888 --notebook-dir /gem-workshop --allow-root --ServerApp.password='sha1:5b7cc1fa957e:8dbf8e98117e3ce4e0ca9000ff2eef62ca4d9f2e'
# Set the container entrypoint
#RUN chmod +x /gem-workshop/entrypoint.sh
#ENTRYPOINT ["/gem-workshop/entrypoint.sh"]

