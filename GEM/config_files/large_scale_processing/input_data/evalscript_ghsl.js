//VERSION=3
function setup() {
  return {
    input: ["PROB"],
    output: [
        {
          id: "GHSL_120",
          bands: 1,
          sampleType: "UINT8"
        }
    ]
  };
}
function evaluatePixel(sample) {
  return [sample.PROB];
}