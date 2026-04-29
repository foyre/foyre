/**
 * Generate a reasonably strong, human-typeable temporary password.
 *
 * Avoids visually confusable characters (0/O, 1/l/I) so it can be read out
 * loud or copy-pasted without error. Uses crypto.getRandomValues for entropy.
 *
 * Length defaults to 14; guarantees at least one upper / lower / digit / symbol.
 */
const UPPER = "ABCDEFGHJKMNPQRSTUVWXYZ"; // excludes I, L, O
const LOWER = "abcdefghjkmnpqrstuvwxyz"; // excludes i, l, o
const DIGITS = "23456789"; // excludes 0, 1
const SYMBOLS = "!@#$%^&*";
const ALL = UPPER + LOWER + DIGITS + SYMBOLS;
export function generateTempPassword(length = 14) {
    if (length < 8)
        length = 8;
    const bytes = new Uint32Array(length);
    crypto.getRandomValues(bytes);
    // Guarantee one of each character class.
    const chars = [
        UPPER[bytes[0] % UPPER.length],
        LOWER[bytes[1] % LOWER.length],
        DIGITS[bytes[2] % DIGITS.length],
        SYMBOLS[bytes[3] % SYMBOLS.length],
    ];
    for (let i = 4; i < length; i++) {
        chars.push(ALL[bytes[i] % ALL.length]);
    }
    // Fisher-Yates shuffle so the guaranteed chars aren't always at the start.
    for (let i = chars.length - 1; i > 0; i--) {
        const j = bytes[i] % (i + 1);
        [chars[i], chars[j]] = [chars[j], chars[i]];
    }
    return chars.join("");
}
