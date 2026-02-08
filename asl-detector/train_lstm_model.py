"""
train_lstm_model.py — Train the ASL sequence LSTM classifier

Usage:
    python train_lstm_model.py

Loads the collected sequence dataset (asl_sequence_dataset.npz), trains an LSTM
neural network, evaluates performance, and saves the model to asl_lstm_model.keras.
"""

import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight

from model_lstm import (
    create_lstm_model,
    compile_model,
    get_callbacks,
    SEQUENCE_LENGTH,
    SEQUENCE_LABELS,
    NUM_SEQUENCE_CLASSES,
)
from landmarks import NUM_FEATURES

# ------- Configuration -------
DATASET_PATH = "asl_sequence_dataset.npz"
MODEL_PATH = "asl_lstm_model.keras"
EPOCHS = 100
BATCH_SIZE = 16
TEST_SPLIT = 0.2
RANDOM_SEED = 42


def load_dataset(path):
    """Load and validate the sequence dataset."""
    if not os.path.exists(path):
        print(f"❌ Dataset not found at '{path}'")
        print("   Run 'python collect_sequence_data.py' first to collect training data.")
        exit(1)

    data = np.load(path)
    X = data["sequences"]  # Shape: (num_sequences, sequence_length, num_features)
    y = data["labels"]

    print(f"📂 Loaded dataset: {X.shape[0]} sequences")
    print(f"   Sequence shape: {X.shape[1]} frames × {X.shape[2]} features")
    print(f"   Classes present: {len(set(y))}/{NUM_SEQUENCE_CLASSES}")

    # Validate shape
    assert X.shape[1] == SEQUENCE_LENGTH, \
        f"Expected sequence length {SEQUENCE_LENGTH}, got {X.shape[1]}"
    assert X.shape[2] == NUM_FEATURES, \
        f"Expected {NUM_FEATURES} features per frame, got {X.shape[2]}"

    # Print per-class counts
    print("\n   Samples per class:")
    for i in range(NUM_SEQUENCE_CLASSES):
        count = np.sum(y == i)
        if count > 0:
            bar = "█" * min(count // 2, 40)
            print(f"   {SEQUENCE_LABELS[i]}: {count:>5}  {bar}")

    return X, y


def train():
    """Main training pipeline."""
    print("=" * 50)
    print("  🧠 ASL LSTM Model Training")
    print("=" * 50)

    # Load data
    X, y = load_dataset(DATASET_PATH)

    # Split into train/test
    # For small datasets, we need to handle splitting carefully
    min_samples_per_class = min([np.sum(y == i) for i in np.unique(y)])
    min_test_samples_needed = len(np.unique(y))  # At least 1 per class for stratified split
    
    if len(X) < min_test_samples_needed * 2:
        # Too small for train/test split - use all data for training
        print(f"\n⚠️  Dataset too small for train/test split (need at least {min_test_samples_needed * 2} samples)")
        print("   Using all data for training (no validation split)")
        X_train, X_test = X, X[:0]  # Empty test set
        y_train, y_test = y, y[:0]
        validation_data = None
    elif min_samples_per_class < 2:
        # Can't do stratified split - use regular split
        print(f"\n⚠️  Too few samples per class for stratified split")
        print("   Using regular train/test split (no stratification)")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SPLIT, random_state=RANDOM_SEED, stratify=None
        )
        validation_data = (X_test, y_test)
    else:
        # Normal stratified split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SPLIT, random_state=RANDOM_SEED, stratify=y
        )
        validation_data = (X_test, y_test)
    
    print(f"\n📊 Train: {len(X_train)} sequences | Test: {len(X_test)} sequences")

    # Compute class weights for imbalanced data
    unique_classes = np.unique(y_train)
    class_weights = compute_class_weight("balanced", classes=unique_classes, y=y_train)
    class_weight_dict = dict(zip(unique_classes.astype(int), class_weights))
    print(f"⚖️  Using balanced class weights for {len(unique_classes)} classes")

    # Build model
    print("\n🏗️  Building LSTM model...")
    model = create_lstm_model(
        sequence_length=SEQUENCE_LENGTH,
        num_features=NUM_FEATURES,
        num_classes=NUM_SEQUENCE_CLASSES,
    )
    model = compile_model(model)
    model.summary()

    # Adjust batch size for small datasets
    effective_batch_size = min(BATCH_SIZE, len(X_train))
    if effective_batch_size < BATCH_SIZE:
        print(f"⚠️  Adjusting batch size to {effective_batch_size} (dataset too small for batch_size={BATCH_SIZE})")

    # Train
    print(f"\n🚀 Training for up to {EPOCHS} epochs (early stopping enabled)...\n")
    history = model.fit(
        X_train, y_train,
        validation_data=validation_data,
        epochs=EPOCHS,
        batch_size=effective_batch_size,
        class_weight=class_weight_dict,
        callbacks=get_callbacks(patience=15),
        verbose=1,
    )

    # Evaluate
    print("\n" + "=" * 50)
    print("  📈 Evaluation Results")
    print("=" * 50)

    if len(X_test) > 0:
        test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
        print(f"\n  Test Accuracy:  {test_acc:.1%}")
        print(f"  Test Loss:      {test_loss:.4f}")

        # Per-class accuracy
        predictions = model.predict(X_test, verbose=0)
        pred_classes = np.argmax(predictions, axis=1)

        print("\n  Per-class accuracy:")
        for i in unique_classes:
            mask = y_test == i
            if np.sum(mask) > 0:
                acc = np.mean(pred_classes[mask] == i)
                total = np.sum(mask)
                print(f"  {SEQUENCE_LABELS[i]}: {acc:.1%} ({total} test sequences)")

        # Confusion matrix
        print("\n  Confusion matrix:")
        for i in unique_classes:
            mask = y_test == i
            wrong = pred_classes[mask] != i
            if np.sum(wrong) > 0:
                wrong_preds = pred_classes[mask][wrong]
                for wp in np.unique(wrong_preds):
                    count = np.sum(wrong_preds == wp)
                    print(f"  {SEQUENCE_LABELS[i]} → {SEQUENCE_LABELS[wp]}: {count} errors")
    else:
        print("\n  ⚠️  No test set available (dataset too small)")
        print("  Model trained on all available data")

    # Save model
    model.save(MODEL_PATH)
    print(f"\n💾 Model saved to '{MODEL_PATH}'")

    # Training summary
    if len(X_test) > 0 and "val_accuracy" in history.history:
        best_epoch = np.argmax(history.history["val_accuracy"]) + 1
        best_val_acc = max(history.history["val_accuracy"])
        print(f"🏆 Best validation accuracy: {best_val_acc:.1%} (epoch {best_epoch})")
    else:
        if "accuracy" in history.history:
            best_epoch = np.argmax(history.history["accuracy"]) + 1
            best_acc = max(history.history["accuracy"])
            print(f"🏆 Best training accuracy: {best_acc:.1%} (epoch {best_epoch})")
    
    print(f"\n💡 Tip: Collect more sequences (10-20 per sign) for better accuracy!")
    print(f"✅ Done! Model ready for sequence-based ASL detection.")


if __name__ == "__main__":
    train()

