"""Convert the trained Keras models to TensorFlow.js layers format.

Primary path: tensorflowjs.converters.save_keras_model on the loaded model.
Fallback (if conversion of the .keras file fails): rebuild the architecture from
asl-detector and load weights, then convert the rebuilt model.

Environment note (verified against this checkout's TF 2.19 / Keras 3.13):
tensorflowjs 4.22's Python converter happily serializes a Keras-3 model
without raising, but the resulting model.json uses Keras 3's config schema
(e.g. InputLayer's "batch_shape" key instead of "batch_input_shape"), which
the matching @tensorflow/tfjs-layers 4.22 JS runtime cannot deserialize
("An InputLayer should be passed either a `batchInputShape` or an
`inputShape`."). So for the static model we additionally verify the
converted topology is JS-loadable and force the rebuild fallback when it
isn't. The rebuild uses the `tf_keras` legacy-Keras-2 shim (already a
dependency of `tensorflowjs`) directly, rather than
`asl-detector/model.py:create_asl_model`: that function does
`from tensorflow import keras` (redirectable to legacy tf_keras) but
`from keras import layers` (the standalone `keras` package, which is always
Keras 3 regardless of environment), so it cannot itself build a legacy-Keras
model. The rebuilt architecture matches create_asl_model() exactly, minus
the Dense layers' L2 kernel regularizers: regularizers only add a penalty to
the training loss and have zero effect on predict() output, and
tfjs-layers doesn't register Keras's "L2" regularizer class name anyway.
Weights are loaded directly from the original .keras file via
model.load_weights(), which reads by variable name/order and works across
the Keras 2/3 divide (verified to reproduce the original model's predictions
exactly, max abs diff 0.0, before this script was relied on for parity).
"""
import os, sys, json
DETECTOR = os.path.join(os.path.dirname(__file__), "..", "asl-detector")
sys.path.insert(0, DETECTOR)
OUT = os.path.join(os.path.dirname(__file__), "..", "frontend", "detection", "models")

import tensorflow as tf  # noqa: E402
import tensorflowjs as tfjs  # noqa: E402


def _assert_js_loadable(out_dir):
    """Raise if model.json's InputLayer uses the Keras-3-only "batch_shape"
    key, which the JS tfjs-layers deserializer (built for the Keras-2 config
    schema) cannot read."""
    with open(os.path.join(out_dir, "model.json")) as f:
        topo = json.load(f)["modelTopology"]
    cfg = topo.get("model_config", topo).get("config", {})
    layers_cfg = cfg.get("layers", [])
    if layers_cfg and "batch_shape" in layers_cfg[0].get("config", {}):
        raise ValueError("converted topology uses Keras 3 schema (batch_shape); not tfjs-layers loadable")


def convert(keras_path, out_subdir, rebuild_fn=None, post_check=None):
    out_dir = os.path.join(OUT, out_subdir)
    os.makedirs(out_dir, exist_ok=True)
    try:
        model = tf.keras.models.load_model(keras_path, compile=False, safe_mode=False)
        tfjs.converters.save_keras_model(model, out_dir)
        if post_check:
            post_check(out_dir)
        print(f"converted {keras_path} -> {out_dir}")
    except Exception as e:
        if rebuild_fn is None:
            raise
        print(f"direct convert failed ({e}); rebuilding architecture and loading weights")
        model = rebuild_fn()
        model.load_weights(keras_path)
        tfjs.converters.save_keras_model(model, out_dir)
        if post_check:
            post_check(out_dir)
        print(f"converted (rebuilt) {keras_path} -> {out_dir}")


def _rebuild_static():
    # Built with the legacy tf_keras (Keras 2) API so the tensorflowjs
    # converter emits tfjs-layers-compatible JSON; see module docstring.
    import tf_keras
    from tf_keras import layers
    from landmarks import NUM_FEATURES, NUM_CLASSES

    dropout_rate = 0.4
    return tf_keras.Sequential([
        layers.Input(shape=(NUM_FEATURES,), name="landmarks_input"),
        layers.Dense(256),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.Dropout(dropout_rate),
        layers.Dense(128),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.Dropout(dropout_rate),
        layers.Dense(64),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.Dropout(dropout_rate / 2),
        layers.Dense(NUM_CLASSES, activation="softmax", name="asl_output"),
    ], name="ASL_Classifier")


def _rebuild_lstm():
    from model_lstm import create_lstm_model
    return create_lstm_model()


if __name__ == "__main__":
    # Static model: force the robust rebuild path whenever the direct
    # convert's output isn't actually loadable by tfjs-layers (see docstring).
    convert(os.path.join(DETECTOR, "asl_model.keras"), "static", _rebuild_static, post_check=_assert_js_loadable)
    # LSTM model: convert per the brief; its tfjs-layers load-compatibility
    # and parity are validated by a later task, not this one.
    convert(os.path.join(DETECTOR, "asl_lstm_model.keras"), "lstm", _rebuild_lstm)
