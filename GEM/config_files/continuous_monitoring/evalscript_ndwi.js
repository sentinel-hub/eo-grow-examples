//VERSION=3
function setup() {
  return {
    input: ["B03", "B08", "CLM", "dataMask"],
    output: [
        {
          id: "NDWI",
          bands: 1,
          sampleType: "FLOAT32"
        }
    ]
  };
}
function is_bad(sample) {
  return ((!sample.dataMask) || sample.CLM)
}
function evaluatePixel(sample) {
  let ndwi = is_bad(sample) ? -1 : index(sample.B03, sample.B08)
  return {"NDWI": [ndwi]};
}
