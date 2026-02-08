"""
model_lstm.py — LSTM model for ASL sequence classification

Architecture: LSTM network that takes sequences of hand landmarks
(SEQUENCE_LENGTH frames × 63 features) and classifies them into sequence-based
ASL signs like "I love you" and "Thank you".
"""

import tensorflow as tf
from tensorflow import keras
from keras import layers, regularizers
from landmarks import NUM_FEATURES

# Sequence configuration (should match collect_sequence_data.py)
SEQUENCE_LENGTH = 30
SEQUENCE_LABELS = ["I_LOVE_YOU", "THANK_YOU", "SIGMA", "BADDIE", "RIZZ", "6_7", "OK", "HELLO", "GOODBYE"]
NUM_SEQUENCE_CLASSES = len(SEQUENCE_LABELS)


def create_lstm_model(sequence_length=SEQUENCE_LENGTH, 
                     num_features=NUM_FEATURES,
                     num_classes=NUM_SEQUENCE_CLASSES,
                     lstm_units=128,
                     dropout_rate=0.3) -> keras.Model:
    """
    Create an LSTM model for sequence-based ASL sign classification.

    Architecture:
    - Input: (sequence_length, num_features) - sequences of hand landmarks
    - LSTM layers to capture temporal patterns
    - Dense layers for classification
    - Output: num_classes with softmax

    Args:
        sequence_length: Number of frames per sequence
        num_features: Number of features per frame (63 for hand landmarks)
        num_classes: Number of output classes
        lstm_units: Number of units in LSTM layers
        dropout_rate: Dropout rate for regularization

    Returns:
        Compiled Keras model
    """
    model = keras.Sequential([
        # Input layer
        layers.Input(shape=(sequence_length, num_features), name="sequence_input"),

        # First LSTM layer with return_sequences=True to pass sequences to next layer
        layers.LSTM(lstm_units, return_sequences=True, name="lstm_1"),
        layers.BatchNormalization(),
        layers.Dropout(dropout_rate),

        # Second LSTM layer
        layers.LSTM(lstm_units // 2, return_sequences=False, name="lstm_2"),
        layers.BatchNormalization(),
        layers.Dropout(dropout_rate),

        # Dense layers for classification
        layers.Dense(64, kernel_regularizer=regularizers.l2(1e-4), name="dense_1"),
        layers.BatchNormalization(),
        layers.Activation("relu"),
        layers.Dropout(dropout_rate / 2),

        # Output layer
        layers.Dense(num_classes, activation="softmax", name="sequence_output"),
    ], name="ASL_Sequence_Classifier")

    return model


def compile_model(model, learning_rate=1e-3) -> keras.Model:
    """Compile model with Adam optimizer and categorical crossentropy."""
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def get_callbacks(patience=15, model_checkpoint_path=None):
    """
    Get training callbacks for early stopping and learning rate reduction.
    
    Args:
        patience: Patience for early stopping
        model_checkpoint_path: Optional path to save best model checkpoint
    """
    callbacks = [
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
    
    if model_checkpoint_path:
        callbacks.append(
            keras.callbacks.ModelCheckpoint(
                model_checkpoint_path,
                monitor="val_accuracy",
                save_best_only=True,
                verbose=1,
            )
        )
    
    return callbacks


def load_trained_model(path="asl_lstm_model.keras") -> keras.Model:
    """Load a previously trained LSTM model."""
    return keras.models.load_model(path)


if __name__ == "__main__":
    # Quick test: build and summarize the model
    model = create_lstm_model()
    model = compile_model(model)
    model.summary()
    print(f"\nModel expects input shape: ({SEQUENCE_LENGTH}, {NUM_FEATURES})")
    print(f"Model outputs: {NUM_SEQUENCE_CLASSES} classes")
    print(f"Classes: {SEQUENCE_LABELS}")

