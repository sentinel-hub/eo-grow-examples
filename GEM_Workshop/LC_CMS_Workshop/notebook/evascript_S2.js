//VERSION=3
const helperBands = ["dataMask", "SCL", "CLM"]
const outputBands = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12"]
const measurements = 6

// Initialize dates and interval
const startDate = new Date("2020-01-01");
const endDate = new Date("2021-01-01");

function prepareInput() {
    return [{
        bands: outputBands.concat(helperBands),
        units: "DN"
    }]
}

function prepareOutput() {
    let outputTiffs = []
    outputBands.forEach(sband =>
        outputTiffs.push({
            id: sband,
            bands: measurements,
            sampleType: "UINT16"
        })
    );
    outputTiffs.push({
        id: 'valcount',
        bands: measurements,
        sampleType: "UINT8"
    });
    return outputTiffs;
}

/**
 * Split the date into a time interval
 * @param startDate
 * @param endDate
 * @param numberOfIntervals
 * @param roundCoefficient
 * @returns {*[]}
 */
function splitDateIntoEqualIntervals(startDate, endDate, numberOfIntervals, roundCoefficient) {
    let diff = endDate.getTime() - startDate.getTime();
    let intervalLength = diff / numberOfIntervals;
    let intervals = [];
    let prevDate = startDate
    for (let i = 1; i < numberOfIntervals + 1; i++) {
        let ndate = new Date(startDate.getTime() + i * intervalLength);
        ndate = new Date(Math.round(ndate.getTime() / roundCoefficient) * roundCoefficient);
        ndate = new Date(ndate.getTime() + ndate.getTimezoneOffset() * 60000);
        intervals.push([prevDate, ndate]);
        prevDate = ndate
    }
    return intervals;

}

function setup() {
    return {
        input: prepareInput(),
        output: prepareOutput(),
        mosaicking: Mosaicking.ORBIT
    }
}

/**
 * Scene classification data, based on Sen2Cor processor [performed at 20m resolution]
 * @type {{CLOUD_MEDIUM_PROB: number, CLOUD_HIGH_PROB: number, NODATA: number, DEFECTIVE: number}}
 */
const SclValue = {
    'NODATA': 0,
    'DEFECTIVE': 1,
    // 'CLOUD_SHADOWS': 3,
    'CLOUD_MEDIUM_PROB': 8,
    'CLOUD_HIGH_PROB': 9,
}

function isValMaskCLM(curSample) {
    return curSample.CLM === 0
}

function isValData(curSample) {
    return curSample.dataMask === 1
}

function isValMaskSCLStrict(curSample) {
    return ![SclValue.NODATA, SclValue.DEFECTIVE, SclValue.CLOUD_HIGH_PROB, SclValue.CLOUD_MEDIUM_PROB].includes(curSample.SCL)
}

function isValMaskSCL(curSample) {
    return ![SclValue.NODATA, SclValue.DEFECTIVE, SclValue.CLOUD_HIGH_PROB].includes(curSample.SCL)
}

function filterClouds(validSamples) {
    let cloudlessSamples = validSamples.filter(isValMaskCLM).filter(isValMaskSCLStrict)
    if (cloudlessSamples.length < 2) {
        // if we don't have enough samples, then try a less strict version of calculating cloud cover
        cloudlessSamples = validSamples.filter(isValMaskCLM).filter(isValMaskSCL)
    }
    if (cloudlessSamples.length < 2) {
        // if we don't have enough samples, then try even less strict version of calculating cloud cover
        cloudlessSamples = validSamples.filter(isValMaskSCLStrict)
    }
    if (cloudlessSamples.length < 2) {
        // if we don't have enough samples, then try even less strict version of calculating cloud cover
        cloudlessSamples = validSamples.filter(isValMaskSCL)
    }
    return cloudlessSamples;
}

function calcNDVI(sample) {
    const denom = sample.B04 + sample.B08;
    // undefined should be treated as 0 or -1 ? ()
    return denom !== 0 ? (sample.B08 - sample.B04) / denom : -1.0
}


function getMaxNdviIdx(samples) {
    let maxNdvi = -1.0
    let maxNdviIdx;
    for (let i = 0; i < samples.length; i++) {
        const curNdvi = calcNDVI(samples[i])
        if (curNdvi > maxNdvi) {
            maxNdviIdx = i
            maxNdvi = curNdvi
        }
    }
    return maxNdviIdx
}

function withoutTime(intime) {
    // Return date without time
    intime.setHours(0, 0, 0, 0);
    return intime;
}

function evaluatePixelForTimeIntervalUsingMaxNdvi(samples) {
    /// filter valid samples first based on cloud cover filter
    let validSamples = samples.filter(isValData)
    let cloudlessSamples = filterClouds(validSamples)
    if (cloudlessSamples.length === 0) {
        return {
            features: outputBands.map((band) => 0),
            valcount: [cloudlessSamples.length]
        }
    }

    // Find the index which has max_ndvi value & the sample at that index is assigned be the best sample
    const maxNdviIdx = getMaxNdviIdx(cloudlessSamples)

    if (maxNdviIdx === undefined) {
        return {
            features: outputBands.map((band) => 0),
            valcount: [cloudlessSamples.length]
        }
    }
    // return the composite / resulting bands for generating TIFF
    const bestSample = cloudlessSamples[maxNdviIdx]
    return {
        features: outputBands.map(band => bestSample[band]),
        valcount: [cloudlessSamples.length]
    }
}

function evaluatePixel(samples, scenes) {
    // init output collection
    let outputs = {}
    outputBands.forEach(band => {
        outputs[band] = []
    })
    outputs['valcount'] = []

    // get valid samples' indices and interval
    let validIndices = [];
    samples.forEach((sample, idx) => {
        if (isValData(sample)) {
            validIndices.push(idx)
        }
    })
    let sampleDates = scenes.map((scene) => withoutTime(new Date(scene.date)))

    // evaluate pixels for each interval & add the output to the main output collection
    const intervals = splitDateIntoEqualIntervals(startDate, endDate, measurements, 1);
    intervals.forEach((curInterval) => {
        const startIntDate = curInterval[0]
        const endIntDate = curInterval[1]
        let samplesWithinInterval = []
        validIndices.forEach(validIdx => {
            if (sampleDates[validIdx] >= startIntDate && sampleDates[validIdx] < endIntDate) {
                samplesWithinInterval.push(samples[validIdx])
            }
        });
        const intervalOutput = evaluatePixelForTimeIntervalUsingMaxNdvi(samplesWithinInterval)
        outputBands.forEach((band, bandIdx) => {
            outputs[band].push(intervalOutput['features'][bandIdx]);
        })
        outputs['valcount'].push(intervalOutput['valcount'][0]);
    })
    return outputs
}

function updateOutputMetadata(scenes, inputMetadata, outputMetadata) {
    // update scenes metadata first
    let scenesWithDates = []
    splitDateIntoEqualIntervals(startDate, endDate, measurements, 1).forEach((interval) => {
        scenesWithDates.push({'date': interval[0].toISOString()});
    })

    outputMetadata.userData = {
        "norm_factor": inputMetadata.normalizationFactor, "scenes": JSON.stringify(scenesWithDates)
    }
}