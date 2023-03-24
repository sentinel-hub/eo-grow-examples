//VERSION=3
function setup() {
  return {
    input: ["Map"],
    output: [
        {
          id: "ESA_WorldCover_120",
          bands: 1,
          sampleType: "UINT8"
        }
    ]
  };
}
function evaluatePixel(sample) {
  return {"ESA_WorldCover_120": [sample.Map]};
}
