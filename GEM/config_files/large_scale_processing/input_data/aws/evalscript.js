//VERSION=3

let inputs = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12", "QM"];

function setup() {
  let outputs = [];
  inputs.forEach(input => {
    outputs.push({
      id: input,
      bands: 1,
      sampleType: (input === "QM") ? SampleType.UINT8 : SampleType.UINT16
    });
  });

  return {
    input: [{
      bands: inputs,
      units: "DN"
    }],
    output: outputs,
    mosaicking: Mosaicking.ORBIT
  };
}

function updateOutput(outputs, collection) {
    let n_observations = Math.max(collection.scenes.length, 1);
    Object.values(outputs).forEach((output) => {
        output.bands = n_observations;
    });
}

function updateOutputMetadata(scenes, inputMetadata, outputMetadata) {
  outputMetadata.userData = {
    factors: inputMetadata.normalizationFactor,
    orbits: scenes.orbits
  };
}

function evaluatePixel(samples) {
  let n_observations = Math.max(samples.length, 1);
  let dataStacks = [];

  inputs.forEach(() => {
    let stack = new Array(n_observations).fill(0);
    dataStacks.push(stack);
  });

  samples.forEach((sample, sample_index) => {
    dataStacks.forEach((stack, stack_index) => {
      stack[sample_index] = sample[inputs[stack_index]];
    });
  });

  let results = {};
  dataStacks.forEach((stack, index) => {
      results[inputs[index]] = stack;
  });
  return results;
}
