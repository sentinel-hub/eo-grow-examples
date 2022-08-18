# GEM spot-mode monitoring

## Introduction

_TODO_

## Requirements

The example relies on [SentinelHub service](https://sentinel-hub.com) capabilities to download Sentinel-2 imagery, in particular using the large-scale batch processing API to construct data cubes. The batch processing allows to download images over large Areas of Interest in a very fast and efficient manner. The data is automatically stored in S3 buckets, which need to be properly configured.

For (optional) access to the weather data, the example relies on [meteoblue](https://www.meteoblue.com/en/weather-api) weather API.


## Installation and running of the example

The example is self-contained in it's folder. To set up the working environment, the following should be sufficient:

```
pip install -r requirements.txt
```

Then, we invite the user to open the [`example.ipynb`](./example.ipynb) notebook.


## Documentation

_TODO (probably remove as the pertinent descriptions should be in the notebook anyways._


## Questions and Issues

Feel free to ask questions about the package and its use cases at [Sentinel Hub forum](https://forum.sentinel-hub.com/) or raise an issue on [GitHub](https://github.com/sentinel-hub/eo-grow-examples/issues).


## License

The example is licensed in the same way as the whole repository. See [LICENSE](https://github.com/sentinel-hub/eo-grow-examples/blob/main/LICENSE).

## Acknowledgements

This project has received funding from the European Union’s Horizon 2020 research and innovation programme under Grant Agreement No. 101004112.