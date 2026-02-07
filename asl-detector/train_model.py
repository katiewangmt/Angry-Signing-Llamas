"""
train_model.py — Train the ASL hand landmark classifier

Usage:
    python train_model.py

Loads the collected dataset (asl_dataset.npz), trains a neural network,
evaluates performance, and saves the model to asl_model.keras.
"""

import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight

from landmarks import ASL_LABELS, NUM_FEATURES, NUM_CLASSES
from model import create_asl_model, compile_model, get_callbacks

# ------- Configuration -------
DATASET_PATH = "asl_dataset.npz"
MODEL_PATH = "asl_model.keras"
EPOCHS = 100
BATCH_SIZE = 32
TEST_SPLIT = 0.2
RANDOM_SEED = 42


def load_dataset(path):
    """Load and validate the dataset."""
    if not os.path.exists(path):
        print(f"❌ Dataset not found at '{path}'")
        print("   Run 'python collect_data.py' first to collect training data.")
        exit(1)

    data = np.load(path)
    X = data["landmarks"]
    y = data["labels"]

    print(f"📂 Loaded dataset: {X.shape[0]} samples, {X.shape[1]} features")
    print(f"   Classes present: {len(set(y))}/{NUM_CLASSES}")

    # Print per-class counts
    print("\n   Samples per class:")
    for i in range(NUM_CLASSES):
        count = np.sum(y == i)
        if count > 0:
            bar = "█" * min(count // 5, 40)
            print(f"   {ASL_LABELS[i]}: {count:>5}  {bar}")

    return X, y


def train():
    """Main training pipeline."""
    print("=" * 50)
    print("  🧠 ASL Model Training")
    print("=" * 50)

    # Load data
    X, y = load_dataset(DATASET_PATH)

    # Validate
    assert X.shape[1] == NUM_FEATURES, f"Expected {NUM_FEATURES} features, got {X.shape[1]}"

    # Split into train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SPLIT, random_state=RANDOM_SEED, stratify=y
    )
    print(f"\n📊 Train: {len(X_train)} samples | Test: {len(X_test)} samples")

    # Compute class weights for imbalanced data
    unique_classes = np.unique(y_train)
    class_weights = compute_class_weight("balanced", classes=unique_classes, y=y_train)
    class_weight_dict = dict(zip(unique_classes.astype(int), class_weights))
    print(f"⚖️  Using balanced class weights for {len(unique_classes)} classes")

    # Build model
    print("\n🏗️  Building model...")
    model = create_asl_model()
    model = compile_model(model)
    model.summary()

    # Train
    print(f"\n🚀 Training for up to {EPOCHS} epochs (early stopping enabled)...\n")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        class_weight=class_weight_dict,
        callbacks=get_callbacks(patience=15),
        verbose=1,
    )

    # Evaluate
    print("\n" + "=" * 50)
    print("  📈 Evaluation Results")
    print("=" * 50)

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
            print(f"  {ASL_LABELS[i]}: {acc:.1%} ({total} test samples)")

    # Confusion pairs (most confused letters)
    print("\n  Most confused pairs:")
    confusion_pairs = []
    for i in unique_classes:
        mask = y_test == i
        wrong = pred_classes[mask] != i
        if np.sum(wrong) > 0:
            wrong_preds = pred_classes[mask][wrong]
            for wp in np.unique(wrong_preds):
                confusion_pairs.append((
                    ASL_LABELS[i], ASL_LABELS[wp], np.sum(wrong_preds == wp)
                ))
    confusion_pairs.sort(key=lambda x: x[2], reverse=True)
    for true_l, pred_l, count in confusion_pairs[:5]:
        print(f"  {true_l} → {pred_l}: {count} errors")

    # Save model
    model.save(MODEL_PATH)
    print(f"\n💾 Model saved to '{MODEL_PATH}'")

    # Training summary
    best_epoch = np.argmax(history.history["val_accuracy"]) + 1
    best_val_acc = max(history.history["val_accuracy"])
    print(f"🏆 Best validation accuracy: {best_val_acc:.1%} (epoch {best_epoch})")
    print(f"\n✅ Done! Run 'python detect.py' for real-time detection.")


if __name__ == "__main__":
    train()
