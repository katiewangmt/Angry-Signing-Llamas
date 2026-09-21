// Loads the converted TF.js models and runs inference. Assumes global `tf`
// (vendored tf.min.js loaded via <script> before the module).
export async function loadModels() {
  const staticModel = await tf.loadLayersModel("./detection/models/static/model.json");
  const lstmModel = await tf.loadLayersModel("./detection/models/lstm/model.json");

  function argmaxConf(dataArr) {
    let mi = 0;
    for (let i = 1; i < dataArr.length; i++) if (dataArr[i] > dataArr[mi]) mi = i;
    return { index: mi, confidence: dataArr[mi] };
  }

  return {
    predictStatic(vec63) {
      return tf.tidy(() => {
        const out = staticModel.predict(tf.tensor2d([Array.from(vec63)]));
        const d = out.dataSync();
        return argmaxConf(d);
      });
    },
    predictSequence(seq30x63) {
      return tf.tidy(() => {
        const out = lstmModel.predict(tf.tensor3d([seq30x63]));
        const d = out.dataSync();
        return argmaxConf(d);
      });
    },
  };
}
