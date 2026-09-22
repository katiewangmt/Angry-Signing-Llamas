// Ported verbatim from asl-detector/landmarks.py and model_lstm.py + asl_handler.py
export const ASL_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
export const SEQUENCE_LABELS = [
  "I_LOVE_YOU", "THANK_YOU", "SIGMA", "BADDIE", "RIZZ", "6_7", "OK", "HELLO", "GOODBYE",
];
export const WORD_TO_LETTER = {
  THANK_YOU: "T", OK: "O", HELLO: "H", GOODBYE: "G", I_LOVE_YOU: "I", "6_7": "6",
};
