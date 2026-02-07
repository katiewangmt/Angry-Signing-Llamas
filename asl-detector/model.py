"""
model.py — TensorFlow/Keras model for ASL hand landmark classification

Architecture: Dense neural network that takes 63 hand landmark features
(21 landmarks × 3 coords) and classifies them into 26 ASL alphabet letters.
"""

import tensorflow as tf
from tensorflow import keras
from keras import layers, regularizers
from landmarks import NUM_FEATURES, NUM_CLASSES


def create_asl_model(dropout_rate=0.4) -> keras.Model:
    """
    Create the ASL classification model.

    Architecture:
    - Input: 63 features (21 landmarks × 3 coordinates)
    - Dense layers with batch normalization and dropout
    - Output: 26 classes (A-Z) with softmax

    This is intentionally a relatively simple model since hand landmarks
    are already a strong feature representation. The model just needs to
    learn the mapping from landmark configurations to letters.
    """
    model = keras.Sequential([
        # Input layer
        layers.Input(shape=(NUM_FEATURES,), name="landmarks_input"),

        # First hidden block
        layers.Dense(256, kernel_regularizer=regularizers.l2(1e-4)),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.Dropout(dropout_rate),

        # Second hidden block
        layers.Dense(128, kernel_regularizer=regularizers.l2(1e-4)),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.Dropout(dropout_rate),

        # Third hidden block
        layers.Dense(64, kernel_regularizer=regularizers.l2(1e-4)),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.Dropout(dropout_rate / 2),

        # Output layer
        layers.Dense(NUM_CLASSES, activation="softmax", name="asl_output"),
    ], name="ASL_Classifier")

    return model


def compile_model(model, learning_rate=1e-3) -> keras.Model:
    """Compile model with Adam optimizer and categorical crossentropy."""
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def get_callbacks(patience=10):
    """Get training callbacks for early stopping and learning rate reduction."""
    return [
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=patience,
            restore_best_weights=True,
            verbose=1,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=patience // 2,
            min_lr=1e-6,
            verbose=1,
        ),
    ]


def load_trained_model(path="asl_model.keras") -> keras.Model:
    """Load a previously trained model."""
    return keras.models.load_model(path)


if __name__ == "__main__":
    # Quick test: build and summarize the model
    model = create_asl_model()
    model = compile_model(model)
    model.summary()
    print(f"\nModel expects {NUM_FEATURES} input features → {NUM_CLASSES} output classes")
